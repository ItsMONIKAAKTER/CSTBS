"""V4 administration: dashboard, inventory, account roles, booking oversight.

All mutations require POST with Flask-WTF CSRF protection. Historical bookings
are retained. Admin capabilities are never granted through public forms.
"""

from collections import defaultdict
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from . import db, limiter
from .authz import admin_required
from .forms import CreateSectionForm, RenameSectionForm, RoleForm, AdminInviteForm, StudentIDForm
from .models import Booking, Event, Gate, Seat, Ticket, User
from .notifications import notify_booking_cancelled
from .admin_keys import issue_login_key
import secrets

admin = Blueprint("admin", __name__, url_prefix="/admin")


def _admin_route(view):
    """Decorator used on all admin pages and actions."""
    return login_required(admin_required(view))


@admin.get("/")
@_admin_route
def dashboard():
    """Live stadium operations with event-scoped capacity and entry state."""
    from datetime import datetime, timedelta
    metrics = {
        "students": db.session.scalar(select(func.count(User.id)).where(User.role == "student")),
        "events": db.session.scalar(select(func.count(Event.id))),
        "active_tickets": db.session.scalar(select(func.count(Ticket.id)).where(
            Ticket.status.in_(["active", "checked_in"]))),
        "inside": db.session.scalar(select(func.count(Ticket.id)).where(Ticket.status == "checked_in")),
        "blocked_seats": db.session.scalar(select(func.count(Seat.id)).where(Seat.is_blocked.is_(True))),
    }
    events = db.session.scalars(select(Event).where(
        Event.starts_at >= datetime.now() - timedelta(days=3)
    ).order_by(Event.starts_at).limit(12)).all()
    if not events:
        events = db.session.scalars(select(Event).order_by(Event.starts_at.desc()).limit(6)).all()
    operations = []
    for event in events:
        capacity = db.session.scalar(select(func.count(Seat.id)).where(Seat.event_id == event.id))
        reserved = db.session.scalar(select(func.count(Booking.id)).join(Seat).where(
            Seat.event_id == event.id, Booking.status == "reserved"))
        checked = db.session.scalar(select(func.count(Ticket.id)).where(
            Ticket.event_id == event.id, Ticket.status == "checked_in"))
        blocked = db.session.scalar(select(func.count(Seat.id)).where(
            Seat.event_id == event.id, Seat.is_blocked.is_(True)))
        gates = db.session.scalars(select(Gate).where(Gate.event_id == event.id)
                                   .order_by(Gate.name)).all()
        operations.append(dict(event=event, capacity=capacity, reserved=reserved,
                               checked=checked, blocked=blocked, gates=gates,
                               available=max(capacity - reserved - blocked, 0)))
    return render_template("admin/dashboard.html", metrics=metrics, operations=operations)


@admin.get("/events/<int:event_id>/seats")
@_admin_route
def seats(event_id):
    """Display sections, blocked seats and reserved inventory for one event."""
    event = db.get_or_404(Event, event_id)
    inventory = db.session.scalars(
        select(Seat).where(Seat.event_id == event.id)
        .order_by(Seat.section, Seat.row_label, Seat.number)
    ).all()
    active = set(db.session.scalars(
        select(Booking.seat_id).join(Seat).where(
            Seat.event_id == event.id, Booking.status == "reserved"
        )
    ).all())
    sections = defaultdict(list)
    for seat in inventory:
        sections[seat.section].append(seat)
    gates = db.session.scalars(select(Gate).where(Gate.event_id == event.id)
                              .order_by(Gate.name)).all()
    return render_template("admin/seats.html", event=event, sections=sections,
                           active=active, gates=gates, create_form=CreateSectionForm(),
                           rename_form=RenameSectionForm())


@admin.post("/seats/<int:seat_id>/toggle-block")
@_admin_route
def toggle_block(seat_id):
    """Block or unblock a seat; never block one with an active booking."""
    seat = db.get_or_404(Seat, seat_id)
    if not seat.is_blocked:
        booked = db.session.scalar(select(Booking.id).where(
            Booking.seat_id == seat.id, Booking.status == "reserved"
        ).limit(1))
        if booked is not None:
            flash("Cancel the active reservation before blocking this seat.", "error")
            return redirect(url_for("admin.seats", event_id=seat.event_id))
    seat.is_blocked = not seat.is_blocked
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("The seat was just reserved; blocking was not applied.", "error")
        return redirect(url_for("admin.seats", event_id=seat.event_id))
    flash(f"{seat.display_label} {'blocked' if seat.is_blocked else 'unblocked'}.", "success")
    return redirect(url_for("admin.seats", event_id=seat.event_id))


