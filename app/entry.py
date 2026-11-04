"""Event-scoped entrance verification with cross-browser QR capture.

A QR encodes only a signed opaque ticket token. GETs never grant admission;
a CSRF-protected staff/admin POST consumes a ticket atomically. A mobile photo
upload works even in browsers without BarcodeDetector/getUserMedia support.
"""
from io import BytesIO

import qrcode
from flask import Blueprint, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select, update

from . import db, limiter
from .models import Booking, Event, Gate, Seat, Ticket, utc_now
from .qr_decode import decode_qr_photo
from .ticketing import resolve_ticket_token, ticket_token, token_from_scan

entry = Blueprint("entry", __name__)


def _gate_staff():
    if current_user.role not in ("staff", "admin"):
        abort(403)


def _can_view(ticket):
    return current_user.role == "admin" or current_user.id in (
        ticket.booking.user_id, ticket.attendee_user_id
    )


def _private(response):
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _selected_gate(ticket=None):
    gate_id = request.values.get("gate_id", type=int)
    if gate_id is None:
        return None
    gate = db.session.get(Gate, gate_id)
    # Gate selection must always be event-scoped, never a foreign event gate.
    if gate is None or (ticket is not None and gate.event_id != ticket.event_id):
        return None
    return gate


def admission_verdict(ticket, gate):
    """Return (machine status, title, help) without mislabeling valid codes."""
    if ticket is None:
        return "invalid", "INVALID TICKET", "The ticket QR code is unknown or has been altered."
    if ticket.booking.status != "reserved" or ticket.status == "cancelled":
        return "invalid", "CANCELLED TICKET", "This reservation was cancelled; entry is not allowed."
    if ticket.status == "checked_in":
        return "invalid", "ALREADY CHECKED IN", "This ticket has already been used for stadium entry."
    if ticket.status != "active" or ticket.attendee_user_id is None:
        return "invalid", "TICKET NOT ASSIGNED", "An administrator must verify the attendee before entry."
    if not ticket.event.checkin_enabled:
        return "waiting", "VALID TICKET — ENTRY NOT OPEN", "The administrator must open stadium entry for this event."
    if gate is None:
        return "waiting", "VALID TICKET — SELECT GATE", "Choose the entrance where this QR is being scanned."
    if ticket.seat.gate_id != gate.id:
        expected = ticket.seat.gate.name if ticket.seat.gate else "the assigned gate"
        return "waiting", "VALID TICKET — WRONG GATE", f"Use {expected} instead of {gate.name}."
    if not gate.is_open:
        return "waiting", "VALID TICKET — GATE CLOSED", f"{gate.name} has not been opened by an administrator."
    return "valid", "VALID TICKET — ADMIT STUDENT", "Check university identification, then confirm entry."


@entry.get("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    if not _can_view(ticket):
        abort(404)
    return _private(make_response(render_template("ticket_detail.html", ticket=ticket)))


@entry.get("/tickets/<int:ticket_id>/qr.png")
@login_required
def ticket_qr(ticket_id):
    """QR contains a signed token, independent of localhost / campus domain."""
    ticket = db.get_or_404(Ticket, ticket_id)
    if not _can_view(ticket):
        abort(404)
    if ticket.status != "active" or ticket.booking.status != "reserved":
        abort(404)
    out = BytesIO()
    qr = qrcode.QRCode(box_size=9, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(ticket_token(ticket))
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(out, format="PNG")
    response = make_response(out.getvalue())
    response.headers["Content-Type"] = "image/png"
    return _private(response)


@entry.get("/entry/scan")
@login_required
def scan():
    _gate_staff()
    gate_id = request.args.get("gate_id", type=int)
    gate = db.session.get(Gate, gate_id) if gate_id else None
    code = request.args.get("code", "")
    if code:
        token = token_from_scan(code, request.host)
        if not token:
            flash("QR not recognized. Scan a CSTBS ticket or upload its QR image.", "error")
        else:
            return redirect(url_for("entry.verify", token=token,
                                      **({"gate_id": gate.id} if gate else {})))
    gates = db.session.scalars(select(Gate).join(Event).order_by(Event.starts_at, Gate.name)).all()
    return _private(make_response(render_template("entry/scan.html", gates=gates, selected_gate=gate)))


@entry.post("/entry/scan-photo")
@limiter.limit("20 per minute")
@login_required
def scan_photo():
    """Camera/photo input fallback; never trust any decoded content directly."""
    _gate_staff()
    gate = _selected_gate()
    uploaded = request.files.get("qr_photo")
    raw = uploaded.stream.read(3 * 1024 * 1024 + 1) if uploaded else b""
    code = decode_qr_photo(raw)
    token = token_from_scan(code, request.host) if code else None
    if not token:
        flash("Could not read an official QR ticket. Try a sharper photo or paste the code.", "error")
        return redirect(url_for("entry.scan", **({"gate_id": gate.id} if gate else {})))
    return redirect(url_for("entry.verify", token=token,
                            **({"gate_id": gate.id} if gate else {})))


@entry.get("/entry/verify/<token>")
@login_required
def verify(token):
    _gate_staff()
    ticket = resolve_ticket_token(token)
    gate = _selected_gate(ticket)
    status, title, guidance = admission_verdict(ticket, gate)
    gates = db.session.scalars(select(Gate).where(Gate.event_id == ticket.event_id)
                              .order_by(Gate.name)).all() if ticket else []
    return _private(make_response(render_template("entry/verify.html", ticket=ticket, token=token,
                                  gate=gate, gates=gates, status=status, title=title, guidance=guidance)))


@entry.post("/entry/check-in/<token>")
@limiter.limit("30 per minute")
@login_required
def check_in(token):
    _gate_staff()
    ticket = resolve_ticket_token(token)
    gate = _selected_gate(ticket)
    status, title, _ = admission_verdict(ticket, gate)
    if status != "valid":
        flash(title + ". Admission was not recorded.", "error")
        return redirect(url_for("entry.verify", token=token,
                                **({"gate_id": gate.id} if gate else {})))
    # Conditional DB update protects against two staff scanning at once, plus
    # an admin closing the event or entrance between verification and POST.
    updated = db.session.execute(update(Ticket).where(
        Ticket.id == ticket.id, Ticket.status == "active",
        Ticket.booking_id.in_(select(Booking.id).where(Booking.status == "reserved")),
        Ticket.event_id.in_(select(Event.id).where(Event.checkin_enabled.is_(True))),
        Ticket.booking_id.in_(select(Booking.id).join(Seat, Booking.seat_id == Seat.id).where(
            Seat.gate_id == gate.id)),
        select(Gate.is_open).where(Gate.id == gate.id).scalar_subquery().is_(True),
    ).values(status="checked_in", checked_in_at=utc_now(),
             checked_in_by_id=current_user.id, checked_in_gate_id=gate.id))
    if updated.rowcount != 1:
        db.session.rollback()
        flash("The ticket was already used or the gate status changed. Refresh and check again.", "error")
    else:
        db.session.commit()
        flash(f"Entry approved: {ticket.attendee_name}, {ticket.seat.display_label}, {gate.name}.", "success")
    return redirect(url_for("entry.verify", token=token, gate_id=gate.id))


@entry.get("/admin/check-ins")
@login_required
def checkin_dashboard():
    _gate_staff()
    counts = db.session.execute(select(Event, func.count(Ticket.id).filter(Ticket.status == "checked_in"))
        .outerjoin(Ticket, Ticket.event_id == Event.id)
        .group_by(Event.id).order_by(Event.starts_at.desc())).all()
    return render_template("entry/dashboard.html", counts=counts)
