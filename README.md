# CSTBS v5.4 — Stadium Operations & Ticket Experience

A Flask-based university stadium event system. Students can reserve **free** assigned seats for themselves and verified classmates, receive one signed QR admission pass per attendee, and enter through an authorized staff gate check-in. Administrators manage events, seat sections, bookings, users, gate operations and private PDF/CSV reports.

**Release:** `v5.4` · **Python:** 3.10+ · **Database:** SQLite · **Admission:** ¥0.00 CNY / no payment gateway

## Features

| Audience | Features |
|---|---|
| Public | Animated responsive home, events and details; day/night theme switcher |
| Students | Register with unique Student ID (6–20 alphanumeric); login, account, personal booking history |
| Booking | Interactive seat map; five-second availability polling; select up to six seats per checkout; match each attendee's existing student account; first seat for the booker; one live ticket per student per event; atomic seat and ticket creation |
| Tickets | Individual non-personal signed QR references; printable on-screen ticket; cancelled/used/unknown tickets rejected |
| Staff | Browser camera scan when supported **or on-device QR photograph upload** via OpenCV (works without BarcodeDetector); choose physical gate, verify ID, one-use check-in and attendance overview |
| Admin | First admin provisioned locally via a one-time 20-minute activation key; **normal email/password login thereafter**; stadium control dashboard, per-event and per-gate entry controls, section-to-gate assignments, event CRUD, seats, student/staff roles, bookings, check-ins, reports |
| Security | Password hashing, Flask-Login, role authorization, CSRF, rate limiting, private ticket images, safe CSV exports, unique-ticket/seat constraints, SQLite foreign keys, session revocation on admin reset |
| Developer | V5.2-compatible SQLite migration with automatic pre-upgrade backup, private `.env`/DB, GitHub Actions CI, health endpoint, integration test suite |

**Limitations:** Live browser camera scanning requires HTTPS/localhost and compatible BarcodeDetector support; the separate camera/gallery photo upload works without it, but still depends on browser camera/photo permissions. No payment, refunds or QR sharing feature. A ticket is assigned only to a registered student who supplies matching Student ID and full name. Obtaining permission from classmates and verifying their physical university ID are operational requirements. Time displayed follows your configured campus/server timezone; production should standardize and document timezone policy.

## Windows PowerShell: First run

1. Install Python 3.10+ and extract the ZIP into `CSTBS-v5.4`.
2. Open PowerShell **inside that folder** and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app run.py init-db
python -m flask --app run.py seed-events
python run.py
```

If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.

3. On the first **interactive local** server start, if no admin exists, enter admin email and name at the terminal prompt. A **20-minute, single-use activation key** appears once. **Do not put it into Notepad, `.env` or Python source.**
4. Open `http://127.0.0.1:5000/admin/activate`, enter the admin email, activation key and a new password (12–128 characters). After success you reach the dashboard.
5. **Future logins:** `http://127.0.0.1:5000/admin/login` → email and password; no key needed.
6. Students register at `/register` with their Student ID, name, email and password, then use `/login`.

Development automatically generates a stable private `instance/.local_secret_key` if you have not set `SECRET_KEY`; it is ignored by Git. A `.env` file is therefore optional for the local demonstration. Never overwrite this secret on an existing installation: the QR signing key falls back to it in development.

### If the admin activation key expires

```powershell
# Second PowerShell window, with .venv active
python -m flask --app run.py admin-key admin@university.edu
```

This is only for administrators **not yet activated**. To deliberately recover/reset an **already activated** administrator account (revokes its password/session), a trusted local operator runs:

```powershell
python -m flask --app run.py admin-reset admin@university.edu
```

Admin users can promote another account through **Admin → Users**, then issue an activation key there. Existing active admin passwords can only be reset after an explicit confirmation. No admin registration endpoint exists.

### Optional demonstration dataset

The demo command is **development-only**; it requires `DEMO_SEED_PASSWORD` configured privately and creates only local demo users. In PowerShell:

```powershell
$env:DEMO_SEED_PASSWORD = 'use-a-long-random-demo-password'
python -m flask --app run.py seed-demo
Remove-Item Env:DEMO_SEED_PASSWORD
```

The event seed is idempotent. Demo tickets have distinct student attendees; none are promoted automatically in a production environment.

## Reservation and gate flow

1. Student logs in and selects 1–6 open seats on an upcoming event.
2. In **Review**, the first seat is assigned to themselves. Each additional seat requires the registered student's full name and Student ID. CSTBS checks registered accounts and existing live tickets.
3. On **Confirm**, the database writes the seat bookings and matching individual tickets in one transaction; race conditions reject the whole conflicting attempt.
4. Students open **Student dashboard** (`/dashboard`) to view personal passes, including tickets booked by classmates. Tickets display event date, time, venue, gate, section, row/seat, attendee ID and unique QR.
5. Admin opens **Stadium control** (`/admin/`) and uses **Open entry** to open all entrances for that event; **Manage gates** assigns sections to named entrance gates and can close individual gates.
6. Staff/admin selects their physical gate at **QR scanner** (`/entry/scan`), scans live using BarcodeDetector or uses the **QR photograph** fallback, and matches university ID. A valid ticket at a closed/wrong gate shows a clear waiting message. Staff explicitly presses **Confirm entry** (CSRF POST) once.
7. Repeated scans show **Already checked in**. Cancelled or unassigned tickets cannot enter. Checked-in tickets are preserved and cannot be cancelled using normal cancellation controls.

