"""Student QR ticket display and staff-controlled stadium gate check-in.

Scanning a QR is a read-only GET. A separate CSRF-protected POST, performed by
a logged-in staff/admin user, consumes admission atomically. Browsers without
the BarcodeDetector API can use their camera's ordinary QR reader or paste a URL.
"""
from io import BytesIO

import qrcode
from flask import Blueprint, abort, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select, update

from . import db, limiter
from .models import Booking, Event, Ticket, User, utc_now
from .ticketing import resolve_ticket_token, ticket_token, token_from_scan

entry = Blueprint("entry", __name__)


def _gate_staff():
    if current_user.role not in ("staff", "admin"):
        abort(403)


def _can_view(ticket):
    return current_user.role == "admin" or (
        current_user.id in (ticket.booking.user_id, ticket.attendee_user_id)
    )


def _private(response):
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


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
    """Generate image at request time; QR never holds names or student IDs."""
    ticket = db.get_or_404(Ticket, ticket_id)
    if not _can_view(ticket):
        abort(404)
    if ticket.status not in ("active", "checked_in") or ticket.booking.status != "reserved":
        abort(404)
    scan_url = url_for("entry.verify", token=ticket_token(ticket), _external=True)
    out = BytesIO()
    qr = qrcode.QRCode(box_size=8, border=3, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(scan_url)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(out, format="PNG")
    response = make_response(out.getvalue())
    response.headers["Content-Type"] = "image/png"
    return _private(response)


@entry.get("/entry/scan")
@login_required
def scan():
    _gate_staff()
    code = request.args.get("code", "")
    if code:
        token = token_from_scan(code, request.host)
        if not token:
            flash("Invalid or foreign QR link. Scan an official CSTBS ticket.", "error")
        else:
            return redirect(url_for("entry.verify", token=token))
    return _private(make_response(render_template("entry/scan.html")))


@entry.get("/entry/verify/<token>")
@login_required
def verify(token):
    _gate_staff()
    ticket = resolve_ticket_token(token)
    return _private(make_response(render_template("entry/verify.html", ticket=ticket, token=token)))


@entry.post("/entry/check-in/<token>")
@limiter.limit("30 per minute")
@login_required
def check_in(token):
    _gate_staff()
    ticket = resolve_ticket_token(token)
    if ticket is None:
        flash("Invalid ticket signature or unknown ticket.", "error")
        return redirect(url_for("entry.scan"))
    if not ticket.event.checkin_enabled:
        flash("Gate entry has not been opened for this event.", "error")
        return redirect(url_for("entry.verify", token=token))
    if ticket.booking.status != "reserved" or ticket.status != "active":
        flash("Ticket cancelled, already checked in, or not yet assigned.", "error")
        return redirect(url_for("entry.verify", token=token))
    # Conditional UPDATE prevents two scanners from admitting the same ticket.
    updated = db.session.execute(update(Ticket).where(
        Ticket.id == ticket.id, Ticket.status == "active",
        Ticket.booking_id.in_(select(Booking.id).where(Booking.status == "reserved")),
        Ticket.event_id.in_(select(Event.id).where(Event.checkin_enabled.is_(True))),
    ).values(status="checked_in", checked_in_at=utc_now(), checked_in_by_id=current_user.id))
    if updated.rowcount != 1:
        db.session.rollback()
        flash("Ticket already used by another gate.", "error")
    else:
        db.session.commit()
        flash(f"Entry confirmed: {ticket.attendee_name} · {ticket.seat.display_label}.", "success")
    return redirect(url_for("entry.verify", token=token))


@entry.get("/admin/check-ins")
@login_required
def checkin_dashboard():
    _gate_staff()
    counts = db.session.execute(select(Event, func.count(Ticket.id).filter(Ticket.status == "checked_in"))
        .outerjoin(Ticket, Ticket.event_id == Event.id)
        .group_by(Event.id).order_by(Event.starts_at.desc())).all()
    return render_template("entry/dashboard.html", counts=counts)
