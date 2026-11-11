## v5.4 — Stadium Operations and Reliable QR Entry (2026-11-03)

### New / improved
- **Dedicated admin stadium control center:** event-specific entrance controls, live event seat/attendance metrics, clear gate status, and operational shortcuts.
- **Separate student dashboard:** `/dashboard` shows tickets assigned to the signed-in student (including passes a classmate booked for them), upcoming events, and profile/booking links. Administrators and staff are redirected to their own role-appropriate panels.
- **Named event gates:** `Gate` SQLAlchemy model with event ownership, independently openable entrances, section-to-gate seat assignments, name editing, and one-click open/close for all event entrances. Gate state and event check-in flag are updated together to avoid confusing false rejections.
- **Reliable scanner fallback:** live QR detection where browser support permits, plus phone-camera/gallery QR photograph upload decoded locally with OpenCV. Photo/manual validation is server-side and never auto-admits a ticket; live video still requires HTTPS/localhost and camera permission.
- **Precise gate results:** separate valid ticket, entry not open, select gate, wrong gate, specific gate closed, cancelled, invalid and already checked-in results. A valid ticket at a closed entrance is **not** labelled counterfeit.
- **Complete individual admission tickets:** holder, Student ID, date/time (campus local), venue, assigned entrance, section, row, seat, ticket number, free admission, entry status and scannable signed QR. The QR now contains an opaque signature token rather than an origin-dependent localhost URL.
- **Single-ticket rule:** maintained one active/checked-in ticket per registered student per event in a SQLite partial unique index; group booking continues only for distinct registered students with matching names/IDs. Additional checks stop duplicate own-seat attempts before seat selection.
- **Upgrades and GitHub safety:** idempotent SQLite V5.4 migration with gate backfill and check-in gate audit field, pre-upgrade snapshot safeguard extended to V5.3 installs, V5.4 test cases, updated CI/manuals. No auto-deployment on GitHub push.
- **UI polish:** simplified administration labels, responsive status cards and sections, accessible form hints, existing day/night theme, reduced-motion support, and removed public version/marketing footer text.

### Compatibility / operational notes
- Existing users, events, seat IDs, bookings, ticket signatures, cancellation and check-in records remain intact. All migrated seats initially use Gate 1; gates remain closed until an administrator opens them.
- Open and assign event gates before an event; select the physical gate in the scanner. Camera photograph fallback needs the `opencv-python-headless` dependency.
- Existing SQLite upgrades need a backup and a stable QR signing secret. Full Flask HTTP and mobile-camera acceptance tests are required on your target Windows/HTTPS deployment before real admissions.


# CSTBS Changelog

## v5.3 — Smart University Stadium Ticketing (2026-11-03)

### Added
- **Administrator activation and normal password login:** first-time admins use a hashed, email-bound 20-minute single-use activation/recovery key to set a password. Future logins require only email and password. Admin password resets invalidate old sessions. Additional administrators can be approved and invited through the admin dashboard; public admin registration stays disabled.
- **Group student reservations:** the first reserved seat belongs to the booking student; every additional ticket requires another registered student's matching full name and Student ID. A SQLite partial unique index enforces one active/checked-in ticket per student/event. Reservations and tickets are committed in one transaction.
- **Individual signed QR tickets:** a ticket for each attendee with a server-verified, persistent-key signature that exposes no student details. Mobile-friendly staff gate scanner (browser BarcodeDetector with native-phone-camera/manual fallback); identity verification; explicit POST check-in with CSRF; duplicate/invalid/cancelled/used ticket rejection.
- **Gate operations:** admin-managed booking/gate open/close, staff-only attendance overview and scanning, confidential attendance PDF and CSV exports, ability to assign verified attendees to unassigned legacy reservations.
- **Modern UI:** Campus Light / Stadium Night switcher, smooth entrance and interaction animations, reduced-motion support, responsive QR card and gate views.
- **GitHub-safe workflow:** read-only GitHub Actions CI, private secrets/DB exclusions, health endpoint, SQLite backup CLI and automatic integrity-checked pre-V5.3 upgrade snapshots, idempotent legacy migration and tests.

### Changed
- V5.2 one-time admin *login* keys are now one-time **activation or recovery** keys, with future admin logins using passwords.
- V5.2 multi-seat bookings are preserved. Extra seats for the same student become explicitly **unassigned** QR tickets until an administrator verifies another registered attendee; no booking rows are silently removed.
- Reservation cancellation invalidates QR tickets and retains history; checked-in tickets cannot be cancelled by normal controls.
- Booking confirmations remain free: `¥0.00` RMB/CNY with no payment gateway.

### Verification scope
- Static compilation/template/JavaScript/SQLite integrity checks provided. Full Flask route integration and production concurrency/load tests must pass in a dependency-enabled environment before deployment.

## v5.2 — Simplified Administrator Login (2026-11-01)
- Removed public admin registration; implemented terminal-generated email-bound, expiring, one-use administrator **login** keys (replaced by activation-only flow in V5.3).
- Protected student ID registration and preserved bookings; local development secret generation without Notepad edits.

## v5.1 — University Accounts & Free Reservations
- Mandatory unique Student IDs, separate administrator invitation registration (retired in V5.2), university-specific free admission, RMB display.

## v5.0 — Reports, Security & Documentation
- Admin booking/event PDF and CSV exports, rate limits, security headers, test workflow, user/admin/deployment manuals.

## v4.0 — Administration
- Admin dashboard, event CRUD, seat section/blocking, user roles, bookings oversight and booking email notifications.

## v3.0 — Seat Reservations
- Live seat-map polling, multi-seat checkout, booking cancellation/history, SQLite active-seat conflict protection.

## v2.0 — Accounts and Events
- Flask-Login, Werkzeug password hashes, student/staff/admin roles, admin event CRUD and sample events.

## v1.0 — Foundation and Prototype
- Requirements analysis, PlantUML, SQLite models, responsive public event catalog and student account UI.
