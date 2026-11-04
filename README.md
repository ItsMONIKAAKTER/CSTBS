# CSTBS v5.3 — Smart University Stadium Ticketing

A Flask-based university stadium event system. Students can reserve **free** assigned seats for themselves and verified classmates, receive one signed QR admission pass per attendee, and enter through an authorized staff gate check-in. Administrators manage events, seat sections, bookings, users, gate operations and private PDF/CSV reports.

**Release:** `v5.3` · **Python:** 3.10+ · **Database:** SQLite · **Admission:** ¥0.00 CNY / no payment gateway

## Features

| Audience | Features |
|---|---|
| Public | Animated responsive home, events and details; day/night theme switcher |
| Students | Register with unique Student ID (6–20 alphanumeric); login, account, personal booking history |
| Booking | Interactive seat map; five-second availability polling; select up to six seats per checkout; match each attendee's existing student account; first seat for the booker; one live ticket per student per event; atomic seat and ticket creation |
| Tickets | Individual non-personal signed QR references; printable on-screen ticket; cancelled/used/unknown tickets rejected |
| Staff | Mobile-friendly camera scan (where `BarcodeDetector` is supported), camera-app / manual QR fallback, separate verified one-use check-in, attendance overview |
| Admin | First admin provisioned locally via a one-time 20-minute activation key; **normal email/password login thereafter**; dashboard, event CRUD, booking/gate open/close, sections and seat blocking, roles, attendee correction for legacy bookings, bookings, ticket/cancellation oversight, attendance, PDF/CSV exports |
| Security | Password hashing, Flask-Login, role authorization, CSRF, rate limiting, private ticket images, safe CSV exports, unique-ticket/seat constraints, SQLite foreign keys, session revocation on admin reset |
| Developer | V5.2-compatible SQLite migration with automatic pre-upgrade backup, private `.env`/DB, GitHub Actions CI, health endpoint, integration test suite |

**Limitations:** `BarcodeDetector` is not supported by all browsers; a phone's native camera or manual QR link can be used. No payment, refunds or QR sharing feature. A ticket is assigned only to a registered student who supplies matching Student ID and full name. Obtaining permission from classmates and verifying their physical university ID are operational requirements. Time displayed follows your configured campus/server timezone; production should standardize and document timezone policy.

## Windows PowerShell: First run

1. Install Python 3.10+ and extract the ZIP into `CSTBS-v5.3`.
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
4. Student accesses **My tickets** and opens each QR ticket. Group attendees also see their own ticket from their account.
5. Admin opens **Gate** for that event under **Admin → Events**. Staff/admin goes to **QR gate** on a phone. QR scan opens a read-only verification page; staff verifies identity and presses **Confirm stadium entry** (POST + CSRF).
6. Repeated scans show **Already used**. Cancelled or unassigned tickets cannot enter. Checked-in tickets are preserved and cannot be cancelled using normal cancellation controls.

## Upgrading an existing V5.2 installation

1. Stop the old server and copy `instance/cstbs.db` into the new version's `instance/`. Also preserve the existing `SECRET_KEY` from your environment or `instance/.local_secret_key`; otherwise sessions and existing HMAC keys will not survive. For public deployments preserve your explicit `TICKET_SIGNING_KEY` as well.
2. Run `python -m flask --app run.py init-db`. On a legacy SQLite DB the migration automatically creates an integrity-checked pre-upgrade snapshot in ignored `instance/backups/` **before changing the schema**. The migration is idempotent.
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

**Health endpoint:** `GET /health` returns `{"status":"ok","version":"5.3"}` when DB queries work.

## Project documentation

- [`docs/user-manual.md`](docs/user-manual.md) — booking for classmates, QR tickets, cancellation
- [`docs/admin-manual.md`](docs/admin-manual.md) — first admin activation, stadium operations, attendee correction
- [`docs/installation-deployment.md`](docs/installation-deployment.md) — Windows, environments, migrations, backups, deployment
- [`docs/database-design.md`](docs/database-design.md) — V5.3 ER model, constraints and legacy compatibility
- [`docs/uml.md`](docs/uml.md) — PlantUML class, activity and entry sequence diagrams
- [`docs/github-release-v5.3.md`](docs/github-release-v5.3.md) — copy-ready GitHub release text
- [`CHANGELOG.md`](CHANGELOG.md) — V1.0 through V5.3

**Not a payment or public university identity-verification system.** For broader production use, obtain consent, perform institutional security and privacy review, adopt production-grade backups and monitoring, and plan a scalable database and trustworthy MFA/SSO for privileged users.
