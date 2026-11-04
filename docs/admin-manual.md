# Administrator and Gate Staff Manual

## Administrator account

An operator creates the initial admin account with `python -m flask --app run.py admin-setup`. The terminal prints a secure one-time activation key valid for 20 minutes. Visit `/admin/activate`, enter the key and set a strong password. Future logins use `/admin/login` with email and password only. An existing admin may invite additional administrators from **Users**. Recovery requires a local operator with `admin-reset EMAIL`. Keys are not entered into `.env` or a Python file.

## Daily stadium operations

1. Sign in and open `/admin/` — the Stadium Control Center.
2. Manage events: create/edit event information, seating sections, and event-specific gates.
3. Assign sections to gate entrances; confirm every seat has the correct gate before admissions begin.
4. Enable/disable booking for an event and open entry when staff are ready. Opening event entry also opens its entrances. Individual gates may be closed independently.
5. Monitor reserved seats and check-ins from the dashboard. Block only unreserved seats; booked seats cannot be blocked.
6. Manage students, staff roles, reservations, cancellations, and assignment of legacy unassigned tickets. Never assign two live tickets for one student and event.
7. Download booking, event, and attendance PDF/CSV reports from the Reports page.
8. After the event, close stadium entry. Back up the database and retain audit information according to university policy.

## Gate staff

Staff sign in and open `/entry/scan`. Select the correct physical entrance gate, enable the camera over HTTPS or localhost, or upload a QR photograph. The server validates the signed token, ticket status, registered attendee, event, and gate. Visually verify the university ID before **Confirm entry**. A second check-in is rejected. A valid ticket at a closed gate is labelled **entry not open**, not fraudulent.
