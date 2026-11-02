"""Initial database schema; booking operations are outside Version 1."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, UniqueConstraint

from . import db


def utc_now():
    """Return a naive UTC timestamp for SQLite's DateTime storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    """A future account holder; no registration/authentication is implemented."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    bookings = db.relationship("Booking", back_populates="user")


class Event(db.Model):
    """A stadium event displayed in the public catalog."""

    __tablename__ = "events"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_event_price"),)

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    venue = db.Column(db.String(120), nullable=False)
    starts_at = db.Column(db.DateTime, index=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    seats = db.relationship("Seat", back_populates="event")


class Seat(db.Model):
    """A uniquely located seat within one event."""

    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "section", "row_label", "number", name="uq_event_seat"
        ),
        CheckConstraint("number > 0", name="ck_seat_number_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    section = db.Column(db.String(30), nullable=False)
    row_label = db.Column(db.String(10), nullable=False)
    number = db.Column(db.Integer, nullable=False)

    event = db.relationship("Event", back_populates="seats")
    bookings = db.relationship("Booking", back_populates="seat")


class Booking(db.Model):
    """Future reservation record; the app does not create bookings in V1."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved', 'cancelled')", name="ck_booking_status"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="reserved")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="bookings")
    seat = db.relationship("Seat", back_populates="bookings")
