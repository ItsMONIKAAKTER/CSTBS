"""Public event browsing, account authentication, and admin event CRUD."""

from datetime import datetime

from flask import abort, Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import db, limiter
from .authz import admin_required
from .notifications import notify_booking_confirmed, notify_booking_cancelled
from .forms import DeleteEventForm, EventForm, LoginForm, RegisterForm, AdminLoginForm, AdminActivationForm, StudentIDForm
from .models import Booking, Event, Seat, Ticket, User, utc_now
from .seating import MAX_SEATS_PER_BOOKING, add_default_seats, reserved_seat_ids
from .admin_keys import consume_login_key
from .ticketing import resolve_attendees, create_tickets_for_bookings

main = Blueprint("main", __name__)


def safe_next_url(target):
    """Allow internal absolute-path redirects only, avoiding open redirects."""
    if (target and target.startswith("/") and not target.startswith("//")
            and "\\" not in target and not any(ord(ch) < 32 for ch in target)):
        return target
    return None


@main.get("/")
def index():
    """Display the landing page and up to three future events."""
    events = db.session.scalars(
        select(Event)
        .where(Event.starts_at >= datetime.now())
        .order_by(Event.starts_at)
        .limit(3)
    ).all()
    return render_template("index.html", featured_events=events)


@main.get("/events")
def events():
    """Show all events publicly, regardless of authentication state."""
    event_list = db.session.scalars(select(Event).order_by(Event.starts_at)).all()
    return render_template("events.html", events=event_list)


@main.get("/events/<int:event_id>")
def event_detail(event_id):
    """Render a public event detail page."""
    event = db.get_or_404(Event, event_id)
    return render_template("event_detail.html", event=event, now=datetime.now())


