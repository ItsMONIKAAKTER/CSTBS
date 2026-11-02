"""Default seat inventory and availability helpers for Version 3."""

from sqlalchemy import select

from . import db
from .models import Booking, Event, Seat

ROWS = "ABCDEF"
SEATS_PER_ROW = 10
MAX_SEATS_PER_BOOKING = 6


def add_default_seats(event):
    """Assign 60 general-admission labelled seats to a newly created event."""
    for row in ROWS:
        for number in range(1, SEATS_PER_ROW + 1):
            db.session.add(Seat(event=event, section="Main", row_label=row, number=number))


def backfill_empty_event_seats():
    """Populate seatless V2 events without touching existing custom seat maps."""
    seatless_events = db.session.scalars(
        select(Event).where(~Event.seats.any())
    ).all()
    for event in seatless_events:
        add_default_seats(event)
    if seatless_events:
        db.session.commit()
    return len(seatless_events)


def reserved_seat_ids(event_id):
    """Freshly query active seat allocations for an event."""
    return set(db.session.scalars(
        select(Booking.seat_id).join(Seat, Booking.seat_id == Seat.id)
        .where(Seat.event_id == event_id, Booking.status == "reserved")
    ).all())