## Upgrading an existing V5.2 / V5.3 installation

1. Stop the old server and **back up** `instance/cstbs.db`; copy it into the new version's `instance/`. Also preserve the existing `SECRET_KEY` from your environment or `instance/.local_secret_key`; otherwise sessions and existing HMAC keys will not survive. For public deployments preserve your explicit `TICKET_SIGNING_KEY` as well.
2. Run `python -m flask --app run.py init-db`. For V5.3 and earlier SQLite schemas, the migration saves an integrity-checked snapshot in ignored `instance/backups/` **before adding gate fields**, backfills Gate 1 for each event, and preserves tickets, QR secrets and check-ins. The upgrade is idempotent.
3. Existing admin roles remain, but **admins must activate a password once** with a new 20-minute key. Run `admin-key EMAIL` or start interactively. Students continue to log in normally.
4. The upgrade preserves V5.2 bookings. For a student who held multiple active seats at the same event, **only the first can automatically become that student's QR ticket**. The others remain reserved with **unassigned** ticket status, which an admin must assign to a different verified registered attendee in **Admin → Bookings**. No history or seat reservation is silently deleted.
5. Re-run all tests, inspect capacity, test key activation, confirm a QR scan and restore from backup if unexpected inconsistencies appear.

More detailed upgrade/backup steps: [`docs/installation-deployment.md`](docs/installation-deployment.md).

## Testing and GitHub-safe workflow

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app tests run.py config.py
python -m flask --app run.py backup-db
```

The GitHub Actions workflow runs checks on pushes and pull requests; **it does not deploy or touch your live DB**. Enable branch protection requiring CI to pass before merging. Deploy only an approved release artifact after a separate DB backup and reviewed migration. GitHub contains source code, not your runtime database. Use persistent storage and stable secrets at the actual host. See [`SECURITY.md`](SECURITY.md) and [`docs/installation-deployment.md`](docs/installation-deployment.md).

**Important:** Each gate starts CLOSED after a fresh event is created or a legacy event is upgraded. This is intentional safety behavior. Admin opens it with **Stadium control → Open entry**. Choose the matching gate in the scanner. A closed gate produces **Valid ticket — entry not open**, rather than a fraudulent-code result. No HTML camera solution can bypass browser permissions or the HTTPS secure-context requirement.

**Health endpoint:** `GET /health` returns `{"status":"ok","version":"5.4"}` when DB queries work.

## Project documentation

- [`docs/user-manual.md`](docs/user-manual.md) — booking for classmates, QR tickets, cancellation
- [`docs/admin-manual.md`](docs/admin-manual.md) — first admin activation, stadium operations, attendee correction
- [`docs/installation-deployment.md`](docs/installation-deployment.md) — Windows, environments, migrations, backups, deployment
- [`docs/database-design.md`](docs/database-design.md) — V5.4 ER model, constraints and legacy compatibility
- [`docs/uml.md`](docs/uml.md) — PlantUML class, activity and entry sequence diagrams
- [`docs/github-release-v5.4.md`](docs/github-release-v5.4.md) — copy-ready GitHub release text
- [`CHANGELOG.md`](CHANGELOG.md) — V1.0 through V5.4

**Not a payment or public university identity-verification system.** For broader production use, obtain consent, perform institutional security and privacy review, adopt production-grade backups and monitoring, and plan a scalable database and trustworthy MFA/SSO for privileged users.

## Role dashboards & QR scanner troubleshooting (V5.4)

- **Students:** visit `/dashboard` after password login, then use *My admission passes*. The ticket holder sees their own QR even if a classmate made the group reservation. One active ticket per Student ID per event is enforced in the database.
- **Admins:** visit `/admin/` after activation/password login. It shows events, attendance, reservations, open gates, and prominent **Open entry** / **Close entry** controls. Use **Manage gates** to add/rename a gate and assign sections, **Seats** to block seats, **Users** to manage roles, and **Reports** for PDF/CSV.
- **Staff:** log in normally and use `/entry/scan` (admin can use it too). Pick the event/gate first. For live video use HTTPS or localhost and grant permission. If `BarcodeDetector` is unavailable, tap **Read QR photograph** and use the phone camera or gallery. Manual pasted signed codes are also supported.
- **QR data:** the code is an opaque signed token, not an exposed Student ID or a `localhost` hyperlink. Use the CSTBS scanner/photo decoder rather than expecting the generic camera app to open a website from this QR.
- **When the screen says entry not open:** the ticket is valid, but an admin must open entry on the stadium dashboard. For *wrong gate*, direct the attendee to the gate printed on their ticket. For *already checked in*, do not admit a second time.

**Dependency note:** V5.4 adds `opencv-python-headless` for reliable server-side QR-photo decoding, in addition to `qrcode[pil]`. Install with `python -m pip install -r requirements.txt` again after updating.
