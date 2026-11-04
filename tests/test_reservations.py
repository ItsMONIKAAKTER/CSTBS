"""V3 Flask integration tests: seat ownership, availability, races, cancellation."""

import re
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import Booking, Event, Seat, User
from app.seating import MAX_SEATS_PER_BOOKING


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "v3-test-key-only",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        self.other_client = self.app.test_client()
        self.user = User(full_name="Student One", email="one@example.edu", role="student")
        self.user.set_password("SecurePassword123")
        self.other = User(full_name="Student Two", email="two@example.edu", role="student")
        self.other.set_password("SecurePassword123")
        event = Event(title="Campus Test Derby", category="Football", description="A great game.",
                      venue="Main Stadium", starts_at=datetime.now() + timedelta(days=5),
                      price=Decimal("15.00"))
        db.session.add_all([self.user, self.other, event])
        db.session.flush()
        self.event_id = event.id
        self.user_id = self.user.id
        self.other_id = self.other.id
        self.seats = [Seat(event_id=event.id, section="Main", row_label="A", number=i)
                      for i in range(1, 9)]
        db.session.add_all(self.seats)
        db.session.commit()
        self.ids = [seat.id for seat in self.seats]

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def csrf(self, client, path):
        response = client.get(path)
        self.assertEqual(response.status_code, 200)
        token = re.search(rb'name="csrf_token"[^>]+value="([^"]+)"', response.data)
        self.assertIsNotNone(token)
        return token.group(1).decode()

    def login(self, client, email):
        return client.post("/login", data={"csrf_token": self.csrf(client, "/login"),
                        "email": email, "password": "SecurePassword123"})

    def review(self, client, ids):
        path = f"/events/{self.event_id}/seats"
        return client.post(f"/events/{self.event_id}/booking/review", data={
            "csrf_token": self.csrf(client, path), "seat_ids": ",".join(map(str, ids))
        })

    def confirm(self, client):
        return client.post(f"/events/{self.event_id}/booking/confirm", data={
            "csrf_token": self.csrf(client, f"/events/{self.event_id}/seats")
        })

    def test_seat_map_protected_and_api_public(self):
        self.assertEqual(self.client.get(f"/events/{self.event_id}/seats").status_code, 302)
        response = self.client.get(f"/api/events/{self.event_id}/seats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["total"], 8)
        self.assertEqual(response.json["available"], 8)
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        self.login(self.client, "one@example.edu")
        self.assertIn(b"Stadium seating", self.client.get(f"/events/{self.event_id}/seats").data)

    def test_review_then_confirm_multiple_seats_atomically(self):
        self.login(self.client, "one@example.edu")
        review = self.review(self.client, self.ids[:2])
        self.assertEqual(review.status_code, 200)
        self.assertIn("¥0.00".encode(), review.data)
        result = self.confirm(self.client)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))), 2)
        history = self.client.get("/bookings")
        self.assertIn(b"Campus Test Derby", history.data)
        self.assertIn(b"A1", history.data)
        self.assertIn(b"A2", history.data)
        self.assertEqual(set(self.client.get(f"/api/events/{self.event_id}/seats").json["reserved_seat_ids"]),
                         set(self.ids[:2]))
        self.assertEqual(self.confirm(self.client).status_code, 302)  # no replay
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))), 2)

    def test_cancel_own_booking_releases_seat_and_preserves_history(self):
        self.login(self.client, "one@example.edu")
        self.review(self.client, self.ids[:1]); self.confirm(self.client)
        booking = db.session.scalar(select(Booking))
        self.assertEqual(self.other_client.get("/bookings").status_code, 302)
        self.login(self.other_client, "two@example.edu")
        forged = self.other_client.post(f"/bookings/{booking.id}/cancel", data={
            "csrf_token": self.csrf(self.other_client, "/bookings")
        })
        self.assertEqual(forged.status_code, 404)
        self.assertEqual(booking.status, "reserved")
        cancelled = self.client.post(f"/bookings/{booking.id}/cancel", data={
            "csrf_token": self.csrf(self.client, "/bookings")
        })
        self.assertEqual(cancelled.status_code, 302)
        self.assertEqual(booking.status, "cancelled")
        self.assertEqual(self.client.get(f"/api/events/{self.event_id}/seats").json["available"], 8)
        self.review(self.other_client, self.ids[:1]); self.confirm(self.other_client)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))), 2)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id)).where(Booking.status == "reserved")), 1)

    def test_reserved_seat_race_between_review_and_confirmation(self):
        self.login(self.client, "one@example.edu")
        self.login(self.other_client, "two@example.edu")
        self.assertEqual(self.review(self.client, self.ids[:1]).status_code, 200)
        self.assertEqual(self.review(self.other_client, self.ids[:1]).status_code, 200)
        self.confirm(self.client)
        result = self.confirm(self.other_client)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))), 1)

    def test_duplicate_and_outside_event_seats_are_rejected(self):
        self.login(self.client, "one@example.edu")
        for ids in ([self.ids[0], self.ids[0]], self.ids[:MAX_SEATS_PER_BOOKING + 1], [-1]):
            self.assertEqual(self.review(self.client, ids).status_code, 302)
        other_event = Event(title="Other", category="Music", description="Different",
                            venue="Park", price=Decimal("0"),
                            starts_at=datetime.now() + timedelta(days=3))
        db.session.add(other_event); db.session.flush()
        other_seat = Seat(event_id=other_event.id, section="Main", row_label="Z", number=1)
        db.session.add(other_seat); db.session.commit()
        self.assertEqual(self.review(self.client, [other_seat.id]).status_code, 302)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))), 0)

    def test_closed_event_and_csrf(self):
        self.login(self.client, "one@example.edu")
        self.assertEqual(self.client.post(f"/events/{self.event_id}/booking/review", data={
            "seat_ids": str(self.ids[0])
        }).status_code, 400)
        event = db.session.get(Event, self.event_id)
        event.starts_at = datetime.now() - timedelta(minutes=2)
        db.session.commit()
        self.assertEqual(self.review(self.client, [self.ids[0]]).status_code, 302)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))), 0)

    def test_database_unique_index_prevents_double_active_booking(self):
        db.session.add(Booking(user_id=self.user_id, seat_id=self.ids[0], status="reserved",
                               price_at_booking=Decimal("15.00")))
        db.session.commit()
        db.session.add(Booking(user_id=self.other_id, seat_id=self.ids[0], status="reserved",
                               price_at_booking=Decimal("15.00")))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_admin_new_event_gets_seats_and_can_delete_until_booked(self):
        admin = User(full_name="Admin", email="admin@example.edu", role="admin")
        admin.set_password("SecurePassword123")
        db.session.add(admin); db.session.commit()
        self.login(self.client, "admin@example.edu")
        token = self.csrf(self.client, "/admin/events/new")
        response = self.client.post("/admin/events/new", data={
            "csrf_token": token, "title": "New Match", "category": "Sports",
            "description": "Fun evening at the campus stadium.", "venue": "Main Stadium",
            "starts_at": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M"),
            "price": "12.50",
        })
        self.assertEqual(response.status_code, 302)
        match = db.session.scalar(select(Event).where(Event.title == "New Match"))
        self.assertEqual(db.session.scalar(select(func.count(Seat.id)).where(Seat.event_id == match.id)), 60)
        response = self.client.post(f"/admin/events/{match.id}/delete", data={
            "csrf_token": self.csrf(self.client, "/admin/events")
        })
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(db.session.get(Event, match.id))

    def test_upgrade_existing_v2_booking_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "previous.sqlite3"
            with sqlite3.connect(path) as conn:
                conn.executescript("""
                CREATE TABLE bookings (
                  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                  seat_id INTEGER NOT NULL, status VARCHAR(20) NOT NULL,
                  created_at DATETIME NOT NULL
                );
                """)
            migrated = create_app({"TESTING": True, "SECRET_KEY": "migration-test",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(path)})
            with migrated.app_context():
                from sqlalchemy import inspect
                names = {col["name"] for col in inspect(db.engine).get_columns("bookings")}
                self.assertIn("price_at_booking", names)
                with db.engine.connect() as connection:
                    indexes = connection.exec_driver_sql(
                        "SELECT name FROM sqlite_master WHERE type='index'"
                    ).fetchall()
                self.assertIn("uq_active_booking_per_seat", [row[0] for row in indexes])


if __name__ == "__main__":
    unittest.main()