@main.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute; 25 per hour", methods=["POST"])
def register():
    """Create a student account and start an authenticated session."""
    if current_user.is_authenticated:
        return redirect(url_for("main.account"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        student_id = form.student_id.data.strip().upper()
        if db.session.scalar(select(User.id).where(User.email == email)) is not None:
            form.email.errors.append("An account with this email already exists.")
        elif db.session.scalar(select(User.id).where(User.student_id == student_id)) is not None:
            form.student_id.errors.append("This Student ID is already registered.")
        else:
            user = User(full_name=form.full_name.data.strip(), email=email,
                        student_id=student_id, role="student")
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:  # Handles concurrent submissions racing on email.
                db.session.rollback()
                form.email.errors.append("Email or Student ID is already registered.")
            else:
                login_user(user)
                flash("Account created. Welcome to CSTBS!", "success")
                return redirect(url_for("main.account"))
    return render_template("register.html", form=form)


@main.get("/register/admin")
def legacy_admin_register_redirect():
    """Retired V5.1 admin registration link never registers an administrator."""
    return redirect(url_for("main.admin_login"), code=302)


@main.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def admin_login():
    """Admin password login; keys are only used for initial activation/reset."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "main.account"))
    form = AdminLoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(select(User).where(User.email == email, User.role == "admin"))
        if user and user.password_ready and user.check_password(form.password.data):
            session.clear()
            login_user(user, fresh=True)
            session["admin_auth_version"] = user.auth_version
            flash("Welcome back to the stadium dashboard.", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials or account not activated. First-time admins must activate with their key.", "error")
    response = make_no_store(render_template("admin_login.html", form=form))
    return response


@main.route("/admin/activate", methods=["GET", "POST"])
@limiter.limit("5 per minute; 15 per hour", methods=["POST"])
def admin_activate():
    """Consume a 20-minute single-use key AND set the first real password."""
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard" if current_user.is_admin else "main.account"))
    form = AdminActivationForm()
    if form.validate_on_submit():
        user = consume_login_key(form.email.data, form.admin_key.data, form.password.data)
        if user:
            session.clear()
            login_user(user, fresh=True)
            session["admin_auth_version"] = user.auth_version
            flash("Account activated. Use email and password for future logins.", "success")
            return redirect(url_for("admin.dashboard"))
        form.admin_key.errors.append("Key invalid, expired or already used. Request a fresh activation key.")
    return make_no_store(render_template("admin_activate.html", form=form))


def make_no_store(page):
    from flask import make_response
    response = make_response(page)
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@main.post("/account/student-id")
@login_required
def update_student_id():
    """Existing student accounts can provide a missing unique university ID."""
    if current_user.role != "student":
        abort(403)
    form = StudentIDForm()
    if form.validate_on_submit():
        candidate = form.student_id.data.strip().upper()
        found = db.session.scalar(select(User.id).where(
            User.student_id == candidate, User.id != current_user.id))
        if found is not None:
            flash("Student ID is already registered.", "error")
        else:
            current_user.student_id = candidate
            try:
                db.session.commit()
                flash("Student ID updated.", "success")
            except IntegrityError:
                db.session.rollback()
                flash("Student ID is already registered.", "error")
    else:
        flash("Student ID must contain 6–20 letters or numbers.", "error")
    return redirect(url_for("main.account"))


@main.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute; 25 per hour", methods=["POST"])
def login():
    """Verify a stored password hash and authenticate the account."""
    if current_user.is_authenticated:
        return redirect(url_for("main.account"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(select(User).where(User.email == email))
        if user and user.role == "admin":
            flash("Administrators sign in with a one-time key at Admin Login.", "info")
            return redirect(url_for("main.admin_login"))
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Signed in successfully.", "success")
            return redirect(safe_next_url(request.args.get("next")) or url_for("main.account"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", form=form)


@main.post("/logout")
@login_required
def logout():
    """Terminate the session; global CSRF protection requires a valid token."""
    session.pop("pending_booking", None)
    logout_user()
    flash("You have signed out.", "info")
    return redirect(url_for("main.index"))


@main.get("/account")
@login_required
def account():
    """Display the logged-in user's basic account information."""
    return render_template("account.html", student_id_form=StudentIDForm())


@main.get("/admin/events")
@login_required
@admin_required
def admin_events():
    """List events and provide editing/deletion controls to administrators."""
    event_list = db.session.scalars(select(Event).order_by(Event.starts_at)).all()
    return render_template(
        "admin/events.html", events=event_list, delete_form=DeleteEventForm()
    )


@main.route("/admin/events/new", methods=["GET", "POST"])
@login_required
@admin_required
def admin_event_create():
    """Create an event from a validated, CSRF-protected form."""
    form = EventForm()
    if form.validate_on_submit():
        event = Event()
        form.populate_obj(event)
        event.price = 0  # All university reservations are free.
        db.session.add(event)
        add_default_seats(event)
        db.session.commit()
        flash("Event created with 60 seats.", "success")
        return redirect(url_for("main.event_detail", event_id=event.id))
    return render_template("admin/event_form.html", form=form, heading="Create event")


@main.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_event_edit(event_id):
    """Edit a previously created event."""
    event = db.get_or_404(Event, event_id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        form.populate_obj(event)
        event.price = 0
        db.session.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("main.event_detail", event_id=event.id))
    return render_template("admin/event_form.html", form=form, heading="Edit event", event=event)


@main.post("/admin/events/<int:event_id>/delete")
@login_required
@admin_required
def admin_event_delete(event_id):
    """Delete an event without silently deleting related seat/booking records."""
    form = DeleteEventForm()
    if not form.validate_on_submit():
        abort(400)
    event = db.get_or_404(Event, event_id)
    # Preserve historical bookings, including cancelled bookings, for auditing.
    any_booking = db.session.scalar(
        select(Booking.id).join(Seat).where(Seat.event_id == event.id).limit(1)
    )
    if any_booking is not None:
        flash("This event has booking history and cannot be deleted.", "error")
    else:
        for seat in list(event.seats):
            db.session.delete(seat)
        db.session.delete(event)
        db.session.commit()
        flash("Event deleted successfully.", "success")
    return redirect(url_for("main.admin_events"))


# V3 reservation journey. A Booking reserves exactly one seat; multiple rows
# commit together as a single user's multi-seat submission.

def _requested_seats(event, raw):
    """Validate client IDs, event ownership and fresh occupancy; return seats.

    Returns (seats, message). Client-side disabled buttons are never trusted.
    """
    if not isinstance(raw, str) or len(raw) > 120:
        return None, "Choose between 1 and 6 seats."
    parts = raw.split(",")
    if (not 1 <= len(parts) <= MAX_SEATS_PER_BOOKING
            or any(not item.isascii() or not item.isdecimal() for item in parts)):
        return None, "Choose between 1 and 6 valid seats."
    ids = [int(part) for part in parts]
    if len(set(ids)) != len(ids):
        return None, "Each seat can only be selected once."
    seats = db.session.scalars(
        select(Seat).where(Seat.event_id == event.id, Seat.id.in_(ids))
        .order_by(Seat.row_label, Seat.number)
    ).all()
    if len(seats) != len(ids):
        return None, "Some seats do not belong to this event."
    if any(seat.is_blocked for seat in seats):
        return None, "A selected seat is blocked by the stadium administrator."
    if reserved_seat_ids(event.id).intersection(ids):
        return None, "One or more seats have just been reserved. Please choose again."
    return seats, None


def _future_event(event):
    """Do not accept new reservations after the advertised event start."""
    if event.starts_at <= datetime.now() or not event.booking_enabled:
        flash("Reservations have closed for this event.", "error")
        return False
    return True


@main.get("/events/<int:event_id>/seats")
@login_required
def seat_map(event_id):
    """Interactive seat selection, backed by the current SQLite inventory."""
    event = db.get_or_404(Event, event_id)
    if current_user.role != "student":
        abort(403)
    if not current_user.student_id:
        flash("Add your Student ID before reserving a ticket.", "error")
        return redirect(url_for("main.account"))
    seats = db.session.scalars(
        select(Seat).where(Seat.event_id == event.id)
        .order_by(Seat.row_label, Seat.number)
    ).all()
    return render_template("seat_map.html", event=event, seats=seats,
                           occupied=reserved_seat_ids(event.id),
                           blocked={seat.id for seat in seats if seat.is_blocked},
                           booking_open=event.starts_at > datetime.now() and event.booking_enabled,
                           max_seats=MAX_SEATS_PER_BOOKING)


@main.get("/api/events/<int:event_id>/seats")
@limiter.limit("60 per minute")
def event_seat_availability(event_id):
    """Return current seat occupancy; poll every 5s for near-real-time state."""
    event = db.get_or_404(Event, event_id)
    total = db.session.scalar(
        select(db.func.count(Seat.id)).where(Seat.event_id == event.id)
    )
    occupied = sorted(reserved_seat_ids(event.id))
    blocked = sorted(db.session.scalars(select(Seat.id).where(
        Seat.event_id == event.id, Seat.is_blocked.is_(True))).all())
    result = jsonify(event_id=event.id, reserved_seat_ids=occupied,
                     blocked_seat_ids=blocked,
                     available=total - len(set(occupied) | set(blocked)), total=total,
                     booking_open=event.starts_at > datetime.now() and event.booking_enabled)
    result.headers["Cache-Control"] = "no-store, max-age=0"
    return result


@main.post("/events/<int:event_id>/booking/review")
@login_required
def booking_review(event_id):
    """Review selected seats and total before the user confirms a write."""
    event = db.get_or_404(Event, event_id)
    if current_user.role != "student" or not current_user.student_id:
        abort(403)
    session.pop("pending_booking", None)
    if not _future_event(event):
        return redirect(url_for("main.seat_map", event_id=event.id))
    seats, error = _requested_seats(event, request.form.get("seat_ids"))
    if error:
        flash(error, "error")
        return redirect(url_for("main.seat_map", event_id=event.id))
    session["pending_booking"] = {"event_id": event.id,
                                  "seat_ids": [seat.id for seat in seats]}
    return render_template("booking_review.html", event=event, seats=seats,
                           total=0, student=current_user)


@main.post("/events/<int:event_id>/booking/confirm")
@limiter.limit("12 per minute")
@login_required
def booking_confirm(event_id):
    """Atomically create reservations with a DB-level unique active-seat guard."""
    event = db.get_or_404(Event, event_id)
    if current_user.role != "student" or not current_user.student_id:
        abort(403)
    pending = session.pop("pending_booking", None)
    if not pending or pending.get("event_id") != event.id:
        flash("Select seats and review them before confirming.", "error")
        return redirect(url_for("main.seat_map", event_id=event.id))
    if not _future_event(event):
        return redirect(url_for("main.seat_map", event_id=event.id))
    seats, error = _requested_seats(event, ",".join(str(i) for i in pending["seat_ids"]))
    if error:
        flash(error, "error")
        return redirect(url_for("main.seat_map", event_id=event.id))
    attendees, attendee_error = resolve_attendees(
        event.id, current_user, len(seats),
        request.form.getlist("attendee_student_id"),
        request.form.getlist("attendee_name"),
    )
    if attendee_error:
        flash(attendee_error, "error")
        return redirect(url_for("main.seat_map", event_id=event.id))
    bookings = [Booking(user_id=current_user.id, seat_id=seat.id,
                        status="reserved", price_at_booking=0) for seat in seats]
    try:
        db.session.add_all(bookings)
        db.session.flush()
        create_tickets_for_bookings(event, bookings, attendees)
        db.session.commit()
    except IntegrityError:
        # The partial unique index wins if somebody booked during confirmation.
        db.session.rollback()
        flash("A seat or attendee was already reserved. Nothing was booked. Please try again.", "error")
        return redirect(url_for("main.seat_map", event_id=event.id))
    notify_booking_confirmed(current_user, event, bookings)
    flash(f"Booking confirmed for {len(bookings)} seat(s).", "success")
    return redirect(url_for("main.booking_history"))


@main.get("/bookings")
@login_required
def booking_history():
    """Show the current user's active and cancelled one-seat reservations."""
    bookings = db.session.scalars(
        select(Booking).join(Seat).join(Event).outerjoin(Ticket, Ticket.booking_id == Booking.id)
        .where((Booking.user_id == current_user.id) | (Ticket.attendee_user_id == current_user.id))
        .order_by(Booking.created_at.desc(), Booking.id.desc())
    ).all()
    return render_template("booking_history.html", bookings=bookings)


@main.post("/bookings/<int:booking_id>/cancel")
@login_required
def cancel_booking(booking_id):
    """Permit only the owner to cancel; preserve cancelled records."""
    booking = db.session.scalar(
        select(Booking).outerjoin(Ticket, Ticket.booking_id == Booking.id)
        .where(Booking.id == booking_id,
            (Booking.user_id == current_user.id) | (Ticket.attendee_user_id == current_user.id))
    )
    if booking is None:
        abort(404)  # Hide other users' reservation IDs.
    if booking.status != "reserved":
        flash("This reservation is already cancelled.", "info")
    elif booking.ticket and booking.ticket.status == "checked_in":
        flash("A checked-in ticket cannot be cancelled.", "error")
    else:
        booking.status = "cancelled"
        if booking.ticket:
            booking.ticket.status = "cancelled"
        db.session.commit()
        notify_booking_cancelled(booking)
        flash(f"Cancelled seat {booking.seat.label} for {booking.event.title}.", "success")
    return redirect(url_for("main.booking_history"))
