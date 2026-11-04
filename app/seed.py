"""Illustrative events loaded explicitly with ``flask seed-events``."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select

from . import db
from .models import Event
from .seating import add_default_seats


def seed_demo_events():
    """Insert four events only if the catalog is empty; return inserted count."""
    if db.session.execute(select(Event.id).limit(1)).first():
        return 0

    samples = [
        (7, 18, 30, "Campus Football Night", "Football", "Main Stadium", "18.00",
         "Cheer for the home team under the stadium lights. Enjoy a spirited evening of campus football, student traditions, and community energy."),
        (12, 10, 0, "Track & Field Showcase", "Athletics", "Athletics Oval", "0.00",
         "Watch student athletes compete in sprints, relays, and field events. A welcoming daytime gathering for the whole campus."),
        (19, 16, 0, "Alumni Soccer Classic", "Soccer", "Main Stadium", "12.00",
         "Celebrate a friendly match that brings alumni and current students together for an afternoon of stadium excitement."),
        (26, 19, 0, "Stadium Music Fest", "Music", "Main Stadium", "24.00",
         "Experience live performances from student bands and campus artists at an open-air evening show."),
    ]

    for days, hour, minute, title, category, venue, price, description in samples:
        event_date = date.today() + timedelta(days=days)
        event = Event(
            title=title, category=category, venue=venue, price=Decimal(price),
            description=description,
            starts_at=datetime.combine(event_date, time(hour=hour, minute=minute)),
        )
        db.session.add(event)
        add_default_seats(event)
    db.session.commit()
    return len(samples)


def seed_demo_environment():
    """Opt-in development-only sample accounts, bookings and blocked inventory.

    Password is supplied through local DEMO_SEED_PASSWORD, never source code.
    Existing accounts are neither re-passworded nor elevated. Repeated runs
    do not create duplicate demo reservations.
    """
    import os
    from flask import current_app
    from .models import Booking, Seat, User

    if current_app.config.get("APP_ENV") == "production":
        raise ValueError("Demo accounts cannot be seeded in production.")
    password = os.getenv("DEMO_SEED_PASSWORD", "")
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Set DEMO_SEED_PASSWORD in your private .env (12-128 characters) first.")
    seed_demo_events()  # Seeds only an empty catalog, never replaces real events.
    demo_accounts = [
        ("demo.student@campus.example", "Demo Student", "student"),
        ("demo.staff@campus.example", "Demo Staff", "staff"),
        ("demo.admin@campus.example", "Demo Administrator", "admin"),
    ]
    accounts = {}
    for email, name, role in demo_accounts:
        found = db.session.scalar(select(User).where(User.email == email))
        if found is not None and (found.role != role or not found.check_password(password)):
            raise ValueError(f"Demo email {email} already exists with different credentials or role.")
        if found is None:
            found = User(email=email, full_name=name, role=role)
            found.set_password(password)
            db.session.add(found)
        accounts[role] = found
    db.session.flush()

    demo_event = db.session.scalar(select(Event).where(Event.title == "Campus Football Night")
                                   .order_by(Event.id).limit(1))
    if demo_event is None:
        db.session.commit()
        return "Demo accounts created; no matching sample event available for booking data."
    seat_rows = db.session.scalars(select(Seat).where(Seat.event_id == demo_event.id,
        Seat.section == "Main").order_by(Seat.row_label, Seat.number).limit(8)).all()
    inserts = 0
    desired = [(0, "student", "reserved"), (1, "staff", "reserved"),
               (2, "student", "cancelled")]
    for offset, role, status in desired:
        if offset >= len(seat_rows):
            continue
        seat = seat_rows[offset]
        already = db.session.scalar(select(Booking.id).where(
            Booking.seat_id == seat.id, Booking.user_id == accounts[role].id).limit(1))
        seat_taken = db.session.scalar(select(Booking.id).where(
            Booking.seat_id == seat.id, Booking.status == "reserved").limit(1))
        if already is None and seat_taken is None and not seat.is_blocked:
            db.session.add(Booking(user_id=accounts[role].id, seat_id=seat.id,
                status=status, price_at_booking=demo_event.price))
            inserts += 1
    # Two visible blocked seats, not reserved and not present in history.
    for seat in seat_rows[3:5]:
        any_reserved = db.session.scalar(select(Booking.id).where(
            Booking.seat_id == seat.id, Booking.status == "reserved").limit(1))
        if any_reserved is None:
            seat.is_blocked = True
    db.session.commit()
    return (f"Demo ready: {len(demo_accounts)} local accounts; "
            f"{inserts} new sample booking records. Do not use these credentials in production.")
