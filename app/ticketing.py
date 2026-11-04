"""Ticket ownership, attendee eligibility and signed QR credential helpers.

Only registered students may hold active tickets. Ticket tokens contain no
personal data; a signed ticket ID + persistent random nonce is verified against
the live database on every check-in.
"""
import re
import secrets
from urllib.parse import urlparse

from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy import select

from . import db
from .models import Ticket, User

_STUDENT_ID = re.compile(r"^[A-Za-z0-9]{6,20}$")


def verify_attendee(student_id, full_name):
    """Require an exact registered student ID and normalized matching name."""
    sid = (student_id or "").strip().upper()
    name = " ".join((full_name or "").strip().split())
    if not _STUDENT_ID.fullmatch(sid) or not 2 <= len(name) <= 120:
        return None, "Enter a valid registered Student ID and full name."
    user = db.session.scalar(select(User).where(User.student_id == sid, User.role == "student"))
    if user is None or " ".join(user.full_name.split()).casefold() != name.casefold():
        return None, "Attendee Student ID and name must match a registered student account."
    return user, None


def resolve_attendees(event_id, booking_user, seat_count, student_ids, names):
    """Validate the whole attendee list before inserting any booking record.

    First seat must belong to the buyer; every additional seat needs another
    registered student's ID and exact name. Each student may hold one active
    ticket at this event, even if somebody else made a booking for them.
    """
    if booking_user.role != "student" or not booking_user.student_id:
        return None, "You need an active student account with a Student ID."
    if seat_count == 1 and not student_ids and not names:
        student_ids, names = [booking_user.student_id], [booking_user.full_name]
    if len(student_ids) != seat_count or len(names) != seat_count:
        return None, "Enter one registered attendee name and Student ID per seat."
    if sum(len(x) for x in student_ids + names) > 1200:
        return None, "Attendee information is too long."
    attendees, ids = [], set()
    for sid, name in zip(student_ids, names):
        student, error = verify_attendee(sid, name)
        if error:
            return None, error
        if student.id in ids:
            return None, "Each seat requires a different student."
        attendees.append(student)
        ids.add(student.id)
    if attendees[0].id != booking_user.id:
        return None, "The first selected seat must be for your own Student ID."
    active = db.session.scalar(select(Ticket.id).where(
        Ticket.event_id == event_id,
        Ticket.attendee_user_id.in_(ids),
        Ticket.status.in_(["active", "checked_in"])
    ).limit(1))
    if active is not None:
        return None, "One of these students already has a ticket for this event."
    return attendees, None


def create_tickets_for_bookings(event, bookings, attendees):
    """Attach one ticket to each booking in the same DB transaction."""
    for booking, student in zip(bookings, attendees):
        db.session.add(Ticket(
            booking_id=booking.id, event_id=event.id,
            attendee_user_id=student.id,
            attendee_name=student.full_name,
            attendee_student_id=student.student_id,
            nonce=secrets.token_urlsafe(24), status="active",
        ))


def _serializer():
    secret = current_app.config.get("TICKET_SIGNING_KEY")
    if not secret:
        raise RuntimeError("Stable TICKET_SIGNING_KEY must be configured.")
    return URLSafeSerializer(secret, salt="cstbs.v53.stadium-entry")


def ticket_token(ticket):
    return _serializer().dumps({"t": ticket.id, "n": ticket.nonce})


def resolve_ticket_token(token):
    """Return a verified, current ticket, or None for tampered/unknown codes."""
    if not isinstance(token, str) or len(token) > 512 or not token:
        return None
    try:
        claims = _serializer().loads(token)
    except (BadSignature, ValueError, TypeError):
        return None
    if not isinstance(claims, dict) or type(claims.get("t")) is not int:
        return None
    ticket = db.session.get(Ticket, claims["t"])
    if ticket is None or not secrets.compare_digest(str(ticket.nonce), str(claims.get("n", ""))):
        return None
    return ticket


def token_from_scan(value, host):
    """Accept our QR URL or a copied raw token, never an external site."""
    raw = (value or "").strip()
    if len(raw) > 1000 or not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        url = urlparse(raw)
        if url.netloc != host or url.query or url.fragment:
            return None
        raw = url.path.rsplit("/entry/verify/", 1)[-1] if url.path.startswith("/entry/verify/") else ""
    return raw if re.fullmatch(r"[A-Za-z0-9._-]{10,512}", raw) else None
