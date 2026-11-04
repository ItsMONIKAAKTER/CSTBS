"""V5 integration tests for role-gated downloads, filters and security."""

import csv
import io
import re
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app import create_app, db
from app.admin_keys import issue_login_key
from app.models import Booking, Event, Seat, User


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-only-key-for-v5",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "MAIL_BACKEND": "console",
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        for email, role in (("admin@example.edu", "admin"),
                            ("student@example.edu", "student")):
            user = User(full_name="=HYPERLINK(example)", email=email, role=role)
            user.set_password("StrongPass123")
            db.session.add(user)
        event = Event(title="=Injected Event", category="Music", description="Demo event",
            venue="Main Stadium", starts_at=datetime.now() + timedelta(days=3),
            price=Decimal("25.00"))
        db.session.add(event)
        db.session.flush()
        seat = Seat(event_id=event.id, section="Main", row_label="A", number=1)
        db.session.add(seat)
        db.session.flush()
        student = db.session.scalar(select(User).where(User.role == "student"))
        db.session.add(Booking(user_id=student.id, seat_id=seat.id,
            status="reserved", price_at_booking=Decimal("25.00")))
        db.session.commit()
        self.event_id = event.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def sign_in(self, email):
        user = db.session.scalar(select(User).where(User.email == email))
        is_admin = user.role == "admin"
        route = "/admin/login" if is_admin else "/login"
        login = self.client.get(route)
        match = re.search(rb'name="csrf_token"[^>]+value="([^"]+)"', login.data)
        self.assertIsNotNone(match)
        payload = {"csrf_token": match.group(1).decode(), "email": email}
        if is_admin:
            payload["admin_key"] = issue_login_key(user)
        else:
            payload["password"] = "StrongPass123"
        result = self.client.post(route, data=payload)
        self.assertEqual(result.status_code, 302)

    def test_reports_forbid_guests_and_non_admins(self):
        for path in ("/admin/reports/", "/admin/reports/events.csv",
                     "/admin/reports/bookings.pdf"):
            self.assertEqual(self.client.get(path).status_code, 302)
        self.sign_in("student@example.edu")
        for path in ("/admin/reports/", "/admin/reports/events.csv",
                     "/admin/reports/bookings.pdf"):
            self.assertEqual(self.client.get(path).status_code, 403)

    def test_pdf_csv_types_and_private_headers(self):
        self.sign_in("admin@example.edu")
        self.assertIn(b"Booking report", self.client.get("/admin/reports/").data)
        for kind in ("bookings", "events"):
            pdf = self.client.get(f"/admin/reports/{kind}.pdf")
            self.assertEqual(pdf.status_code, 200)
            self.assertEqual(pdf.data[:5], b"%PDF-")
            self.assertIn("application/pdf", pdf.content_type)
            self.assertIn("attachment", pdf.headers["Content-Disposition"])
            self.assertIn("no-store", pdf.headers["Cache-Control"])
            csv_file = self.client.get(f"/admin/reports/{kind}.csv")
            self.assertEqual(csv_file.status_code, 200)
            self.assertIn("text/csv", csv_file.content_type)
            self.assertTrue(csv_file.data.startswith(b"\xef\xbb\xbf"))
            rows = list(csv.reader(io.StringIO(csv_file.data.decode("utf-8-sig"))))
            self.assertEqual(len(rows), 2)

    def test_booking_filters_and_spreadsheet_injection_escape(self):
        self.sign_in("admin@example.edu")
        csv_response = self.client.get(f"/admin/reports/bookings.csv?event_id={self.event_id}&status=reserved")
        lines = list(csv.reader(io.StringIO(csv_response.data.decode("utf-8-sig"))))
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1][2].startswith("'="))
        self.assertTrue(lines[1][4].startswith("'="))
        empty = self.client.get("/admin/reports/bookings.csv?status=cancelled")
        self.assertEqual(len(list(csv.reader(io.StringIO(empty.data.decode("utf-8-sig"))))), 1)
        for invalid in ("?status=broken", "?event_id=-1", "?event_id=x", "?event_id=0000000000001"):
            self.assertEqual(self.client.get("/admin/reports/bookings.csv" + invalid).status_code, 400)

    def test_security_headers_and_protected_writes(self):
        page = self.client.get("/")
        self.assertIn("frame-ancestors 'none'", page.headers["Content-Security-Policy"])
        self.assertEqual(page.headers["X-Frame-Options"], "DENY")
        self.assertEqual(self.client.post("/register", data={}).status_code, 400)
        self.assertEqual(self.client.get("/admin/reports/bookings.xml").status_code, 302)


if __name__ == "__main__":
    unittest.main()
