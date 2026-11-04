# CSTBS v5.1 — University Accounts & Free Reservations

**Campus Stadium Ticket Booking System** is a Python 3.10+ Flask/SQLite web application for university events, free seat reservations, student accounts, secure administrator invitations, and campus stadium management.

This update extends the complete **V5.0** project, preserving event browsing, seat selection, conflict-safe bookings, cancellation, the admin dashboard, sections and seat blocks, booking emails, and PDF/CSV reports. All admissions are **free**; the display currency is **Chinese yuan (RMB/CNY, ¥)**, and **there is no payment collection or gateway**.

## What's new in V5.1

- **Student self-registration** at `/register` requires a unique 6–20-character Student ID (ASCII letters and digits). Values are normalized to uppercase and checked for duplicates both in Flask and SQLite.
- **Administrator self-registration** at `/register/admin` requires a valid, unexpired, one-time secret invitation key (plus name, email, password).
- **First administrator bootstrap**: local development displays a key **once in the `python run.py` server terminal** after the database is created, if no administrator exists. The key expires after 60 minutes and is stored as a keyed hash, not plaintext.
- **Admin-managed future invitations**: `/admin/users` issues additional one-use keys through a CSRF-protected button. The newly generated key is displayed once on a private, no-cache response. Admins share it privately.
- **Student ID management**: students with migrated accounts can fill/update their ID at `/account`; admins can correct student IDs and manage roles at `/admin/users`.
- **Free university events**: event creation/editing no longer accepts prices; new bookings cost ¥0.00. Existing event catalog price values are reset to zero during the V5.1 SQLite upgrade. Legacy booking price snapshots are retained privately for audit compatibility, never charged or shown as payment.
- Booking/event PDF and CSV reports show CNY `0.00` admission (not financial revenue).

## Roles and features

| Capability | Visitor | Student | Staff | Administrator |
|---|:---:|:---:|:---:|:---:|
| Browse public events | ✓ | ✓ | ✓ | ✓ |
| Self-register with required Student ID | ✓ | — | — | — |
| Register with single-use admin key | ✓ | — | — | — |
| Reserve seats / view and cancel own bookings | — | ✓ | ✓ | ✓ |
| Admin dashboard, event CRUD, seat blocks and sections | — | — | — | ✓ |
| Manage Student IDs, roles and admin invitations | — | — | — | ✓ |
| View/cancel all bookings; export PDF/CSV reports | — | — | — | ✓ |

## Windows 10/11 installation (PowerShell)

1. Extract `CSTBS-v5.1.zip`. Open PowerShell **inside `CSTBS-v5.1`**.
2. Install Python 3.10+, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

If activation is blocked by PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then try activation again. Paste the generated secret key into `.env` as `SECRET_KEY=<your-random-key>`. **Keep `.env` private.**

3. Initialize and run:

```powershell
python -m flask --app run.py init-db
python -m flask --app run.py seed-events
python run.py
```

Browse **http://127.0.0.1:5000**. The app runs on localhost only with debugger disabled.

### Create your first administrator — entirely from the website

When you first run `python run.py`, a key like `CSTBS-<random-secret>` appears **in the PowerShell window**. Copy it without sharing. Browse `http://127.0.0.1:5000/register/admin`, enter your name, email, password (12–128 characters), and the key. The key expires after **60 minutes**, and cannot be reused.

If you lose the first key or it expires, you can safely regenerate it (only while no admin exists):

```powershell
python -m flask --app run.py reset-bootstrap-key
```

Once an admin exists, additional admin keys are created from **Admin Dashboard → Users → Generate one-time admin key**, not with PyCharm or direct SQL. The admin sends the key privately to the new administrator. Keys are single-use and valid for 60 minutes. Student users register normally through `/register` and must supply their unique university Student ID.

**Note:** The initial automatic startup key is for local development. For production, run `flask init-db` followed by `flask reset-bootstrap-key` in a secure operator terminal; do **not** automatically print secrets into web-server logs.

### Optional local demonstration dataset

Create four illustrative free events using `seed-events`. To add fake accounts, blocked seats and sample booking records, set `DEMO_SEED_PASSWORD` in your private `.env`, then run:

```powershell
python -m flask --app run.py seed-demo
```

The demo password must be 12–128 characters. This command refuses `APP_ENV=production`, never resets existing accounts, and demo student ID is `DEMO1001`. Do not use these accounts on a public service.

## Main endpoints

| Route | Use |
|---|---|
| `/`, `/events`, `/events/<id>` | Public event browsing |
| `/register` | Student registration (Student ID required) |
| `/register/admin` | Admin invitation registration |
| `/login`, `POST /logout`, `/account` | Common authentication/profile |
| `POST /account/student-id` | Student updates their ID |
| `/events/<id>/seats` | Interactive seat map; availability API every five seconds |
| `/events/<id>/booking/review`, `/booking/confirm` | Free reservation checkout |
| `/bookings` | Booking history and cancellation |
| `/admin/` | Administrator dashboard |
| `/admin/events...` | Event CRUD and seat/section management |
| `/admin/users` | Student IDs, roles and administrator key invitation |
| `/admin/bookings` | Booking oversight/cancellation |
| `/admin/reports/` | Booking and event PDFs/CSVs |

## Security and data preservation

- Flask-Login, Werkzeug hashed passwords, Flask-WTF CSRF on all state-changing actions, Flask-Limiter on registration/login and booking confirmation.
- One-time admin keys use cryptographically secure randomness, HMAC-SHA256 fingerprints, expiration timestamps, and atomic consumption in a database transaction. No plaintext key is retained, and the dashboard invitation response is `Cache-Control: no-store`.
- SQLite enforces unique Student IDs, one active booking per seat, and booking/blocked-seat conflict prevention. User-submitted roles or event prices are ignored.
- Previous V5 accounts remain available. Existing students without an ID can complete their profile after login; administrators can correct it. Bookings and email flow are retained.
- No payment UI, card entry, refund, gateway, or charge processing exists.
- For a larger deployment, migrate to a real migration tool/database, use HTTPS, configured SMTP, and shared rate-limit storage. See [deployment guide](docs/installation-deployment.md).

## Upgrade from Version 5.0

1. Stop V5; **back up** `instance/cstbs.db` while no process is writing it.
2. Extract V5.1 into a new folder; copy the database to its `instance/` directory and preserve your private `.env` secret for existing sessions. Never include either in Git.
3. Install requirements and run `python -m flask --app run.py init-db` once. The idempotent V5.1 SQLite upgrade adds nullable `users.student_id` and a unique index, creates `admin_invitations`, and changes event prices to zero. Existing booking rows are preserved.
4. Run tests and verify users, admin access, bookings, reports, and emails against a staging copy before switching traffic.

## Tests & documents

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app config.py run.py
```

Guides: [User Manual](docs/user-manual.md), [Admin Manual](docs/admin-manual.md), [Installation & Deployment](docs/installation-deployment.md), [Requirements](docs/requirements.md), [Database Design](docs/database-design.md), [PlantUML](docs/uml.md), [Security](SECURITY.md), [CHANGELOG](CHANGELOG.md), [V5.1 GitHub release notes](docs/github-release-v5.1.md), and [V5.1 PDF change report](docs/version-5.1-changes.pdf).

## Deployment limitations

Single-host SQLite, five-second polling, best-effort synchronous mail, and limited compatibility migration scripts are intended for a campus demonstration or small pilot. This structure is **deployment-oriented but not production-certified**; test end-to-end locally and complete operational security review before using real student data. GitHub release tag: **`v5.1`**.
