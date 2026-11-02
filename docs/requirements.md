# CSTBS Version 2 — Requirements Analysis

## Purpose

Extend V1's read-only campus event catalog into a functioning **Accounts and Events** milestone. Public event browsing remains available; students can register and sign in; administrators manage event listings.

## Roles and permissions

| Actor | Browse events | Register / log in | View account | Create/edit/delete events |
| --- | --- | --- | --- | --- |
| Visitor | Yes | Yes | No | No |
| Student | Yes | Already registered | Yes | No |
| Staff | Yes | Already registered | Yes | No |
| Admin | Yes | Already registered | Yes | Yes |

All browser registrations are assigned `student`; trusted local CLI access is required to change roles.

## Functional requirements and acceptance criteria

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Registration | A valid registration creates a `users` row and signs in the new student. |
| FR-02 | Password safety | Only a Werkzeug hash is stored; incorrect passwords fail. |
| FR-03 | Login/logout | Valid credentials create a Flask-Login session, POST `/logout` ends it. |
| FR-04 | Roles | `student`, `staff`, `admin` are stored; public role selection is impossible. |
| FR-05 | Protected routes | `/account` and all admin routes require login. |
| FR-06 | Admin authorization | Students/staff receive 403 on admin routes. |
| FR-07 | Public catalog | `/events` and `/events/<id>` work without login. |
| FR-08 | Create event | Admin can provide title, category, description, venue, date/time and non-negative price. |
| FR-09 | Edit event | Admin can update a saved event from a pre-filled form. |
| FR-10 | Delete event | Admin deletes via POST+CSRF; events with attached seats cannot be deleted. |
| FR-11 | Seed data | `flask seed-events` inserts four examples if catalog is empty. |
| FR-12 | V1 compatibility | Existing SQLite user table gains a default `student` role if needed. |

## Non-functional requirements

- Python 3.10+, Flask, Flask-SQLAlchemy, SQLite, Flask-WTF, Flask-Login, Werkzeug, dotenv, Jinja2.
- Secrets are read from local environment and excluded from Git.
- CSRF checks apply to all modifying POST requests.
- Navigation, event cards, forms, and admin pages adapt to mobile screens.
- Clean architecture: models/forms/routes/templates/seed/migrations separated.
- Automated Flask-client integration tests provided for core flows.

## Representative user journeys

1. Visitor browses events, registers with name/email/password, and lands in an account page as `student`.
2. Returning user signs in, views account, and logs out via CSRF-protected POST.
3. Maintainer promotes an existing account to admin via local CLI; admin signs in and adds/edits/deletes events.
4. Student/staff attempt an admin route and receive HTTP 403.
5. Maintainer executes the sample-data seeding command only when needed.

## Out of scope

Seat inventory and bookings, payments, refunds, password reset, email verification, self-service role promotion, staff-specific workflows, real-time availability, production-rate limiting, generalized database migrations, production deployment. V1's Seat and Booking classes remain passive schema placeholders.

## Manual acceptance checklist

- [ ] Install dependencies and create a strong local `.env` secret.
- [ ] Seed demo events and confirm public event pages work while signed out.
- [ ] Register a student, inspect hashed DB password, sign out and sign back in.
- [ ] Confirm duplicate email and wrong password are rejected.
- [ ] Confirm anonymous users redirect to login for protected pages.
- [ ] Confirm student/staff get 403 for admin pages.
- [ ] Promote a test user via CLI, create/edit/delete an event in the UI.
- [ ] Confirm logout and deletion without CSRF return HTTP 400.
- [ ] Verify small-screen responsiveness and browser keyboard navigation.
- [ ] Execute `python -m unittest discover -s tests -v`.
