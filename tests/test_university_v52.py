"""CSTBS v5.2 targeted admin key login and student/booking regression tests."""
import re
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, select
from app import create_app, db
from app.admin_keys import consume_login_key, issue_login_key, provision_first_admin
from app.models import AdminInvitation, Booking, Event, Seat, User, utc_now


class UniversityV52Tests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True,
            "SECRET_KEY": "long-v52-test-only-secret-do-not-use-in-production",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "MAIL_BACKEND": "console"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def csrf(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def student(self, email="student@campus.edu", sid="STU123456"):
        pw = "SecureStudentPass123"
        return self.client.post("/register", data={
            "csrf_token": self.csrf("/register"), "email": email,
            "student_id": sid, "full_name": "Uni Student",
            "password": pw, "confirm_password": pw}, follow_redirects=True)

    def admin_login(self, email, key):
        return self.client.post("/admin/login", data={
            "csrf_token": self.csrf("/admin/login"),
            "email": email, "admin_key": key}, follow_redirects=True)

    def logout(self):
        return self.client.post("/logout", data={"csrf_token": self.csrf("/account")})

    def test_student_registers_with_unique_id_no_admin_role(self):
        response = self.student(sid="stU00123")
        self.assertEqual(response.status_code, 200)
        student = db.session.scalar(select(User))
        self.assertEqual((student.student_id, student.role), ("STU00123", "student"))
        self.logout()
        duplicate = self.student(email="second@campus.edu", sid="STU00123")
        self.assertIn(b"already registered", duplicate.data)
        self.assertEqual(db.session.scalar(select(func.count(User.id))), 1)

    def test_first_admin_setup_without_public_registration(self):
        self.assertEqual(self.client.get("/register/admin").status_code, 302)
        self.assertIn(self.client.post("/register/admin").status_code, (400, 405))  # retired POST route
        user = provision_first_admin("admin@university.edu", "University Admin")
        self.assertEqual(user.role, "admin")
        self.assertIsNotNone(user.password_hash)
        key = issue_login_key(user, bootstrap=True)
        token_row = db.session.scalar(select(AdminInvitation))
        self.assertEqual(token_row.target_user_id, user.id)
        self.assertNotIn(key, token_row.token_hash)
        response = self.admin_login(user.email, key)
        self.assertIn(b"Administrator login successful", response.data)
        self.assertIn(b"dashboard", response.data.lower())
        self.assertIsNotNone(token_row.used_at)
        self.logout()
        self.assertIn(b"Invalid, expired", self.admin_login(user.email, key).data)

    def test_wrong_email_expired_key_reissue_and_token_binding(self):
        admin_a = provision_first_admin("first@university.edu")
        admin_b = User(full_name="Other Admin", email="second@university.edu", role="admin")
        admin_b.set_password("UnusedPassword98765")
        db.session.add(admin_b); db.session.commit()
        key = issue_login_key(admin_a)
        self.assertIn(b"Invalid, expired", self.admin_login(admin_b.email, key).data)
        invite = db.session.scalar(select(AdminInvitation).where(
            AdminInvitation.target_user_id == admin_a.id))
        invite.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()
        self.assertIn(b"Invalid, expired", self.admin_login(admin_a.email, key).data)
        replacement = issue_login_key(admin_a)
        self.assertNotEqual(key, replacement)
        self.assertIn(b"Invalid, expired", self.admin_login(admin_a.email, key).data)
        self.assertIn(b"Administrator login successful", self.admin_login(admin_a.email, replacement).data)

    def test_admin_only_key_issuance_ui_and_roles(self):
        admin = provision_first_admin("admin@campus.edu")
        self.student(email="student@campus.edu", sid="CAMPUS666")
        student = db.session.scalar(select(User).where(User.role == "student"))
        self.assertEqual(self.client.post("/admin/admin-invitations/new", data={
            "csrf_token": self.csrf("/account"), "target_user_id": str(admin.id)
        }).status_code, 403)
        self.logout()
        self.admin_login(admin.email, issue_login_key(admin))
        user_page = self.client.get("/admin/users")
        self.assertIn(b"Generate login key", user_page.data)
        wrong = self.client.post("/admin/admin-invitations/new", data={
            "csrf_token": self.csrf("/admin/users"), "target_user_id": str(student.id)})
        self.assertEqual(wrong.status_code, 400)
        generated = self.client.post("/admin/admin-invitations/new", data={
            "csrf_token": self.csrf("/admin/users"), "target_user_id": str(admin.id)})
        self.assertEqual(generated.status_code, 200)
        self.assertIn("no-store", generated.headers["Cache-Control"])
        self.assertIn(admin.email.encode(), generated.data)
        # Existing admin can still manage student IDs from website.
        r = self.client.post(f"/admin/users/{student.id}/student-id", data={
            "csrf_token": self.csrf("/admin/users"), "student_id": "CAMPUS777"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(student.student_id, "CAMPUS777")

    def test_admin_password_cannot_bypass_access_key(self):
        admin = provision_first_admin("admin@university.edu")
        response = self.client.post("/login", data={
            "csrf_token": self.csrf("/login"), "email": admin.email,
            "password": "any-password"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/admin/login"))
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_free_booking_regression(self):
        self.student()
        event = Event(title="University Match", category="Sports",
            description="A friendly campus university match", venue="Campus",
            starts_at=datetime.now() + timedelta(days=4), price=Decimal("22.00"))
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
