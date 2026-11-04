# Requirements Update — CSTBS v5.2

| ID | Requirement | Acceptance |
|---|---|---|
| FR-52-01 | No public admin registration | GET `/register/admin` redirects to `/admin/login`; POST cannot register users. |
| FR-52-02 | Initial admin bootstrap requires trusted terminal | Local `python run.py` prompts for email/name when no admin exists; no code, `.env`, Notepad or SQL edits. |
| FR-52-03 | Admin login uses email + one-time key | Login key is attached to one existing admin user, expires within 20 minutes and is single-use. |
| FR-52-04 | Direct dashboard after admin login | Valid POST `/admin/login` redirects to `/admin/` and creates Flask-Login session. |
| FR-52-05 | Lost key recovery | `flask admin-key EMAIL` immediately prints a new key; issuing it revokes earlier unused keys. |
| FR-52-06 | Admin invitation UI changed to targeted key UI | Admin Users page can generate 20-minute keys for existing admins; promotion remains protected. |
| FR-52-07 | Students remain unchanged | Student registration requires a unique 6-20 char student ID; login uses email/password; no escalation. |
| FR-52-08 | Existing bookings and roles survive | V5.2 schema update adds target recipient field and invalidates legacy registration keys only. |
| FR-52-09 | Local setup requires no secret editing | Private stable development SECRET_KEY generated automatically in instance when missing; production requires explicit configuration. |
| SEC-52-01 | Key material stored only hashed | HMAC-SHA256 token fingerprint; no raw key persists in DB, source or config. |
| SEC-52-02 | Key tied to email and admin account | Wrong email, role, expired, replayed or replaced token is rejected. |
| SEC-52-03 | Admin password cannot bypass key | Admin users are redirected away from common password login. |

## Preserved V5.1 requirements

Students still require unique student IDs, bookings stay free (CNY ¥0.00), admin controls remain role-protected, seat inventory remains conflict-safe, and reports are PDF and CSV.

---

# Requirements Update — CSTBS v5.1

- **FR-51-01:** Visitor can create a student account only with full name, email, password and a unique 6–20-character Student ID. Student role is server-assigned.
- **FR-51-02:** Initial administrator can register through the website using a secret key generated in the local terminal, valid for 60 minutes and one use.
- **FR-51-03:** Existing administrator can generate further single-use invitations on the website, without changing Python files or SQLite rows manually.
- **FR-51-04:** Registered users (student, staff, admin) log in using one common login page.
- **FR-51-05:** Admin manages Student IDs, user roles, event CRUD, seats, sections, bookings and reports from the web UI.
- **FR-51-06:** All admission is free (RMB/CNY ¥0.00); ticket payment, charges and refunds are out of scope.
- **FR-51-07:** Existing V5 users, events and booking history survive a controlled migration.
- **SEC-51-01:** Stored admin invitation tokens are keyed hashes; keys expire and are atomically consumed, and admin invitation generation requires admin role + CSRF.
- **SEC-51-02:** Student ID is checked server-side and unique in SQLite; student and admin registration endpoints are rate limited.
- **ACC-51-01:** A reused or expired admin key never creates an account; forged student role and client price are ignored.
- **ACC-51-02:** A seat confirmed for an event has amount due ¥0.00, including legacy events once updated.
- **ACC-51-03:** Admin UI provides key generation and Student ID editing without an IDE.

---

## V5 historical requirements

# CSTBS V5 — Requirements and Verification

## Goal and scope

Integrate V1–V4 accounts, events, seating, reservations, administration and email notifications, then deliver protected PDF/CSV reports, improved security, demo data and full manuals. **No payment processing or issued tickets.**

## Role access matrix

| Capability | Anonymous | Student | Staff | Admin |
| --- | :---: | :---: | :---: | :---: |
| Browse events and seat availability | Yes | Yes | Yes | Yes |
| Create an account/login | Yes | Yes | Yes | Yes |
| Reserve/cancel own bookings | No | Yes | Yes | Yes |
| Event CRUD/seat sections/blocks | No | No | No | Yes |
| Manage roles and all bookings | No | No | No | Yes |
| Export PDF/CSV reports | No | No | No | Yes |

