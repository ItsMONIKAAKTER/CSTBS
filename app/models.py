"""Persistent account and event models; seats/bookings remain V1 placeholders."""

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

ROLES = ("student", "staff", "admin")


def utc_now():
    """Return a naive UTC value suitable for the existing SQLite schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    """Registered user with a securely hashed password and server-set role."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'staff', 'admin')", name="ck_user_role"),)

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student", server_default="student")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    bookings = db.relationship("Booking", back_populates="user")

    def set_password(self, password):
        """Hash a plaintext password; never store the original value."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Validate a candidate password against the saved hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """Whether this user may access event-management endpoints."""
        return self.role == "admin"


class Event(db.Model):
    """Event available in the public catalog and managed by administrators."""

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
    """V1 seat schema retained for backward compatibility; no seat UI yet."""

    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("event_id", "section", "row_label", "number", name="uq_event_seat"),
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
    """V1 booking schema retained; ticket bookings are outside Version 2."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("status IN ('reserved', 'cancelled')", name="ck_booking_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="reserved")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="bookings")
    seat = db.relationship("Seat", back_populates="bookings")
