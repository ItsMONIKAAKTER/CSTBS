"""CSTBS accounts, event inventory, and per-seat booking records.

A booking reserves exactly one seat. Multi-seat checkout saves several bookings
in one database transaction. Cancellation retains the row as audit history.
"""

from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

ROLES = ("student", "staff", "admin")


def utc_now():
    """Naive UTC timestamps, consistent with the existing SQLite database."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    """Account with hashed password, server-controlled role, and bookings."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'staff', 'admin')", name="ck_user_role"),)

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, index=True, nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=True)  # Existing V5 accounts may be empty.
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student", server_default="student")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    bookings = db.relationship("Booking", back_populates="user", order_by="Booking.created_at.desc()")

    def set_password(self, password):
        """Store a one-way password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check a plaintext candidate against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class AdminInvitation(db.Model):
    """Hashed, expiring, single-use login key tied to an administrator."""

    __tablename__ = "admin_invitations"
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    bootstrap = db.Column(db.Boolean, nullable=False, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    used_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)


class Event(db.Model):
    """Public event, including its assigned seating inventory."""

    __tablename__ = "events"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_event_price"),)

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    venue = db.Column(db.String(120), nullable=False)
    starts_at = db.Column(db.DateTime, index=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    seats = db.relationship("Seat", back_populates="event", order_by="(Seat.row_label, Seat.number)")


class Seat(db.Model):
    """A physical seat allocated to exactly one event."""

    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("event_id", "section", "row_label", "number", name="uq_event_seat"),
        CheckConstraint("number > 0", name="ck_seat_number_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    section = db.Column(db.String(30), nullable=False)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    row_label = db.Column(db.String(10), nullable=False)
    number = db.Column(db.Integer, nullable=False)

    event = db.relationship("Event", back_populates="seats")
    bookings = db.relationship("Booking", back_populates="seat", order_by="Booking.created_at.desc()")

    @property
    def label(self):
        return f"{self.row_label}{self.number}"

    @property
    def display_label(self):
        """Unambiguous seat name across multiple sections."""
        return f"{self.section} · {self.label}"


class Booking(db.Model):
    """One user's claim to one seat; cancelled records stay in history.

    The partial unique index permits multiple cancelled history records but
    never more than one active reservation for a seat, even with racing POSTs.
    """

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("status IN ('reserved', 'cancelled')", name="ck_booking_status"),
        Index("uq_active_booking_per_seat", "seat_id", unique=True,
              sqlite_where=text("status = 'reserved'")),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="reserved")
    price_at_booking = db.Column(db.Numeric(10, 2), nullable=False, server_default="0")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="bookings")
    seat = db.relationship("Seat", back_populates="bookings")

    @property
    def event(self):
        return self.seat.event