@admin.post("/events/<int:event_id>/sections/create")
@_admin_route
def create_section(event_id):
    """Add a section of numbered seats, up to 20 rows by 30 seats per row."""
    event = db.get_or_404(Event, event_id)
    form = CreateSectionForm()
    if not form.validate_on_submit():
        flash("Invalid section. Use 2-30 characters, 1-20 rows and 1-30 seats per row.", "error")
        return redirect(url_for("admin.seats", event_id=event.id))
    name = form.name.data.strip()
    exists = db.session.scalar(select(Seat.id).where(
        Seat.event_id == event.id, func.lower(Seat.section) == name.lower()
    ).limit(1))
    if exists is not None:
        flash("A section with this name already exists.", "error")
        return redirect(url_for("admin.seats", event_id=event.id))
    gate = db.session.scalar(select(Gate).where(Gate.event_id == event.id)
                             .order_by(Gate.id).limit(1))
    if gate is None:
        gate = Gate(event_id=event.id, name="Gate 1")
        db.session.add(gate)
        db.session.flush()
    for row_index in range(form.rows.data):
        for number in range(1, form.seats_per_row.data + 1):
            db.session.add(Seat(event_id=event.id, gate_id=gate.id, section=name,
                                row_label=chr(65 + row_index), number=number))
    db.session.commit()
    flash(f"Added section {name} with {form.rows.data * form.seats_per_row.data} seats.", "success")
    return redirect(url_for("admin.seats", event_id=event.id))


@admin.post("/events/<int:event_id>/sections/rename")
@_admin_route
def rename_section(event_id):
    """Rename a section without replacing seat IDs or booking relationships."""
    event = db.get_or_404(Event, event_id)
    form = RenameSectionForm()
    if not form.validate_on_submit():
        flash("Invalid section name.", "error")
        return redirect(url_for("admin.seats", event_id=event.id))
    old_name, new_name = form.old_name.data, form.new_name.data.strip()
    rows = db.session.scalars(select(Seat).where(
        Seat.event_id == event.id, Seat.section == old_name
    )).all()
    if not rows:
        abort(404)
    existing = db.session.scalar(select(Seat.id).where(
        Seat.event_id == event.id, func.lower(Seat.section) == new_name.lower(),
        Seat.section != old_name
    ).limit(1))
    if existing is not None:
        flash("The destination section name is already in use.", "error")
    else:
        for seat in rows:
            seat.section = new_name
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("That name would create duplicate seat labels.", "error")
        else:
            flash(f"Section {old_name} renamed to {new_name}.", "success")
    return redirect(url_for("admin.seats", event_id=event.id))


@admin.post("/events/<int:event_id>/sections/<section>/delete")
@_admin_route
def delete_section(event_id, section):
    """Remove an unused section only if none of its seats has booking history."""
    event = db.get_or_404(Event, event_id)
    rows = db.session.scalars(select(Seat).where(
        Seat.event_id == event.id, Seat.section == section
    )).all()
    if not rows:
        abort(404)
    any_booking = db.session.scalar(select(Booking.id).join(Seat).where(
        Seat.event_id == event.id, Seat.section == section
    ).limit(1))
    if any_booking is not None:
        flash("This section has booking history and cannot be deleted.", "error")
    else:
        for seat in rows:
            db.session.delete(seat)
        db.session.commit()
        flash(f"Section {section} deleted.", "success")
    return redirect(url_for("admin.seats", event_id=event.id))


@admin.get("/users")
@_admin_route
def users():
    """Display all accounts and admin-controlled roles."""
    accounts = db.session.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    return render_template("admin/users.html", users=accounts, invite_form=AdminInviteForm())


@admin.post("/users/<int:user_id>/role")
@_admin_route
def change_role(user_id):
    """Update another account's role, preserving the acting admin account."""
    account = db.get_or_404(User, user_id)
    form = RoleForm()
    if not form.validate_on_submit():
        flash("Choose a valid account role.", "error")
    elif current_user.id == account.id:
        flash("You cannot change your own role from the admin panel.", "error")
    elif account.role == "admin" and form.role.data != "admin" and db.session.scalar(
        select(func.count(User.id)).where(User.role == "admin")
    ) <= 1:
        flash("At least one administrator must remain.", "error")
    elif form.role.data == "student" and not account.student_id:
        flash("Assign a unique Student ID before changing this user to student.", "error")
    else:
        if form.role.data == "admin" and account.role != "admin":
            account.set_password(secrets.token_urlsafe(48))
            account.password_ready = False
        account.role = form.role.data
        account.auth_version = (account.auth_version or 0) + 1
        db.session.commit()
        flash(f"Role updated for {account.email}.", "success")
    return redirect(url_for("admin.users"))