Public registration assigns only student role. Staff is not an administrative role.

## Version 5 functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR5-01 | Admin report hub | `/admin/reports/` is linked from admin tabs and dashboard. |
| FR5-02 | Booking PDF | `GET /admin/reports/bookings.pdf` returns a PDF attachment with IDs, times, event, owner, seat, status and saved price; repeated table header and page footer. |
| FR5-03 | Event PDF | `GET /admin/reports/events.pdf` returns inventory and occupancy report, including available seats. |
| FR5-04 | Booking CSV | Same booking fields, UTF-8 BOM, CSV quoting and formula-escape on dangerous user fields. |
| FR5-05 | Event CSV | Same event fields and calculated capacity counts; no personal records beyond admin-only access. |
| FR5-06 | Filters | Booking status is all/reserved/cancelled; event ID numeric or omitted; invalid values return 400. |
| FR5-07 | Authorization and privacy | Guests redirect to login; non-admins receive 403. Downloads are private/no-store and capped at 2,000 PDF or 10,000 CSV rows. |
| FR5-08 | Rate limiting | Login/register POSTs, confirmation POSTs and availability polls have explicit IP-based limits; other pages use a global limit. |
| FR5-09 | Security checks | CSRF on mutations; bounded form values; security headers; 128-KiB request limit; secure cookie, trusted host and shared limiter store required in production. |
| FR5-10 | Demonstration | `seed-events` remains idempotent; `seed-demo` creates fictional users, a sample booking history and blocked seats only in development with a private password. |
| FR5-11 | Manuals | Complete user, admin, installation/deployment and security guides ship in repository. |
| FR5-12 | Compatibility | V1–V4 routes and models preserved; no new table required for V5 reports. |

## Retained critical invariants

1. A booking reserves exactly one event seat; a multi-seat confirmation saves all bookings in one transaction.
2. An active seat is allocated to at most one booking (SQLite partial unique index).
3. A blocked seat may not be reserved and a reserved seat may not be blocked (three SQLite triggers).
4. Only owners cancel their own bookings; administrators may cancel any booking; history is never deleted.
5. Email notifications follow successful commits and failures cannot roll back bookings.
6. Admin-only UI uses per-action POST/CSRF; all data exports require fresh role authorization.

## Non-functional requirements

- Maintainability: application factory, separated report/notification/seed services, templates, tests and documentation.
- Accessibility: semantic forms, clear seat states, keyboard-operable buttons, responsive reporting controls.
- Performance: SQL aggregation for report counts; paginated bookings UI; row-limited exports.
- Privacy: no-store on report downloads, CSV formula mitigation, no hardcoded credentials and local DB excluded from Git.
- Deployment: Gunicorn behind HTTPS, dedicated low-privilege user, private SQLite volume, Redis rate limiting and protected SMTP; no `debug=True`.
- Availability: polling every five seconds is near-real-time; no seat holds or live push.

## V5 acceptance checklist

- [ ] Guest is redirected from all report endpoints, student/staff receive 403.
- [ ] Admin can download nonempty booking PDF and event PDF (start with `%PDF-`).
- [ ] Both CSV exports open correctly; formula-looking values are prefixed with apostrophe.
- [ ] Invalid status/event report filters are rejected; cancelled filtering works.
- [ ] Report attachment and Cache-Control private/no-store headers are present.
- [ ] Registration/login rate limits show 429 after repeated requests (in rate-limiting-enabled environment).
- [ ] All write routes reject missing CSRF token; sessions use secure settings when deployed.
- [ ] All V1–V4 unit/integration tests pass after installation.
- [ ] Fresh seed and demo seed are repeatable without creating duplicate active reservations.
- [ ] PDF report, README, manuals, UML, changelog and GitHub release description are included in ZIP.

## Explicit exclusions and deployment warning

No payments, QR tickets, refunds, durable email queue, password reset, MFA, distributed seat holds, certified student privacy compliance or full schema migration framework. SQLite and polling remain appropriate for limited load only. A publicly exposed campus system requires independent security review and operational acceptance.
