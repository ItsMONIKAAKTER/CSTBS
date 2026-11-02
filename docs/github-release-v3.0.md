# CSTBS v3.0 — Seat Reservations

Version 3.0 of the **Campus Stadium Ticket Booking System** introduces end-to-end seat reservations while retaining the V2 authentication, roles and administrator event-management features.

## What's new

- **Interactive seat map:** responsive A1–F10 visual seating grid with available, selected, and reserved states.
- **Near-real-time availability:** seat status updates from a no-cache JSON endpoint every five seconds.
- **Complete reservation flow:** select up to six seats, review seat assignments and total, then confirm to save bookings in SQLite.
- **Safe booking writes:** atomic multi-seat booking, server-side validation and a partial unique SQLite index prevent double-booking.
- **My bookings:** personalized booking history with reserved and cancelled seat records.
- **Self-service cancellation:** users may cancel only their own bookings, immediately releasing seats for other students.
- **Expanded database models:** fully implemented Seat and Booking relations, booking price snapshots, event seat seeding and V2-compatible SQLite upgrades.
- **Documentation and tests:** updated requirements, PlantUML diagrams, database design, README, changelog and reservation integration test suite.

## Preserved from v2.0

Flask-Login registration and login, Werkzeug password hashing, student/staff/admin roles, protected routes, public events and administrator CRUD.

## Scope and limitations

Bookings allocate seats but **do not collect payment or issue tickets**. Availability is five-second polling rather than WebSocket push; seats are not held during selection. SQLite is intended for a development/demo campus project.

**Suggested GitHub tag:** `v3.0`  
**Release title:** `CSTBS v3.0 — Seat Reservations`
