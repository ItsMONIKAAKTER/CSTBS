"""Regression checks for V5.2 student IDs and the upgraded admin activation flow."""
import re
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, select
from app import create_app, db
from testing_support import create_isolated_test_app
from app.admin_keys import issue_login_key, provision_first_admin
from app.models import AdminInvitation, Booking, Event, Seat, User, utc_now


class UniversityAccountRegressionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_isolated_test_app({"TESTING": True,
            "SECRET_KEY": "v53-test-secret-do-not-use-in-production",
            "TICKET_SIGNING_KEY": "v53-test-qr-secret-do-not-use-in-production",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "MAIL_BACKEND": "console"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()

    def csrf(self, path):
        page = self.client.get(path)
        self.assertEqual(page.status_code, 200)
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data)
        self.assertIsNotNone(token)
        return token.group(1).decode()

    def register(self, email="student@campus.edu", sid="STU00123"):
        return self.client.post("/register", data={
            "csrf_token": self.csrf("/register"), "email": email,
            "student_id": sid, "full_name": "Uni Student",
            "password": "SecureStudentPass123", "confirm_password": "SecureStudentPass123"
        }, follow_redirects=True)

    def activate(self, email, key, password="NewAdminPassword123"):
        return self.client.post("/admin/activate", data={
            "csrf_token": self.csrf("/admin/activate"), "email": email,
            "admin_key": key, "password": password, "confirm_password": password
        }, follow_redirects=True)

    def test_student_ids_are_unique_and_no_role_escalation(self):
        self.register(sid="stU00123")
        student = db.session.scalar(select(User))
        self.assertEqual((student.student_id, student.role), ("STU00123", "student"))
        self.client.post("/logout", data={"csrf_token": self.csrf("/account")})
        duplicate = self.register(email="second@campus.edu", sid="STU00123")
        self.assertIn(b"already registered", duplicate.data)
        self.assertEqual(db.session.scalar(select(func.count(User.id))), 1)

    def test_admin_key_only_activates_once_then_password_login(self):
        self.assertEqual(self.client.get("/register/admin").status_code, 302)
        admin = provision_first_admin("admin@university.edu", "University Admin")
        self.assertFalse(admin.password_ready)
        key = issue_login_key(admin)
        invitation = db.session.scalar(select(AdminInvitation))
        self.assertNotIn(key, invitation.token_hash)
        reply = self.activate(admin.email, key)
        self.assertIn(b"Account activated", reply.data)
        self.assertTrue(admin.password_ready)
        self.assertIsNotNone(invitation.used_at)
        self.client.post("/logout", data={"csrf_token": self.csrf("/account")})
        self.assertIn(b"invalid, expired or already used", self.activate(admin.email, key).data.lower())
        signed_in = self.client.post("/admin/login", data={
            "csrf_token": self.csrf("/admin/login"), "email": admin.email,
            "password": "NewAdminPassword123"}, follow_redirects=True)
        self.assertIn(b"dashboard", signed_in.data.lower())

    def test_expired_key_does_not_activate(self):
        admin = provision_first_admin("admin@university.edu")
        key = issue_login_key(admin)
        invitation = db.session.scalar(select(AdminInvitation))
        invitation.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()
        reply = self.activate(admin.email, key)
        self.assertIn(b"Key invalid", reply.data)
        self.assertFalse(admin.password_ready)

    def test_admin_can_issue_activation_key_for_newly_promoted_user(self):
        admin = provision_first_admin("admin@campus.edu")
        key = issue_login_key(admin)
        self.activate(admin.email, key)
        self.client.post("/logout", data={"csrf_token": self.csrf("/account")})
        self.register(email="student@campus.edu", sid="CAMPUS666")
        # Can't access admin while still signed into the new student account.
        self.assertEqual(self.client.get("/admin/users").status_code, 403)

    def test_free_single_booking_still_works(self):
        self.register()
        event = Event(title="University Match", category="Sports", description="Friendly",
            venue="Campus", starts_at=datetime.now() + timedelta(days=4), price=Decimal("0"))
        db.session.add(event); db.session.flush()
        seat = Seat(event_id=event.id, section="Main", row_label="A", number=1)
        db.session.add(seat); db.session.commit()
        self.client.post(f"/events/{event.id}/booking/review", data={
            "csrf_token": self.csrf(f"/events/{event.id}/seats"), "seat_ids": str(seat.id)})
        self.client.post(f"/events/{event.id}/booking/confirm", data={
            "csrf_token": self.csrf(f"/events/{event.id}/seats")})
        self.assertEqual(db.session.scalar(select(Booking.price_at_booking)), Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()
