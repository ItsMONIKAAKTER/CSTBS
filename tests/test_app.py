"""Flask integration tests using an isolated in-memory SQLite database.

Run with: python -m unittest discover -s tests -v
"""

import re
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from app import create_app, db
from app.admin_keys import issue_login_key
from app.models import Booking, Event, Seat, User
from app.seed import seed_demo_events


class CSTBSTests(unittest.TestCase):
    """Exercise real Flask routes, forms, role checks, and database writes."""

    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "testing-not-production",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def csrf(self, path):
        """Read the CSRF field from a real HTML form response."""
        page = self.client.get(path)
        self.assertEqual(page.status_code, 200)
        match = re.search(rb'name="csrf_token"[^>]+value="([^"]+)"', page.data)
        self.assertIsNotNone(match)
        return match.group(1).decode("ascii")

    def register(self, email="student@example.edu", password="StrongPass123"):
        return self.client.post("/register", data={
            "csrf_token": self.csrf("/register"),
            "full_name": "Campus Student",
            "student_id": "STU" + __import__("hashlib").sha256(email.lower().encode()).hexdigest()[:8].upper(),
            "email": email,
            "password": password,
            "confirm_password": password,
        }, follow_redirects=True)

    def logout(self):
        return self.client.post("/logout", data={"csrf_token": self.csrf("/account")})

    def make_user(self, email, role):
        user = User(full_name="Test User", email=email, role=role)
        user.set_password("StrongPass123")
        db.session.add(user)
        db.session.commit()
        return user

    def sign_in(self, email, next_path=""):
        user = db.session.scalar(select(User).where(User.email == email))
        if user and user.role == "admin":
            return self.client.post("/admin/login", data={
                "csrf_token": self.csrf("/admin/login"),
                "email": email, "password": "StrongPass123"}, follow_redirects=True)
        path = "/login" + ("?next=" + next_path if next_path else "")
        return self.client.post(path, data={
            "csrf_token": self.csrf(path), "email": email,
            "password": "StrongPass123",
        }, follow_redirects=True)

    def event_data(self, csrf_token, title="Open Day Cup"):
        return {
            "csrf_token": csrf_token,
            "title": title,
            "category": "Sports",
            "description": "A lively interfaculty campus sports event.",
            "venue": "Main Stadium",
            "starts_at": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "price": "12.50",
        }

    def test_public_pages_and_unknown_event(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/events").status_code, 200)
        self.assertEqual(self.client.get("/events/999999").status_code, 404)

    def test_registration_hashes_password_and_sets_student_role(self):
        response = self.register(email="STUDENT@EXAMPLE.EDU")
        self.assertIn(b"Welcome, Campus Student", response.data)
        user = db.session.scalar(select(User).where(User.email == "student@example.edu"))
        self.assertEqual(user.role, "student")
        self.assertNotEqual(user.password_hash, "StrongPass123")
        self.assertTrue(user.check_password("StrongPass123"))
        self.assertFalse(user.check_password("WrongPass123"))

    def test_registration_rejects_duplicate_email(self):
        self.register()
        self.logout()
        response = self.register(email="STUDENT@example.edu")
        self.assertIn(b"already exists", response.data)
        self.assertEqual(db.session.scalar(select(func.count(User.id))), 1)

    def test_public_registration_cannot_assign_admin_role(self):
        payload = {
            "csrf_token": self.csrf("/register"),
            "full_name": "Untrusted User",
            "student_id": "STU2026001",
            "email": "untrusted@example.edu",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
            "role": "admin",  # Attempt a forged browser field.
        }
        self.client.post("/register", data=payload)
        user = db.session.scalar(select(User).where(User.email == "untrusted@example.edu"))
        self.assertEqual(user.role, "student")

    def test_login_logout_and_protected_account(self):
        denied = self.client.get("/account")
        self.assertEqual(denied.status_code, 302)
        self.make_user("student@example.edu", "student")
        response = self.sign_in("student@example.edu")
        self.assertIn(b"Account details", response.data)
        self.assertEqual(self.logout().status_code, 302)
        self.assertEqual(self.client.get("/account").status_code, 302)

    def test_invalid_password_not_authenticated(self):
        self.make_user("student@example.edu", "student")
        response = self.client.post("/login", data={
            "csrf_token": self.csrf("/login"),
            "email": "student@example.edu",
            "password": "nope",
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", response.data)
        self.assertEqual(self.client.get("/account").status_code, 302)

    def test_roles_enforced_and_admin_page_protected(self):
        self.assertEqual(self.client.get("/admin/events").status_code, 302)
        for role in ("student", "staff"):
            email = role + "@example.edu"
            self.make_user(email, role)
            self.sign_in(email)
            self.assertEqual(self.client.get("/admin/events").status_code, 403)
            self.assertEqual(self.client.get("/admin/events/new").status_code, 403)
            self.logout()

    def test_admin_creates_edits_deletes_event(self):
        self.make_user("admin@example.edu", "admin")
        self.sign_in("admin@example.edu")
        created = self.client.post("/admin/events/new", data=self.event_data(
            self.csrf("/admin/events/new")
        ), follow_redirects=True)
        self.assertIn(b"Open Day Cup", created.data)
        event = db.session.scalar(select(Event).where(Event.title == "Open Day Cup"))
        self.assertEqual(event.price, Decimal("0.00"))
        modified = self.client.post(f"/admin/events/{event.id}/edit", data=self.event_data(
            self.csrf(f"/admin/events/{event.id}/edit"), title="Updated Cup"
        ), follow_redirects=True)
        self.assertIn(b"Updated Cup", modified.data)
        self.assertEqual(db.session.get(Event, event.id).title, "Updated Cup")
        deleted = self.client.post(f"/admin/events/{event.id}/delete", data={
            "csrf_token": self.csrf("/admin/events")
        }, follow_redirects=True)
        self.assertIn(b"Event deleted successfully", deleted.data)
        self.assertIsNone(db.session.get(Event, event.id))

    def test_non_admin_cannot_modify_events(self):
        self.make_user("staff@example.edu", "staff")
        self.sign_in("staff@example.edu")
        response = self.client.post("/admin/events/new", data={
            "csrf_token": self.csrf("/account"), **{k: v for k, v in self.event_data("ignore").items() if k != "csrf_token"}
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(db.session.scalar(select(func.count(Event.id))), 0)

    def test_post_requires_csrf_token(self):
        self.assertEqual(self.client.post("/register", data={}).status_code, 400)
        self.assertEqual(self.client.post("/logout", data={}).status_code, 400)

    def test_login_does_not_redirect_to_external_domain(self):
        self.make_user("student@example.edu", "student")
        response = self.sign_in("student@example.edu", next_path="//evil.example")
        self.assertIn(b"Account details", response.data)
        self.assertNotIn(b"evil.example", response.data)

    def test_event_deletion_refused_when_booking_history_exists(self):
        self.make_user("admin@example.edu", "admin")
        event = Event(title="Reserved Event", category="Music", description="Showtime",
                      venue="Main Stadium", starts_at=datetime.now(), price=Decimal("0"))
        db.session.add(event)
        db.session.flush()
        seat = Seat(event_id=event.id, section="A", row_label="1", number=1)
        db.session.add(seat)
        user = self.make_user("buyer@example.edu", "student")
        db.session.add(Booking(user_id=user.id, seat=seat, status="cancelled",
                               price_at_booking=Decimal("0")))
        db.session.commit()
        self.sign_in("admin@example.edu")
        response = self.client.post(f"/admin/events/{event.id}/delete", data={
            "csrf_token": self.csrf("/admin/events")
        }, follow_redirects=True)
        self.assertIn(b"booking history", response.data)
        self.assertIsNotNone(db.session.get(Event, event.id))

    def test_admin_event_ignores_forged_negative_price(self):
        self.make_user("admin@example.edu", "admin")
        self.sign_in("admin@example.edu")
        data = self.event_data(self.csrf("/admin/events/new"))
        data["price"] = "-1.00"
        response = self.client.post("/admin/events/new", data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(db.session.scalar(select(func.count(Event.id))), 1)
        self.assertEqual(db.session.scalar(select(Event.price)), Decimal("0.00"))

    def test_role_assignment_cli(self):
        self.make_user("student@example.edu", "student")
        result = self.app.test_cli_runner().invoke(args=[
            "set-role", "student@example.edu", "admin"
        ])
        self.assertEqual(result.exit_code, 0, result.output)
        user = db.session.scalar(select(User).where(User.email == "student@example.edu"))
        self.assertEqual(user.role, "admin")

    def test_seed_only_if_catalog_empty(self):
        self.assertEqual(seed_demo_events(), 4)
        self.assertEqual(seed_demo_events(), 0)
        self.assertEqual(db.session.scalar(select(func.count(Event.id))), 4)

    def test_legacy_sqlite_user_role_upgrade(self):
        # Simulates a real V1 user table on disk before loading the V2 models.
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.sqlite3"
            with sqlite3.connect(path) as connection:
                connection.executescript("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    full_name VARCHAR(120) NOT NULL,
                    email VARCHAR(254) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL
                );
                INSERT INTO users (full_name, email, password_hash, created_at)
                VALUES ('Old User', 'old@example.edu', 'fake-hash', '2026-01-01 12:00:00');
                """)
            migrated_app = create_app({
                "TESTING": True,
                "SECRET_KEY": "testing-only",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(path),
            })
            with migrated_app.app_context():
                old_user = db.session.scalar(select(User).where(User.email == "old@example.edu"))
                self.assertEqual(old_user.role, "student")
                self.assertEqual(db.session.scalar(select(func.count(User.id))), 1)


if __name__ == "__main__":
    unittest.main()
