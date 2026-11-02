"""Page routes for the read-only catalog and UI-only account forms."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for
from sqlalchemy import select

from . import db
from .forms import LoginForm, RegisterForm
from .models import Event

main = Blueprint("main", __name__)


@main.get("/")
def index():
    """Show the landing page and three upcoming demo events."""
    events = db.session.scalars(
        select(Event)
        .where(Event.starts_at >= datetime.now())
        .order_by(Event.starts_at)
        .limit(3)
    ).all()
    return render_template("index.html", featured_events=events)


@main.get("/events")
def events():
    """List all demo events in chronological order."""
    event_list = db.session.scalars(select(Event).order_by(Event.starts_at)).all()
    return render_template("events.html", events=event_list)


@main.get("/events/<int:event_id>")
def event_detail(event_id):
    """Show details for one event, or a 404 for an unknown ID."""
    event = db.get_or_404(Event, event_id)
    return render_template("event_detail.html", event=event)


@main.route("/login", methods=["GET", "POST"])
def login():
    """Validate demo form inputs without checking or storing credentials."""
    form = LoginForm()
    if form.validate_on_submit():
        flash("Sign-in is a preview only; authentication is not enabled in V1.", "info")
        return redirect(url_for("main.login"))
    return render_template("login.html", form=form)


@main.route("/register", methods=["GET", "POST"])
def register():
    """Validate demo form inputs without creating a user account."""
    form = RegisterForm()
    if form.validate_on_submit():
        flash("Registration is a preview only; no account was created.", "info")
        return redirect(url_for("main.register"))
    return render_template("register.html", form=form)
