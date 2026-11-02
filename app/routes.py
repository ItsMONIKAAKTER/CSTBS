"""Public event browsing, account authentication, and admin event CRUD."""

from datetime import datetime
from functools import wraps

from flask import abort, Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import db
from .forms import DeleteEventForm, EventForm, LoginForm, RegisterForm
from .models import Event, User

main = Blueprint("main", __name__)


def admin_required(view):
    """Return HTTP 403 for logged-in users who are not administrators."""
    @wraps(view)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return decorated


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
    return render_template("event_detail.html", event=event)


@main.route("/register", methods=["GET", "POST"])
def register():
    """Create a student account and start an authenticated session."""
    if current_user.is_authenticated:
        return redirect(url_for("main.account"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if db.session.scalar(select(User.id).where(User.email == email)) is not None:
            form.email.errors.append("An account with this email already exists.")
        else:
            user = User(full_name=form.full_name.data.strip(), email=email, role="student")
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:  # Handles concurrent submissions racing on email.
                db.session.rollback()
                form.email.errors.append("An account with this email already exists.")
            else:
                login_user(user)
                flash("Account created. Welcome to CSTBS!", "success")
                return redirect(url_for("main.account"))
    return render_template("register.html", form=form)


@main.route("/login", methods=["GET", "POST"])
def login():
    """Verify a stored password hash and authenticate the account."""
    if current_user.is_authenticated:
        return redirect(url_for("main.account"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(select(User).where(User.email == email))
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
    logout_user()
    flash("You have signed out.", "info")
    return redirect(url_for("main.index"))


@main.get("/account")
@login_required
def account():
    """Display the logged-in user's basic account information."""
    return render_template("account.html")


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
        db.session.add(event)
        db.session.commit()
        flash("Event created successfully.", "success")
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
    if event.seats:
        flash("This event has assigned seats and cannot be deleted.", "error")
    else:
        db.session.delete(event)
        db.session.commit()
        flash("Event deleted successfully.", "success")
    return redirect(url_for("main.admin_events"))
