"""Illustrative events loaded explicitly with ``flask seed-events``."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select

from . import db
from .models import Event


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
        db.session.add(Event(
            title=title, category=category, venue=venue, price=Decimal(price),
            description=description,
            starts_at=datetime.combine(event_date, time(hour=hour, minute=minute)),
        ))
    db.session.commit()
    return len(samples)
