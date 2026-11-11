# CSTBS v5.1 — University Accounts & Free Reservations

## GitHub release description

Version 5.1 makes the Campus Stadium Ticket Booking System easier to operate for real university workflows. Students can self-register with a mandatory unique Student ID, while university administrators can create accounts from a dedicated secure registration page using a one-time registration key.

### Added
- Required unique 6–20 character Student ID on student registration.
- Separate administrator registration protected by a 60-minute, single-use key.
- Initial local setup key generated and shown in the terminal (no direct PyCharm or SQLite user editing).
- Administrator dashboard controls to issue more admin invitations and edit student IDs.
- Self-service Student ID completion for accounts migrated from earlier versions.

### Changed
- University events and reservations are **free admission (RMB/CNY, ¥0.00)**.
- Removed price input from administrator event creation/edit screens and removed payment totals from booking views.
- Seeded events and new booking snapshots are always zero-cost.
- Booking/event PDF and CSV reports now display free CNY admission, not revenue.

### Preserved
- Flask authentication and protected roles; administrator events, seats and sections management; conflict-safe seat reservations; booking history, cancellations, emails, PDF/CSV reports and responsive UI.

### Security and migration
- Administrator keys are random, keyed-hash stored, expiring, one-time and atomically consumed.
- Student ID uniqueness is enforced in SQLite; all registration/admin changes use CSRF and rate limits.
- Backward-compatible SQLite schema upgrade preserves user accounts and booking history; existing event prices are set to zero; historical booking price snapshots remain stored but are not charged or displayed.

**Release tag:** `v5.1`  
**Release title:** CSTBS v5.1 — University Accounts & Free Reservations  
**Status:** Complete source update; execute Flask integration tests and deployment review before live usage.
