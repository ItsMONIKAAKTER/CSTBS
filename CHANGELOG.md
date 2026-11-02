# Changelog

All notable CSTBS changes are recorded in this file.

## [3.0.0] — 2026-11-01 — Seat Reservations

### Added
- Interactive mobile-friendly seat selection grid (60 default seats per event) with native button navigation, seat legend, selection summary, and six-seat limit.
- Polling JSON seat availability (`GET /api/events/<id>/seats`) every five seconds with `Cache-Control: no-store` and fresh server checks.
- Multi-seat reservation journey: select, review, confirm, atomically persist one booking per seat.
- Logged-in booking history and POST/CSRF-protected cancellation of owned bookings; cancelled records remain available for historical display.
- Completed `Seat` and `Booking` model relationships, per-booking seat-price snapshot and partial unique SQLite index preventing multiple active reservations for one seat.
- Default seat inventory on seeded and admin-created events; local startup backfills empty-seat V2 events.
- Reservation integration tests and refreshed requirements, UML and database documentation.

### Changed
- Event detail page now links to live seat reservation for upcoming events.
- Account and navigation now link to **My bookings**.
- Admin event deletion removes unused seats when no booking history exists, and refuses deletion when any reserved/cancelled history exists.
- SQLite compatibility upgrade adds the `price_at_booking` column to prior booking tables and the unique active-seat index; existing data are preserved.

### Security and behavior
- Sessions/authentication, student/staff/admin roles and admin-only event CRUD retained from V2.
- Booking confirmation rechecks event/seat ownership, max-seat count, occupancy, and time window server-side.
- SQLite unique partial index is the final double-booking guard; transactional failures roll back the entire seat selection.
- Cancellations are owner-only; all state-changing routes require CSRF protection.
- No payment is collected. A "reservation" means seat allocation, not a paid ticket.

### Known limitations
- Five-second polling is near-real-time rather than WebSocket push or a temporary seat hold.
- SQLite and application-level migrations are for local/demo workloads only.
- No checkout, ticket delivery, QR scanning, refunds or production security hardening.

## [2.0.0] — Accounts and Events

- Secure registration/login/logout using Flask-Login and Werkzeug hashing.
- Student/staff/admin roles, `@login_required`, admin-only event create/edit/delete.
- Public events, sample data seeding, V1-to-V2 role compatibility, refreshed documentation.

## [1.0.0] — Web Prototype

- Flask application factory, V1 models, public catalog pages, UI-only account forms,
  responsive Jinja2 templates, CSS, requirements and UML design documents.
