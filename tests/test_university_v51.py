"""CSTBS V5.1: student identity, invite safety, role access and free bookings."""
import re
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app import create_app, db
from app.admin_keys import issue_key
from app.models import AdminInvitation, Booking, Event, Seat, User, utc_now


class UniversityV51Tests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "unit-test-v51-very-private",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "MAIL_BACKEND": "console"})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def csrf(self, path):
        r = self.client.get(path)
        self.assertEqual(r.status_code, 200)
        found = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
        self.assertIsNotNone(found)
        return found.group(1).decode()

    def student(self, email="a@campus.edu", sid="2026001234", **extra):
        password = "StrongPassword123"
        return self.client.post("/register", data={
            "csrf_token": self.csrf("/register"), "email": email,
            "student_id": sid, "full_name": "Uni Student",
            "password": password, "confirm_password": password, **extra}, follow_redirects=True)

    def admin(self, key, email="admin@campus.edu"):
        password = "StrongPassword123"
        return self.client.post("/register/admin", data={
            "csrf_token": self.csrf("/register/admin"), "full_name": "Campus Admin",
            "email": email, "admin_key": key, "password": password,
            "confirm_password": password}, follow_redirects=True)

    def logout(self):
        return self.client.post("/logout", data={"csrf_token": self.csrf("/account")})

    def test_student_id_required_validated_unique_and_case_normalized(self):
        invalid = self.student(sid="x")
        self.assertIn(b"6", invalid.data)
        self.assertEqual(db.session.scalar(select(func.count(User.id))), 0)
        result = self.student(sid="stU00123")
        self.assertIn(b"Uni Student", result.data)
        user = db.session.scalar(select(User))
        self.assertEqual(user.student_id, "STU00123")
        self.assertEqual(user.role, "student")
        self.logout()
        duplicate = self.student(email="b@campus.edu", sid="STU00123")
        self.assertIn(b"already registered", duplicate.data)
        self.assertEqual(db.session.scalar(select(func.count(User.id))), 1)

    def test_student_cannot_submit_admin_role(self):
        result = self.student(sid="STU00999", role="admin")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(db.session.scalar(select(User.role)), "student")
        self.assertEqual(self.client.get("/admin/").status_code, 403)

    def test_admin_key_required_single_use_and_expiring(self):
        r = self.admin("CSTBS-not-real-key-not-real")
        self.assertIn(b"Invalid, expired", r.data)
        key = issue_key(bootstrap=True, minutes=60)
        self.assertNotIn(key, str(db.session.scalar(select(AdminInvitation.token_hash))))
        registered = self.admin(key)
        self.assertIn(b"Administrator account created", registered.data)
        self.assertEqual(db.session.scalar(select(User.role)), "admin")
        self.assertIsNotNone(db.session.scalar(select(AdminInvitation.used_at)))
        self.logout()
        replay = self.admin(key, email="other@campus.edu")
        self.assertIn(b"Invalid, expired", replay.data)
        self.assertEqual(db.session.scalar(select(func.count(User.id))), 1)

    def test_expired_invitation_rejected(self):
        key = issue_key(bootstrap=True, minutes=60)
        invitation = db.session.scalar(select(AdminInvitation))
        invitation.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()
        r = self.admin(key)
        self.assertIn(b"Invalid, expired", r.data)
        self.assertEqual(db.session.scalar(select(func.count(User.id))), 0)

    def test_admin_ui_create_invitation_and_student_id_edit(self):
        key = issue_key(bootstrap=True, minutes=60)
        self.admin(key)
        invitation_response = self.client.post("/admin/admin-invitations/new",
            data={"csrf_token": self.csrf("/admin/users")})
        self.assertEqual(invitation_response.status_code, 200)
        self.assertIn("no-store", invitation_response.headers["Cache-Control"])
        generated = re.search(rb'CSTBS-[A-Za-z0-9_\-]{20,}', invitation_response.data)
        self.assertIsNotNone(generated)
        generated_key = generated.group().decode()
        self.logout()
        self.admin(generated_key, email="secondadmin@campus.edu")
        self.assertEqual(db.session.scalar(select(func.count(User.id)).where(User.role == "admin")), 2)
        self.logout()
        self.student(email="student@campus.edu", sid="STU123456")
        student = db.session.scalar(select(User).where(User.role == "student"))
        self.logout()
        self.client.post("/login", data={"csrf_token": self.csrf("/login"),
            "email": "admin@campus.edu", "password": "StrongPassword123"})
        r = self.client.post(f"/admin/users/{student.id}/student-id", data={
            "csrf_token": self.csrf("/admin/users"), "student_id": "STU654321"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(student.student_id, "STU654321")

    def test_non_admin_cannot_issue_keys(self):
        self.student()
        self.assertEqual(self.client.post("/admin/admin-invitations/new", data={
            "csrf_token": self.csrf("/account")}).status_code, 403)

    def test_free_booking_regardless_of_legacy_price(self):
        self.student()
        event = Event(title="University Match", category="Sports", description="A student match",
            venue="Campus", starts_at=datetime.now() + timedelta(days=4), price=Decimal("25.00"))
        db.session.add(event)
        db.session.flush()
        seat = Seat(event_id=event.id, section="Main", row_label="A", number=1)
        db.session.add(seat)
        db.session.commit()
        r = self.client.post(f"/events/{event.id}/booking/review", data={
            "csrf_token": self.csrf(f"/events/{event.id}/seats"), "seat_ids": str(seat.id)})
        self.assertEqual(r.status_code, 200)
        self.assertIn("¥0.00".encode(), r.data)
        self.client.post(f"/events/{event.id}/booking/confirm", data={
            "csrf_token": self.csrf(f"/events/{event.id}/seats")})
        self.assertEqual(db.session.scalar(select(Booking.price_at_booking)), Decimal("0.00"))

    def test_legacy_student_can_complete_missing_id(self):
        user = User(full_name="Legacy Student", email="legacy@campus.edu", role="student")
        user.set_password("StrongPassword123")
        db.session.add(user)
        db.session.commit()
        self.client.post("/login", data={"csrf_token": self.csrf("/login"),
            "email": user.email, "password": "StrongPassword123"})
        self.assertIn(b"Not yet provided", self.client.get("/account").data)
        r = self.client.post("/account/student-id", data={
            "csrf_token": self.csrf("/account"), "student_id": "UNI2026001"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(user.student_id, "UNI2026001")


if __name__ == "__main__":
    unittest.main()
