# CSTBS v5.3 — Smart University Stadium Ticketing

## Overview

CSTBS v5.3 upgrades the university stadium booking system with one-time administrator account activation, secure reusable admin password login, verified group reservations, individual QR tickets, mobile stadium check-in, stadium entry controls, and a polished day/night interface.

## New features

- **Simplified admin onboarding:** initial or recovery keys are generated automatically in the local terminal or issued by an existing admin. They expire after 20 minutes and are used only to activate/reset an admin password. Normal admin login thereafter uses email and password.
- **Registered-student group bookings:** each student has at most one active ticket for each event. Extra seats require a verified registered attendee's full name and Student ID.
- **Signed individual QR tickets:** private QR admission references, one per attendee, bound to live ticket and booking state.
- **Stadium gate verification:** staff/admin camera scanner (supported browsers) and manual fallback, check-in confirmation, anti-replay controls, attendance overview.
- **Administrator operations:** booking and gate open/close toggles, legacy attendee correction, QR/ticket oversight, and private attendance CSV/PDF exports; event, seat, section, role and booking management preserved.
- **Polished design:** responsive Campus Light and Stadium Night themes, animations with accessibility-aware reduced motion.
- **Safer GitHub workflow:** tests on push/PR, no automatic deployment, SQLite backup before V5.3 schema changes, Git hygiene and a health endpoint.

## Preserved from V1–V5.2

Events, Student ID registration, event CRUD, seat map, occupancy polling, booking history and cancellation, staff/admin roles, email notices, PDF/CSV reporting, free reservations and ¥0.00 CNY formatting.

## Upgrade notes

Back up `instance/cstbs.db` and preserve application and QR signing secrets. Existing admins must activate a password once. Existing multi-seat bookings remain in the database; extra unassigned seats need verified attendee assignment before QR entry. No payment service is required.

## Testing and deployment

Includes targeted Flask tests and GitHub Actions CI. Full integration, concurrency and production-security verification must be completed in an environment with installed dependencies before hosting real stadium operations. GitHub pushes do not mutate production data or trigger deployments.

**Version:** 5.3.0  
**GitHub tag:** `v5.3`  
**Release title:** *CSTBS v5.3 — Smart University Stadium Ticketing*
