"""V5.3 authorization, attendee, signed QR, entry replay and upgrade tests.

Run after requirements install: python -m unittest discover -s tests -v
"""
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
from app.models import Booking, Event, Seat, Ticket, User
from app.ticketing import ticket_token, resolve_ticket_token


class TicketingV53Tests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "v53-flask-test-secret",
            "TICKET_SIGNING_KEY": "v53-stable-test-key-that-is-long-enough-123",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "MAIL_BACKEND": "console"})
        self.ctx = self.app.app_context(); self.ctx.push()
        self.client = self.app.test_client()
        self.student_a = self._user("student.a@campus.edu", "Alice Student", "S1234567", "student")
        self.student_b = self._user("student.b@campus.edu", "Bob Student", "S1234568", "student")
        self.student_c = self._user("student.c@campus.edu", "Clara Student", "S1234569", "student")
        self.staff = self._user("staff@campus.edu", "Gate Staff", None, "staff")
        self.admin = self._user("admin@campus.edu", "Stadium Admin", None, "admin")
        self.event = Event(title="Campus Finals", category="Sports", description="University finals",
            venue="University Stadium", starts_at=datetime.now()+timedelta(days=2), price=Decimal("0"))
        db.session.add(self.event); db.session.flush()
        self.seats = [Seat(event_id=self.event.id, section="North", row_label="A", number=n)
                      for n in range(1,5)]
        db.session.add_all(self.seats); db.session.commit()

    def _user(self, email, name, sid, role):
        user = User(full_name=name, email=email, student_id=sid, role=role)
        user.set_password("UniversityPass123")
        db.session.add(user);db.session.flush()
        return user

    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()

    def csrf(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
        self.assertIsNotNone(match, path)
        return match.group(1).decode()

    def login(self, user):
        url = "/admin/login" if user.role == "admin" else "/login"
        return self.client.post(url, data={"csrf_token":self.csrf(url),
            "email":user.email,"password":"UniversityPass123"})

    def logout(self):
        return self.client.post("/logout", data={"csrf_token":self.csrf("/account")})

    def book(self, seat_ids, ids=None, names=None):
        event_id = self.event.id
        review = self.client.post(f"/events/{event_id}/booking/review", data={
            "csrf_token":self.csrf(f"/events/{event_id}/seats"),
            "seat_ids":','.join(str(i) for i in seat_ids)})
        self.assertEqual(review.status_code,200)
        post = {"csrf_token":self.csrf(f"/events/{event_id}/seats")}
        if ids is not None:
            post["attendee_student_id"] = ids
            post["attendee_name"] = names
        return self.client.post(f"/events/{event_id}/booking/confirm", data=post, follow_redirects=True)

    def test_group_booking_names_and_id_must_match_registered_students(self):
        self.login(self.student_a)
        response = self.book([s.id for s in self.seats[:2]],
            ["S1234567", "S1234568"], ["Alice Student", "Wrong Name"])
        self.assertIn(b"must match a registered student",response.data)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))),0)
        success = self.book([s.id for s in self.seats[:2]],
            ["S1234567", "S1234568"], ["Alice Student", "Bob Student"])
        self.assertIn(b"Booking confirmed", success.data)
        tickets = db.session.scalars(select(Ticket).order_by(Ticket.id)).all()
        self.assertEqual([t.attendee_user_id for t in tickets], [self.student_a.id,self.student_b.id])
        self.assertEqual(len(tickets),2)
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))),2)
        self.assertIn(b"View QR ticket",self.client.get('/bookings').data)
        self.assertEqual(self.client.get(f"/tickets/{tickets[0].id}/qr.png").headers["Content-Type"],"image/png")

    def test_one_student_cannot_receive_two_live_tickets_for_same_event(self):
        self.login(self.student_a)
        self.book([self.seats[0].id])
        self.book([self.seats[1].id])
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))),1)
        first = db.session.scalar(select(Ticket))
        self.assertEqual(first.status,"active")
        self.logout()
        self.login(self.student_b)
        self.book([self.seats[2].id, self.seats[3].id],
            ["S1234568", "S1234567"], ["Bob Student", "Alice Student"])
        self.assertEqual(db.session.scalar(select(func.count(Booking.id))),1)
        # Database constraint also rejects direct duplicate active ticket rows.
        second = Booking(user_id=self.student_b.id,seat_id=self.seats[3].id,price_at_booking=0)
        db.session.add(second);db.session.flush()
        db.session.add(Ticket(booking_id=second.id,event_id=self.event.id,
            attendee_user_id=self.student_a.id,attendee_name="Alice Student",
            attendee_student_id=self.student_a.student_id,nonce="distinctnonce1234",status="active"))
        with self.assertRaises(IntegrityError):db.session.commit()
        db.session.rollback()

    def test_signed_qr_rejects_tampering_duplicate_entry_and_student_scanning(self):
        self.login(self.student_a)
        self.book([self.seats[0].id]);ticket = db.session.scalar(select(Ticket))
        token = ticket_token(ticket)
        self.assertEqual(resolve_ticket_token(token).id,ticket.id)
        self.assertIsNone(resolve_ticket_token(token+"invalid"))
        self.assertEqual(self.client.get('/entry/verify/'+token).status_code,403)
        self.logout()
        self.login(self.staff)
        closed = self.client.get('/entry/verify/'+token)
        self.assertIn(b"GATE CLOSED",closed.data)
        self.logout();self.login(self.admin)
        self.client.post(f"/admin/events/{self.event.id}/toggle/checkin", data={
            "csrf_token":self.csrf('/admin/events')})
        self.logout();self.login(self.staff)
        self.assertIn(b"VALID TICKET",self.client.get('/entry/verify/'+token).data)
        result = self.client.post('/entry/check-in/'+token,data={
            "csrf_token":self.csrf('/entry/scan')}, follow_redirects=True)
        self.assertIn(b"ALREADY USED",result.data)
        self.assertEqual(ticket.status,'checked_in')
        self.assertEqual(ticket.checked_in_by_id,self.staff.id)
        self.client.post('/entry/check-in/'+token,data={
            "csrf_token":self.csrf('/entry/scan')})
        self.assertEqual(ticket.status,'checked_in')
        self.assertEqual(db.session.scalar(select(func.count(Ticket.id)).where(Ticket.status=='checked_in')),1)

    def test_cancelled_ticket_and_checkin_rules(self):
        self.login(self.student_a)
        self.book([self.seats[0].id]);ticket=db.session.scalar(select(Ticket))
        token=ticket_token(ticket)
        self.client.post(f"/bookings/{ticket.booking_id}/cancel",data={"csrf_token":self.csrf('/bookings')})
        self.assertEqual(ticket.status,'cancelled')
        self.logout();self.login(self.staff)
        self.assertIn(b"CANCELLED", self.client.get('/entry/verify/'+token).data)
        self.assertNotEqual(self.client.post('/entry/check-in/'+token,data={
            "csrf_token":self.csrf('/entry/scan')}).status_code,200)
        self.assertNotEqual(ticket.status,'checked_in')

    def test_gate_routes_staff_only_and_reports_admin_only(self):
        self.assertEqual(self.client.get('/entry/scan').status_code,302)
        self.login(self.student_a)
        self.assertEqual(self.client.get('/entry/scan').status_code,403)
        self.assertEqual(self.client.get('/admin/reports/attendance.csv').status_code,403)
        self.logout();self.login(self.staff)
        self.assertEqual(self.client.get('/entry/scan').status_code,200)
        self.assertEqual(self.client.get('/admin/reports/attendance.pdf').status_code,403)
        self.logout();self.login(self.admin)
        for url in ('/admin/reports/attendance.csv','/admin/reports/attendance.pdf'):
            answer=self.client.get(url)
            self.assertEqual(answer.status_code,200)
            self.assertIn('no-store', answer.headers['Cache-Control'])
        self.assertEqual(self.client.get('/health').json['status'],'ok')


if __name__ == '__main__':
    unittest.main()
