# CSTBS Version 4 — Requirements and Acceptance Criteria

## Goal

Extend V3 *Seat Reservations* with a safe, role-protected administration console and development email notifications. Retain accounts, public event catalog, event CRUD, interactive selection, multi-seat reservation and owner cancellation. No payments or ticket fulfilment.

## Access matrix

| Feature | Visitor | Student | Staff | Admin |
| --- | --- | --- | --- | --- |
| Browse events / availability JSON | Yes | Yes | Yes | Yes |
| Reserve / cancel own seats | No | Yes | Yes | Yes |
| View dashboard and admin data | No | No | No | Yes |
| Event CRUD and seating administration | No | No | No | Yes |
| Manage roles / all bookings | No | No | No | Yes |

Public registration cannot choose roles. Admin-only operations require authentication and role enforcement server-side.

## Functional requirements

| ID | Feature | Acceptance criteria |
| --- | --- | --- |
| FR4-01 | Admin dashboard | `/admin/` shows KPI totals and recent reservations. Students/staff receive 403; anonymous users go to login. |
| FR4-02 | Event CRUD | Existing admin create/edit/delete remains available under the admin navigation; newly created event includes 60 default seats; no deletion with any history. |
| FR4-03 | Seat blocking | Admin can block/unblock a free seat; a reserved seat cannot be blocked. Public availability excludes blocked seats and JS marks them clearly. |
| FR4-04 | Sections | Admin can add a uniquely named section (1–20 rows, 1–30 seats each), rename it, and delete it only when it has no booking history. |
| FR4-05 | User roles | Admin can promote/demote another registered user among student/staff/admin; cannot change their own role or remove the sole admin via UI. |
| FR4-06 | All bookings | Admin sees reserved/cancelled bookings across all users with event/status filters and pagination. |
| FR4-07 | Administrative cancellation | Admin can cancel active bookings and retain history. Duplicate cancellation doesn't resend email. |
| FR4-08 | Confirmation notification | Successful checkout sends one email (or prints preview) with event, seats, time and informational total, after commit. |
| FR4-09 | Cancellation notification | Owner and admin cancellation send one email/preview to booking owner after commit. |
| FR4-10 | Email configuration | Flask-Mail supports console preview without SMTP and Ethereal SMTP via environment variables, no hardcoded secrets. |
| FR4-11 | Upgrade compatibility | Existing V3 SQLite seats gain `is_blocked=0` by non-destructive startup schema upgrade. Booking history remains. |
| FR4-12 | Integrity | Database protects against double-booking, reserving blocked seats and blocking active bookings, including racing writes. |
| FR4-13 | Preservation | All V1–V3 routes, sessions, event catalog, roles, user booking history and cancellation continue to work. |

## Non-functional requirements

- **Security:** admin-only routes, CSRF on mutations, parameter/enum validation, no public role elevation, no secrets in source, ownership restrictions on personal booking routes.
- **Integrity:** SQLite partial unique active-seat index and block-state triggers. Cancellation preserves booking records and historical price snapshots.
- **Accessibility:** native form controls, focus states, page headings, labelled seat buttons, responsive tables and sectioned map.
- **Performance:** booking admin uses pages of 25 rows; dashboards use aggregate SQL. Seat polling remains every 5 seconds, no WebSockets.
- **Mail durability:** an email failure cannot roll back an already confirmed booking. Delivery is best-effort and log-based; no outbox or retry service yet.

## Manual acceptance checklist

- [ ] As student or staff, all `/admin/` pages return HTTP 403 after sign-in; anonymous users redirect to login.
- [ ] As admin, create, edit and delete an unbooked event; booked event deletion is refused.
- [ ] Create a new `West Stand` section, rename it, block/unblock a free seat, and inspect the public availability API and map.
- [ ] Confirm bookings cannot reserve blocked seats; verify a reserved seat cannot be blocked.
- [ ] Promote student to staff, then admin; verify another admin can change their role, but not their own.
- [ ] Filter all bookings by event/status; cancel a student's active reservation as admin.
- [ ] Confirm one email preview appears after checkout, and another after cancellation; repeated cancellation doesn't send another.
- [ ] Try SMTP with Ethereal test credentials; ensure no credentials are printed.
- [ ] Upgrade a backed-up V3 SQLite DB and verify existing bookings/seats remain intact and `is_blocked` defaults false.
- [ ] Run `python -m unittest discover -s tests -v` and smoke-test small screens.

## Explicit exclusions

No payments, refunds, QR ticket issuance, email queue/retry service, irreversible deletion of bookings, complex seating geometry, external identity provider, migration framework, audit log, or production deployment system.
