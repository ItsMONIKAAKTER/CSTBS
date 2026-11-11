# V5.4 stadium operations quick manual

**Admin dashboard:** `/admin/`. First-time administrator activates their account with a single-use 20-minute key on `/admin/activate` and sets a password; normal subsequent login is `/admin/login`. Do not edit source, Notepad or the database to provision a key.

1. Select an event in the dashboard. **Open entry** opens all its entrances together; **Close entry** stops all check-ins. Gates start CLOSED for safety. This setting is separate from public seat booking availability.
2. Click **Manage gates** for the event. Add/rename gates (e.g. Gate 1 / North Gate); assign each seating section to its actual entrance; optionally open/close individual entrances. Do not reassign sections after people enter.
3. Under **Events & seats**, create/edit events, manage sections, block seats without active bookings, and control seat reservation availability.
4. Under **Students & staff**, manage Student IDs and roles. Under **Bookings**, cancel unentered tickets, inspect attendees, and assign verified registered students to legacy unassigned seats.
5. **Staff entry:** staff or admin logs into `/entry/scan`, selects their physical gate, and scans live over HTTPS/localhost or photographs the ticket QR. The verification screen shows either VALID TICKET, a waiting reason (wrong/closed gate), cancelled, invalid, or already used. Only **Confirm entry** records admission.
6. Export PDF/CSV attendance and booking reports using Reports. Preserve keys and private data, verify ID at the entrance, and test all scan devices before opening.

**Troubleshooting:** If a valid ticket says ENTRY NOT OPEN, click Open entry for its event. If it says WRONG GATE, send the attendee to the gate on the pass. If live video is unsupported or camera permission is denied, select the gate and upload a QR photograph. Phone camera use needs HTTPS or localhost, while photo capture is the cross-browser fallback.


# CSTBS v5.3 — Administrator and Gate Staff Manual

## First administrator activation (no Notepad)

Local interactive startup (`python run.py`) prompts for first administrator email/name **only when no admin exists**. It prints a single-use 20-minute activation key. Open `/admin/activate`, supply email/key and choose a strong password. The key is consumed. Future access is `/admin/login` with **email + password**. There is no public admin registration and no manual editing of a key in code, `.env` or SQLite.

For an expired key, if the account is not activated, run `python -m flask --app run.py admin-key EMAIL` in a trusted terminal. For account recovery after activation, a trusted operator runs `admin-reset EMAIL`, which revokes previous password sessions and issues a key. Protect terminal access and never publish keys.

## Admin dashboard and event management

- `/admin/`: KPIs, active bookings and quick links.
- `/admin/events`: Create/edit/delete events; manage seats and sections. Deletion is refused once an event has booking history.
- **Booking ON/OFF**: controls whether upcoming events accept new reservations.
- **Gate OPEN/CLOSED**: enables or prevents staff check-ins. Keep the gate closed until event staff are present and have verified entry procedures.
- `/admin/events/<id>/seats`: Add/rename unused sections, block/unblock individual seats. Reserved seats cannot be blocked or removed until their reservation is cancelled.

## Students and administrator roles

`/admin/users` allows the admin to inspect students, correct Student IDs and assign staff/admin roles. Do not promote untrusted people. Promoting a user to admin invalidates their previous password and requires an explicit **activation key**. To reset an already activated admin password, check the explicit reset confirmation before generating a new key. Never demote the last admin. Campus staff can scan QR tickets but cannot perform event CRUD or download private reports.

## Booking and legacy attendee management

`/admin/bookings`: filter by event/status, review booking owners and each ticket's actual attendee, cancel unused bookings. A QR represents one **attendee**, not the purchaser. An old V5.2 multi-seat booking may be labeled **unassigned**. For these rows, verify the original booking ownership and the new attendee's consent/name/Student ID, then use **Assign attendee**. The system rejects duplicate live tickets for the same event/student.

Do not cancel checked-in reservations as normal operations; entry history stays intact. If a student is ineligible or a QR appears duplicated, stop entry and investigate rather than overriding the gate record.

## QR check-in operations

1. Assign trusted gate workers the **staff** role. All gate workers must use their own account and secure device.
2. Open the relevant event's **Gate** control before admitting people.
3. Open `/entry/scan` on a mobile browser. In Chromium-based browsers with `BarcodeDetector`, choose **Start camera**; camera access requires HTTPS or localhost. Otherwise use the phone's camera app to scan the QR URL or paste the URL in the manual verification field.
4. The app opens `/entry/verify/<signed-code>` and shows **Valid**, **Already used**, **Cancelled**, **Unassigned**, **Gate closed**, or **Invalid**. Compare the ticket name and Student ID with the student's physical identity document.
5. Press **Confirm stadium entry** only for valid and matching attendees. The server updates the ticket conditionally so two gates cannot record a second admission. The page then shows **Already used** on subsequent attempts.
6. Close the event gate after the session and export attendance from `/admin/reports/attendance.csv` or `.pdf`.

## Reports and privacy

Admins can download event, booking and attendance PDF/CSV. These exports contain students' names, IDs and emails; store them privately according to your university's retention policy. Never push reports or SQLite databases to GitHub.

## Operational safety

Back up the SQLite file and stable signing keys before upgrades. Use `flask backup-db` on demand. For multi-gate high-volume university operation, use institution-approved hosting, monitoring, transaction-capable central storage, and a reviewed authentication policy (MFA/SSO recommended).
