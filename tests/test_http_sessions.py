"""Regression tests for isolated test-client sessions and genuine CSRF checks."""

import re
import unittest
from datetime import datetime, timedelta

from sqlalchemy import select

from app import db
from app.models import Event, User
from testing_support import create_isolated_test_app


class HttpSessionIsolationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_isolated_test_app({
            "TESTING": True,
            "SECRET_KEY": "isolated-http-session-test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "MAIL_BACKEND": "console",
        })
        # Deliberately keep the context open to reproduce the old fixture bug.
        self.context = self.app.app_context()
        self.context.push()
        self.primary = self.app.test_client()
        self.other = self.app.test_client()
        for email, role in (("admin@campus.edu", "admin"),
                            ("student@campus.edu", "student")):
            user = User(full_name="Test Student" if role == "student" else "Test Admin",
                        email=email, role=role,
                        student_id="STU000111" if role == "student" else None)
            user.set_password("StrongPassword123")
            db.session.add(user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    @staticmethod
    def csrf(client, path):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
        assert match is not None, path
        return match.group(1).decode("ascii")

    def test_second_browser_remains_anonymous(self):
        token = self.csrf(self.primary, "/login")
        response = self.primary.post("/login", data={
            "csrf_token": token, "email": "student@campus.edu",
            "password": "StrongPassword123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.primary.get("/account").status_code, 200)
        self.assertEqual(self.other.get("/account").status_code, 302)
        self.assertEqual(self.other.get("/login").status_code, 200)

    def test_admin_session_reset_keeps_csrf_protection(self):
        token = self.csrf(self.primary, "/admin/login")
        result = self.primary.post("/admin/login", data={
            "csrf_token": token, "email": "admin@campus.edu",
            "password": "StrongPassword123",
        })
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.primary.get("/admin/").status_code, 200)
        # A fresh logout/menu token must be valid after login's session.clear().
        token = self.csrf(self.primary, "/admin/events/new")
        event_data = {
            "title": "University Open Match",
            "category": "Sports",
            "description": "Stadium test event with enough information",
            "venue": "Campus Stadium",
            "starts_at": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M"),
        }
        self.assertEqual(self.primary.post("/admin/events/new", data=event_data).status_code, 400)
        response = self.primary.post("/admin/events/new", data={"csrf_token": token, **event_data})
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(db.session.scalar(select(Event.id)))
