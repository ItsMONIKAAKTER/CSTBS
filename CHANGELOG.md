# Changelog

All notable project changes are documented here.

## [2.0.0] - 2026-11-01

### Added
- Working account registration, sign-in, sign-out, and authenticated account page.
- Flask-Login session handling and `@login_required` protection.
- Werkzeug password hashing and verification.
- Role support for `student`, `staff`, and `admin` (public registration always creates `student`).
- Admin-only event management pages with create, edit, and delete operations.
- Server-side admin authorization and CSRF-protected event forms.
- Explicit `flask seed-events` command for a sample event catalog.
- Local `flask set-role EMAIL ROLE` command to bootstrap administrators.
- SQLite V1-to-V2 role-column upgrade without dropping legacy data.
- Account/admin Jinja2 templates, responsive CSS, and delete confirmation.
- Integration test suite under `tests/`.

### Changed
- Replaced UI-only login and registration from V1 with real database-backed accounts.
- Updated shared navigation to reflect signed-in users and admin options.
- Preserved public event listing and detail pages.
- Changed sample seeding from automatic-on-every-startup to an explicit CLI command.
- Updated requirements analysis, UML, database documentation, README, and dependencies.

### Security
- Emails normalized before storage and lookup; duplicate emails rejected.
- Password hashes only; no plaintext persistence.
- All public registrations are `student`; elevated roles require local CLI access.
- Login redirects limited to internal paths; logout and deletion require POST + CSRF.
- Event deletion refuses to remove an event that has associated seats.

### Not included
- Ticket bookings, seat allocation, payments, password recovery, email verification, rate limiting, production deployment, and generalized database migrations.

## [1.0.0] - Initial prototype

- Responsive homepage and public event catalog.
- Event details and UI-only login/registration pages.
- Initial `User`, `Event`, `Seat`, and `Booking` schema; sample events.
- Requirements, UML, and database design documents.