@admin.post("/admin-invitations/new")
@limiter.limit("10 per hour")
@_admin_route
def generate_admin_key():
    """Display a newly generated single-use admin key only in this response."""
    form = AdminInviteForm()
    if not form.validate_on_submit():
        abort(400)
    try:
        target_id = int(form.target_user_id.data)
    except (ValueError, TypeError):
        abort(400)
    target = db.session.get(User, target_id)
    if target is None or target.role != "admin":
        abort(400)
    if target.password_ready and request.form.get("confirm_reset") != "yes":
        flash("Reset confirmation required before disabling an existing admin password.", "error")
        return redirect(url_for("admin.users"))
    key = issue_login_key(target, created_by=current_user.id)
    response = render_template("admin/invitation_created.html", key=key, target=target)
    from flask import make_response
    result = make_response(response)
    result.headers["Cache-Control"] = "no-store, private"
    result.headers["Pragma"] = "no-cache"
    return result


@admin.post("/users/<int:user_id>/student-id")
@_admin_route
def change_student_id(user_id):
    """Allow admins to correct existing student IDs without deleting bookings."""
    account = db.get_or_404(User, user_id)
    if account.role != "student":
        flash("Student IDs are managed for student accounts only.", "error")
        return redirect(url_for("admin.users"))
    form = StudentIDForm()
    if not form.validate_on_submit():
        flash("Use a 6–20-character letters/numbers Student ID.", "error")
    else:
        candidate = form.student_id.data.strip().upper()
        existing = db.session.scalar(select(User.id).where(
            User.student_id == candidate, User.id != user_id))
        if existing is not None:
            flash("This Student ID is already in use.", "error")
        else:
            account.student_id = candidate
            try:
                db.session.commit()
                flash("Student ID saved.", "success")
            except IntegrityError:
                db.session.rollback()
                flash("This Student ID is already in use.", "error")
    return redirect(url_for("admin.users"))


@admin.get("/bookings")
@_admin_route
def bookings():
    """Browse booking history with optional event and status filters."""
    status = request.args.get("status", "all")
    if status not in ("all", "reserved", "cancelled"):
        abort(400)
    event_id = request.args.get("event_id", type=int)
    query = select(Booking).join(Seat).options(
        joinedload(Booking.user), joinedload(Booking.seat).joinedload(Seat.event)
    )
    if status != "all":
        query = query.where(Booking.status == status)
    if event_id is not None:
        query = query.where(Seat.event_id == event_id)
    query = query.order_by(Booking.created_at.desc(), Booking.id.desc())
    page = db.paginate(query, page=max(request.args.get("page", 1, type=int), 1),
                       per_page=25, error_out=False)
    events = db.session.scalars(select(Event).order_by(Event.starts_at.desc())).all()
    return render_template("admin/bookings.html", bookings=page.items, page=page,
                           events=events, selected_status=status, selected_event=event_id)


@admin.post("/bookings/<int:booking_id>/cancel")
@_admin_route
def cancel_booking(booking_id):
    """Cancel any active booking as administrator and email its owner."""
    booking = db.get_or_404(Booking, booking_id)
    if booking.status == "cancelled":
        flash("This booking is already cancelled.", "info")
    elif booking.ticket and booking.ticket.status == "checked_in":
        flash("Checked-in tickets cannot be cancelled. Check-in remains in the audit history.", "error")
    else:
        booking.status = "cancelled"
        if booking.ticket:
            booking.ticket.status = "cancelled"
        db.session.commit()
        notify_booking_cancelled(booking)
        flash("Reservation cancelled; owner notification processed.", "success")
    return redirect(url_for("admin.bookings"))


def _set_event_entry(event, is_open):
    """Open/close the event and ALL entrances in a single database commit."""
    event.checkin_enabled = is_open
    for gate in db.session.scalars(select(Gate).where(Gate.event_id == event.id)).all():
        gate.is_open = is_open
    db.session.commit()


@admin.post("/events/<int:event_id>/entry/<action>")
@_admin_route
def set_event_entry(event_id, action):
    if action not in ("open", "close"):
        abort(404)
    event = db.get_or_404(Event, event_id)
    _set_event_entry(event, action == "open")
    flash(f"Stadium entry {'OPEN' if action == 'open' else 'CLOSED'} for {event.title}.", "success")
    return redirect(request.form.get("return_to") if request.form.get("return_to") in
                    (url_for("admin.dashboard"), url_for("main.admin_events"),
                     url_for("admin.gates", event_id=event.id)) else
                    url_for("admin.gates", event_id=event.id))


@admin.post("/events/<int:event_id>/toggle/<gate>")
@_admin_route
def toggle_event_gate(event_id, gate):
    """Compatibility for older event list form; now updates all entrances."""
    if gate not in ("booking", "checkin"):
        abort(404)
    event = db.get_or_404(Event, event_id)
    if gate == "checkin":
        _set_event_entry(event, not event.checkin_enabled)
    else:
        event.booking_enabled = not event.booking_enabled
        db.session.commit()
    flash(f"{gate.title()} state updated for {event.title}.", "success")
    return redirect(url_for("main.admin_events"))


