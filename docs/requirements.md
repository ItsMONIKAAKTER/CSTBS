# CSTBS Version 3 — Requirements and Acceptance Criteria

## Goal & boundary

Version 3 adds **seat reservations** to the Version 2 authenticated event catalog. Visitors can browse events; signed-in students, staff and admins can reserve and cancel their own labelled event seats. Administrators still manage events. No payment or ticket fulfilment is performed.

## Actors and access

| Actor | Browse catalog | See seat availability | Reserve / cancel own | Admin event CRUD |
| --- | --- | --- | --- | --- |
| Anonymous | Yes | Yes (JSON) | No | No |
| Student | Yes | Yes | Yes | No |
| Staff | Yes | Yes | Yes | No |
| Admin | Yes | Yes | Yes | Yes |

Public registration always produces `student` users; only trusted CLI operators may elevate roles.

## Functional acceptance matrix

| ID | Requirement | Acceptance test |
| --- | --- | --- |
| FR3-01 | Seat inventory | New events receive 60 labelled seats (`A1`–`F10`). Existing V2 events with no seats are backfilled without overwriting custom rows. |
| FR3-02 | Interactive map | Signed-in user sees a responsive grid, available/reserved/selected legend and keyboard-focusable buttons. |
| FR3-03 | Availability feed | Public no-cache JSON reports current occupied IDs, total/available seats and booking-open state. JS polls every 5 seconds. |
| FR3-04 | Selection validation | Server checks event membership, duplicate IDs, maximum six seats, occupancy, event start time. |
| FR3-05 | Review | POST selection creates short-lived pending selection in signed session and displays seat labels, quantity and calculated total. |
| FR3-06 | Confirmation | POST with CSRF and pending session records seat bookings in one transaction, or rolls everything back when a conflict occurs. |
| FR3-07 | No double-booking | SQLite enforces one active (`reserved`) booking per seat using a partial unique index. |
| FR3-08 | Personal booking history | `GET /bookings` shows only the current user's reservations, including cancelled records. |
| FR3-09 | Cancellation | POST+CSRF for owner cancels one seat and frees it; another user's booking ID returns 404. |
| FR3-10 | Admin event rules | Admin-created events get seats; event deletion succeeds only when no booking row references its seats. |
| FR3-11 | Preservation | V2 user sessions, roles, CRUD and public pages remain working. |
| FR3-12 | V2 SQLite upgrade | Adds booking price snapshot and unique active-seat index; preserves existing users, events, seats and bookings. |

## Non-functional acceptance criteria

- **Consistency:** Database uniqueness guarantees that a seat never has two *active* reservations, including concurrent requests.
- **Security:** authentication on reservation and cancellation; CSRF tokens; server-side ownership/seat validation; role guards; no hardcoded secrets.
- **Responsiveness:** mobile grid horizontally scrollable within a labelled region; checkout stacks below map; buttons are keyboard usable and announced via ARIA.
- **Usability:** reservation confirmation page shows price; stale selections produce an error and a safe return to map; no implied payment.
- **Testability:** Flask test-client cases exercise happy path, forbidden actions, stale selection, index uniqueness and schema upgrade.

## Main journey

1. Visitor browses events and signs in.
2. User opens a future event's map and chooses one to six seats.
3. Browser fetches current availability every five seconds. Any taken seat is disabled.
4. User reviews seat labels and estimated total.
5. User confirms. The server revalidates and commits all chosen bookings atomically.
6. User views booking history, optionally cancels individual seats. Cancelled history remains and seats become available.

## Out of scope

No live WebSocket server, temporary seat holding / reservation expiry, charge collection, refunds, email confirmations, QR codes, order groups, scans, or production migration/hosting layer. The existing seat map is a default general `Main` section, not a venue-specific configuration editor.

## Manual smoke-test checklist

- [ ] Create account, log in, open future event map.
- [ ] Pick two available seats and review labels + total.
- [ ] Confirm and verify both entries in My bookings; API shows both reserved.
- [ ] In a second signed-in account, verify the seats are unavailable.
- [ ] Cancel one seat from the first account; verify it is free and selectable again.
- [ ] Attempt to cancel the other account's booking; verify HTTP 404.
- [ ] Try to reserve more than six and submit tampered seat IDs; verify rejection.
- [ ] Race two confirmations for the same seat; verify only one succeeds.
- [ ] Create/delete an unbooked event as admin; refuse deletion after booking history.
- [ ] Run `python -m unittest discover -s tests -v`.
