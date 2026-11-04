# CSTBS CHANGELOG

## v5.2 — Simplified Administrator Login (2026-11-01)

### Changed
- Removed public administrator registration. The old GET `/register/admin` redirects to `/admin/login`; POST registration is not available.
- A first-run local terminal prompt provisions the first administrator and prints their one-time access key (no editing source, `.env`, Notepad or database).
- Existing admins sign in using their **email + 20-minute, one-time access key**; successful login redirects to `/admin/`. Admin password login is disabled.
- Existing admin roles and bookings preserved; V5.1 unbound registration tokens invalidated during schema update.
- Admin Dashboard > Users generates a targeted key only for existing admin accounts. A trusted admin may first promote a user.
- Added interactive CLI `flask admin-setup` and `flask admin-key EMAIL` for setup/recovery.
- Local development auto-generates a stable private Flask secret in `instance/` if not configured. Production requires explicit secure settings.

### Added security and quality
- Email-bound tokens, hashed token fingerprints, single use and time-based expiry; new token revokes prior unused tokens for that admin.
- New admin login form and tests for replay, expiration, wrong email, invalid roles, CSRF, admin access and booking regression.
- Updated Windows setup, manuals, diagrams and GitHub release notes.

## v5.1 — University Accounts & Free Reservations
- Unique mandatory Student IDs, one-time administrator registration invitations (replaced by V5.2), free campus admission, RMB display.

## v5.0 — Final Reporting, Security & Documentation
- PDF and CSV admin exports, rate limiting, security headers, complete manuals and demo improvements.

## v4.0 — Administration
- Dashboard, seat/section blocking, user role and all-booking management, booking email notifications.

## v3.0 — Seat Reservations
- Interactive seats, availability polling, booking checkout/history/cancellation, conflict prevention.

## v2.0 — Accounts & Events
- Flask-Login authentication, Werkzeug password hashes, student/staff/admin roles, admin event CRUD.

## v1.0 — Initial Prototype
- Requirements, UML/database design, responsive pages, event catalog and initial models.
