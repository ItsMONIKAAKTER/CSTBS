# CSTBS v5.4 — Stadium Operations & Ticket Experience

Version 5.4 improves the Campus Stadium Ticket Booking System with reliable QR entry and role-specific stadium dashboards.

## New in this release
- Admin-only **Stadium Control Center** with event-specific Open Entry / Close Entry and occupancy snapshots.
- Student-only dashboard for upcoming events and personal QR passes, including tickets booked by classmates.
- **Event gates:** create, rename and independently open/close named entrances; map stadium sections to gates. All legacy sections migrate to Gate 1.
- **Camera/photo scanner fallback:** OpenCV-backed QR photograph upload if live browser BarcodeDetector is unavailable. Check-in continues to require a staff/admin account, correct open gate, identity check and explicit confirmation.
- **Clear verification results:** valid ticket not yet open, wrong gate, gate closed, cancelled, invalid, or already used; no false counterfeit warning for a valid ticket at a closed entrance.
- **Complete ticket information:** date, time, venue, ticket number, gate, section, row, seat, Student ID and an opaque signed QR. Admission remains free (¥0.00); no payment gateway.
- **Strict uniqueness:** one live ticket per registered Student ID per event, including group bookings; database and server guards retained.
- **UI and quality:** simpler navigation and admin controls, polished responsive role panels, accessible transitions and dark/light theme. Removed public version marketing footer.
- **GitHub-safe upgrades:** idempotent SQLite V5.4 migration, snapshot before schema changes, preserved QR credentials and booking data, expanded tests, updated manuals and read-only GitHub CI.

## Compatibility and deployment
Upgrade from V5.3 after backing up the existing DB and retaining the persistent signing key. Install updated requirements for QR photograph decoding. Newly created and upgraded gates begin closed; open them from the admin dashboard before scanning. Test the browser camera and photo fallback on actual staff devices over HTTPS. Full integration, concurrency and security acceptance are required before real campus deployment.

**Version:** 5.4.0  
**GitHub tag:** `v5.4`  
**Release title:** CSTBS v5.4 — Stadium Operations & Ticket Experience