@admin.get("/events/<int:event_id>/gates")
@_admin_route
def gates(event_id):
    event = db.get_or_404(Event, event_id)
    entrances = db.session.scalars(select(Gate).where(Gate.event_id == event.id)
                                   .order_by(Gate.name)).all()
    inventory = db.session.scalars(select(Seat).where(Seat.event_id == event.id)
                                   .order_by(Seat.section, Seat.row_label, Seat.number)).all()
    sections = defaultdict(list)
    for seat in inventory:
        sections[seat.section].append(seat)
    return render_template("admin/gates.html", event=event, gates=entrances, sections=sections)


@admin.post("/events/<int:event_id>/gates")
@_admin_route
def add_gate(event_id):
    event = db.get_or_404(Event, event_id)
    name = " ".join(request.form.get("name", "").strip().split())
    if not 2 <= len(name) <= 40 or not all(c.isalnum() or c in " -_" for c in name):
        flash("Use a gate name of 2–40 letters/numbers.", "error")
    else:
        db.session.add(Gate(event_id=event.id, name=name, is_open=False))
        try:
            db.session.commit()
            flash(f"Added {name}. Assign a section before using this gate.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("This gate name already exists for this event.", "error")
    return redirect(url_for("admin.gates", event_id=event.id))


@admin.post("/events/<int:event_id>/gates/<int:gate_id>/rename")
@_admin_route
def rename_gate(event_id, gate_id):
    gate = db.get_or_404(Gate, gate_id)
    if gate.event_id != event_id:
        abort(404)
    name = " ".join(request.form.get("name", "").strip().split())
    if not 2 <= len(name) <= 40 or not all(c.isalnum() or c in " -_" for c in name):
        flash("Enter a valid gate name.", "error")
    else:
        gate.name = name
        try:
            db.session.commit()
            flash("Gate renamed.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("That gate name already exists.", "error")
    return redirect(url_for("admin.gates", event_id=event_id))


@admin.post("/gates/<int:gate_id>/toggle")
@_admin_route
def toggle_gate(gate_id):
    gate = db.get_or_404(Gate, gate_id)
    gate.is_open = not gate.is_open
    if gate.is_open:
        gate.event.checkin_enabled = True
    else:
        remaining = db.session.scalar(select(Gate.id).where(
            Gate.event_id == gate.event_id, Gate.id != gate.id,
            Gate.is_open.is_(True)).limit(1))
        if remaining is None:
            gate.event.checkin_enabled = False
    db.session.commit()
    flash(f"{gate.name} is now {'OPEN' if gate.is_open else 'CLOSED'}.", "success")
    return redirect(url_for("admin.gates", event_id=gate.event_id))


@admin.post("/events/<int:event_id>/sections/<section>/gate")
@_admin_route
def assign_section_gate(event_id, section):
    event = db.get_or_404(Event, event_id)
    gate_id = request.form.get("gate_id", type=int)
    gate = db.session.get(Gate, gate_id) if gate_id else None
    if gate is None or gate.event_id != event.id:
        abort(400)
    seats = db.session.scalars(select(Seat).where(
        Seat.event_id == event.id, Seat.section == section)).all()
    if not seats:
        abort(404)
    # Prevent moving already-admitted students to another gate mid-event.
    checked = db.session.scalar(select(Ticket.id).join(Booking).where(
        Booking.seat_id.in_([seat.id for seat in seats]), Ticket.status == "checked_in").limit(1))
    if checked is not None:
        flash("Cannot reassign a section containing checked-in tickets.", "error")
    else:
        for seat in seats:
            seat.gate_id = gate.id
        db.session.commit()
        flash(f"{section} now enters through {gate.name}.", "success")
    return redirect(url_for("admin.gates", event_id=event.id))


@admin.post("/tickets/<int:ticket_id>/assign")
@_admin_route
def assign_legacy_ticket(ticket_id):
    """Verify an old multi-seat booking's attendee before issuing any QR."""
    ticket = db.get_or_404(Ticket, ticket_id)
    if ticket.status != "unassigned" or ticket.booking.status != "reserved":
        abort(400)
    from .ticketing import verify_attendee
    sid, name = request.form.get("student_id", ""), request.form.get("student_name", "")
    user, error = verify_attendee(sid, name)
    if error:
        flash(error, "error")
    else:
        ticket.attendee_user_id = user.id
        ticket.attendee_student_id = user.student_id
        ticket.attendee_name = user.full_name
        ticket.status = "active"
        try:
            db.session.commit()
            flash("Legacy booking assigned and QR ticket enabled.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("That student already has an active ticket for this event.", "error")
    return redirect(url_for("admin.bookings"))
