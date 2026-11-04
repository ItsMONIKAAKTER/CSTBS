"""Version 4 integration cases; run with unittest after pip install."""

import re
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.admin_keys import issue_login_key
from app.models import Booking, Event, Seat, User


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-key-v4",
                               "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                               "MAIL_BACKEND": "console"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        for email, role in [("admin@example.edu", "admin"), ("student@example.edu", "student"),
                            ("staff@example.edu", "staff")]:
            user = User(full_name=role.capitalize(), email=email, role=role)
            user.set_password("StrongPass123")
            db.session.add(user)
        self.event = Event(title="Open Air Derby", category="Sport",
                           description="University football event", venue="Stadium",
                           starts_at=datetime.now() + timedelta(days=5),
                           price=Decimal("10.00"))
        db.session.add(self.event)
        db.session.flush()
        db.session.add(Seat(event_id=self.event.id, section="Main", row_label="A", number=1))
        db.session.commit()
        self.event_id = self.event.id
        self.seat_id = db.session.scalar(select(Seat.id).where(Seat.event_id == self.event_id))

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def csrf(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        value = re.search(rb'name="csrf_token"[^>]+value="([^"]+)"', response.data)
        self.assertIsNotNone(value)
        return value.group(1).decode()

    def sign_in(self, email):
        user = db.session.scalar(select(User).where(User.email == email))
        if user.role == "admin":
            key = issue_login_key(user)
            return self.client.post("/admin/login", data={
                "csrf_token": self.csrf("/admin/login"), "email": email,
                "admin_key": key})
        return self.client.post("/login", data={"csrf_token": self.csrf("/login"),
            "email": email, "password": "StrongPass123"})

    def sign_out(self):
        return self.client.post("/logout", data={"csrf_token": self.csrf("/account")})

    def admin_post(self, path, data=None):
        return self.client.post(path, data={"csrf_token": self.csrf("/admin/"), **(data or {})})

    def test_admin_paths_require_role_and_csrf(self):
        for path in ("/admin/", "/admin/users", "/admin/bookings",
                     f"/admin/events/{self.event_id}/seats"):
            self.assertEqual(self.client.get(path).status_code, 302)
        self.sign_in("student@example.edu")
        for path in ("/admin/", "/admin/users", "/admin/bookings",
                     f"/admin/events/{self.event_id}/seats"):
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.post(f"/admin/seats/{self.seat_id}/toggle-block").status_code, 400)
        self.sign_out()
        self.sign_in("admin@example.edu")
        self.assertIn(b"Stadium", self.client.get("/admin/").data)
        self.assertIn(b"Seat", self.client.get(f"/admin/events/{self.event_id}/seats").data)

    def test_roles_and_self_demote_blocked(self):
        self.sign_in("admin@example.edu")
        student = db.session.scalar(select(User).where(User.role == "student"))
        admin = db.session.scalar(select(User).where(User.role == "admin"))
        r = self.admin_post(f"/admin/users/{student.id}/role", {"role": "staff"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(student.role, "staff")
        self.admin_post(f"/admin/users/{admin.id}/role", {"role": "student"})
        self.assertEqual(admin.role, "admin")
        self.admin_post(f"/admin/users/{student.id}/role", {"role": "superadmin"})
        self.assertEqual(student.role, "staff")

    def test_create_rename_delete_unbooked_section(self):
        self.sign_in("admin@example.edu")
        base = f"/admin/events/{self.event_id}/sections"
        self.admin_post(base + "/create", {"name": "West Stand", "rows": "2", "seats_per_row": "3"})
        seats = db.session.scalars(select(Seat).where(Seat.event_id == self.event_id,
                                                     Seat.section == "West Stand")).all()
        self.assertEqual(len(seats), 6)
        self.admin_post(base + "/rename", {"old_name": "West Stand", "new_name": "East Stand"})
        self.assertEqual(db.session.scalar(select(func.count(Seat.id)).where(Seat.section == "East Stand")), 6)
        self.admin_post(base + "/East Stand/delete")
        self.assertEqual(db.session.scalar(select(func.count(Seat.id)).where(Seat.section == "East Stand")), 0)

    def test_block_unblock_and_occupied_seat_rejection(self):
        self.sign_in("admin@example.edu")
        route = f"/admin/seats/{self.seat_id}/toggle-block"
        self.admin_post(route)
        seat = db.session.get(Seat, self.seat_id)
        self.assertTrue(seat.is_blocked)
        self.assertIn(self.seat_id, self.client.get(f"/api/events/{self.event_id}/seats").json["blocked_seat_ids"])
        self.assertEqual(self.client.get(f"/api/events/{self.event_id}/seats").json["available"], 0)
        self.admin_post(route)
        self.assertFalse(seat.is_blocked)
        student = db.session.scalar(select(User).where(User.role == "student"))
        db.session.add(Booking(user_id=student.id, seat_id=self.seat_id,
                               status="reserved", price_at_booking=Decimal("10.00")))
        db.session.commit()
        self.admin_post(route)
        self.assertFalse(seat.is_blocked)
        self.admin_post(f"/admin/events/{self.event_id}/sections/Main/delete")
        self.assertIsNotNone(db.session.get(Seat, self.seat_id))

    def test_database_rejects_booking_on_blocked_seat(self):
        seat = db.session.get(Seat, self.seat_id)
        seat.is_blocked = True
        db.session.commit()
        student = db.session.scalar(select(User).where(User.role == "student"))
        db.session.add(Booking(user_id=student.id, seat_id=self.seat_id,
                               status="reserved", price_at_booking=Decimal("10.00")))
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        seat.is_blocked = False
        db.session.commit()

    def test_admin_cancellation_and_email_after_commit(self):
        student = db.session.scalar(select(User).where(User.role == "student"))
        booking = Booking(user_id=student.id, seat_id=self.seat_id,
                          status="reserved", price_at_booking=Decimal("10.00"))
        db.session.add(booking)
        db.session.commit()
        self.sign_in("admin@example.edu")
        with patch("app.admin.notify_booking_cancelled") as notifier:
            result = self.admin_post(f"/admin/bookings/{booking.id}/cancel")
            self.assertEqual(result.status_code, 302)
            self.assertEqual(booking.status, "cancelled")
            notifier.assert_called_once()
            # Repeated cancel is safe and does not generate another email.
            self.admin_post(f"/admin/bookings/{booking.id}/cancel")
            notifier.assert_called_once()

    def test_upgrade_v3_database_adds_block_flag(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "v3.sqlite"
            with sqlite3.connect(path) as conn:
                conn.executescript("CREATE TABLE seats (id INTEGER PRIMARY KEY, event_id INTEGER, "
                                   "section VARCHAR(30), row_label VARCHAR(10), number INTEGER);"
                                   "INSERT INTO seats VALUES (1, 1, 'Main', 'A', 1);")
            upgraded = create_app({"TESTING": True, "SECRET_KEY": "test-migration-v4",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{path}"})
            with upgraded.app_context():
                from sqlalchemy import inspect
                fields = {col["name"] for col in inspect(db.engine).get_columns("seats")}
                self.assertIn("is_blocked", fields)
                self.assertEqual(db.session.get(Seat, 1).is_blocked, False)


if __name__ == "__main__":
    unittest.main()
