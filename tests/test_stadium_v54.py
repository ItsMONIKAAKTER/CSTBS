"""V5.4 gate assignment, status, photo-QR, dashboards and migration tests."""
import io
import re
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

import qrcode
from sqlalchemy import select, text

from app import create_app, db
from app.entry import admission_verdict
from app.models import Booking, Event, Gate, Seat, Ticket, User
from app.qr_decode import decode_qr_photo
from app.ticketing import ticket_token


class StadiumV54Tests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True, "SECRET_KEY": "test-stadium-v54-secret-key", 
            "TICKET_SIGNING_KEY": "test-stadium-v54-qr-signature-secret-1234",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "MAIL_BACKEND": "console"
        })
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        self.admin = self.user("admin@campus.edu", "Admin User", None, "admin")
        self.staff = self.user("staff@campus.edu", "Gate Officer", None, "staff")
        self.student = self.user("student@campus.edu", "Alice Student", "ALICE001", "student")
        self.other_student = self.user("other@campus.edu", "Bob Student", "BOB00001", "student")
        self.event = Event(title="Campus Match", category="Sports", description="Test stadium match",
                           venue="Campus Stadium", starts_at=datetime.now() + timedelta(days=3), price=Decimal("0"))
        db.session.add(self.event)
        db.session.flush()
        self.north_gate = Gate(event_id=self.event.id, name="Gate 1")
        self.south_gate = Gate(event_id=self.event.id, name="Gate 2")
        db.session.add_all([self.north_gate, self.south_gate])
        db.session.flush()
        self.seat = Seat(event_id=self.event.id, section="North", row_label="A", number=1,
                         gate_id=self.north_gate.id)
        db.session.add(self.seat)
        db.session.flush()
        self.booking = Booking(user_id=self.student.id, seat_id=self.seat.id,
                               status="reserved", price_at_booking=0)
        db.session.add(self.booking)
        db.session.flush()
        self.ticket = Ticket(booking_id=self.booking.id, event_id=self.event.id,
                             attendee_user_id=self.student.id, attendee_name=self.student.full_name,
                             attendee_student_id=self.student.student_id, nonce="v54-signed-nonce-12345", status="active")
        db.session.add(self.ticket)
        db.session.commit()
        self.token = ticket_token(self.ticket)

    def user(self, email, name, sid, role):
        u = User(full_name=name, email=email, student_id=sid, role=role)
        u.set_password("UniversityPass123")
        db.session.add(u)
        db.session.flush()
        return u

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def csrf(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
        self.assertIsNotNone(match, url)
        return match.group(1).decode()

    def login(self, user):
        url = "/admin/login" if user.role == "admin" else "/login"
        return self.client.post(url, data={"csrf_token": self.csrf(url),
                                           "email": user.email, "password": "UniversityPass123"})

    def logout(self):
        self.client.post("/logout", data={"csrf_token": self.csrf("/account")})

    def test_role_specific_dashboards_and_footer(self):
        self.login(self.student)
        self.assertIn(b"Student dashboard", self.client.get("/dashboard").data)
        self.assertEqual(self.client.get("/admin/").status_code, 403)
        self.assertIn(b"CSTBS-", self.client.get(f"/tickets/{self.ticket.id}").data)
        self.assertIn(b"Gate 1", self.client.get(f"/tickets/{self.ticket.id}").data)
        self.assertNotIn(b"Version 5.3", self.client.get("/").data)
        self.logout()
        self.login(self.admin)
        self.assertIn(b"Stadium control center", self.client.get("/admin/").data)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_gate_status_and_wrong_gate_clear_verdict(self):
        self.login(self.staff)
        url = f"/entry/verify/{self.token}"
        self.assertIn(b"ENTRY NOT OPEN", self.client.get(url).data)
        self.assertEqual(admission_verdict(self.ticket, self.north_gate)[0], "waiting")
        self.logout()
        self.login(self.admin)
        self.client.post(f"/admin/events/{self.event.id}/entry/open", data={
            "csrf_token": self.csrf("/admin/")})
        self.assertTrue(self.north_gate.is_open)
        self.logout()
        self.login(self.staff)
        self.assertIn(b"WRONG GATE", self.client.get(url + f"?gate_id={self.south_gate.id}").data)
        response = self.client.post(f"/entry/check-in/{self.token}", data={
            "csrf_token": self.csrf('/entry/scan'), "gate_id": self.south_gate.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, "active")
        self.assertIn(b"ADMIT STUDENT", self.client.get(url+f"?gate_id={self.north_gate.id}").data)
        ok = self.client.post(f"/entry/check-in/{self.token}", data={
            "csrf_token": self.csrf('/entry/scan'), "gate_id": self.north_gate.id})
        self.assertEqual(ok.status_code, 302)
        self.assertEqual(self.ticket.status, "checked_in")
        self.assertEqual(self.ticket.checked_in_gate_id, self.north_gate.id)
        self.assertIn(b"ALREADY CHECKED IN", self.client.get(url+f"?gate_id={self.north_gate.id}").data)

    def test_gate_operations_are_admin_only(self):
        url = f"/admin/events/{self.event.id}/gates"
        self.login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.logout()
        self.login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(f"/admin/gates/{self.north_gate.id}/toggle", data={
            "csrf_token": self.csrf(url)})
        self.assertTrue(self.north_gate.is_open)
        self.assertTrue(self.event.checkin_enabled)
        self.client.post(f"/admin/events/{self.event.id}/sections/North/gate", data={
            "csrf_token": self.csrf(url), "gate_id": self.south_gate.id})
        self.assertEqual(self.seat.gate_id, self.south_gate.id)
        self.client.post(f"/admin/events/{self.event.id}/entry/close", data={
            "csrf_token": self.csrf(url)})
        self.assertFalse(self.event.checkin_enabled)
        self.assertFalse(self.north_gate.is_open)
        self.assertFalse(self.south_gate.is_open)

    def test_photo_scan_decodes_signed_opaque_token(self):
        image = qrcode.make(self.token)
        output = io.BytesIO()
        image.save(output, format="PNG")
        self.assertEqual(decode_qr_photo(output.getvalue()), self.token)
        self.assertIsNone(decode_qr_photo(b"not-an-image"))
        self.login(self.staff)
        response = self.client.post("/entry/scan-photo", data={
            "csrf_token": self.csrf('/entry/scan'), "gate_id": str(self.north_gate.id),
            "qr_photo": (io.BytesIO(output.getvalue()), "ticket.png")},
            content_type="multipart/form-data")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/entry/verify/", response.location)
        self.assertIn(f"gate_id={self.north_gate.id}", response.location)

    def test_student_cannot_get_second_ticket_via_booking_screen(self):
        self.login(self.student)
        result = self.client.get(f"/events/{self.event.id}/seats")
        self.assertEqual(result.status_code, 302)
        self.assertIn('/dashboard', result.location)
        # Persistent unique index also prevents a second live ticket for same attendee.
        index_sql = db.session.execute(text("SELECT sql FROM sqlite_master WHERE name='uq_live_ticket_per_event_student'")) .scalar_one()
        self.assertIn('UNIQUE', index_sql)


if __name__ == "__main__":
    unittest.main()
