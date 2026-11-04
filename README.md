# CSTBS v5.0 — Final Release

**Campus Stadium Ticket Booking System** is a Python 3.10+ Flask application for campus event discovery, account management, seat reservations, and stadium administration. Version 5 adds **administrator PDF reports and CSV downloads**, strengthened request security, a demonstration data command, and complete user/admin/deployment manuals.

> **Scope:** A reservation allocates seats; no payments, QR ticket issuance, refunds, or external identity system are included. This repository has deployment-oriented structure, but SQLite, simple compatibility migrations, five-second seat polling, and best-effort mail are designed for **small, single-host installations**. Complete the deployment hardening checklist before exposing the app to real users.

## Features by role

| Feature | Visitor | Student / Staff | Admin |
| --- | :---: | :---: | :---: |
| Browse events, event details and seat availability | ✓ | ✓ | ✓ |
| Create an account / sign in | ✓ | ✓ | ✓ |
| Select, review and confirm up to 6 seats | — | ✓ | ✓ |
| Review and cancel own bookings | — | ✓ | ✓ |
| Admin dashboard and full event CRUD | — | — | ✓ |
| Manage sections, block/unblock seats | — | — | ✓ |
| Promote/demote other accounts | — | — | ✓ |
| Filter and cancel any booking | — | — | ✓ |
| Export booking/event reports (PDF or CSV) | — | — | ✓ |

The app retains Flask-Login, Werkzeug password hashing, role checks, Flask-WTF CSRF tokens, SQLite double-booking constraints, and Flask-Mail booking notifications from earlier versions.

## Technology stack

Python 3.10+, Flask 3.1, SQLAlchemy 2, Flask-SQLAlchemy, SQLite, Jinja2, Flask-Login, Flask-WTF, Flask-Mail, Flask-Limiter, ReportLab, python-dotenv, HTML, CSS and JavaScript. Gunicorn is provided for Unix WSGI deployment; no JavaScript build process is needed.

## Local installation (macOS/Linux)

```bash
unzip CSTBS-v5.zip && cd CSTBS-v5
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `.env` and replace `SECRET_KEY=replace-with-a-random-secret` with the generated key. **Never commit `.env`.** On Windows, use `.venv\Scripts\Activate.ps1` and `Copy-Item .env.example .env` instead of the two corresponding commands.

```bash
python -m flask --app run.py init-db
python -m flask --app run.py seed-events
python run.py
```

Open http://127.0.0.1:5000/. The development server listens on **localhost only**; it runs with the debugger disabled. The SQLite database is `instance/cstbs.db` by default. `seed-events` safely inserts four upcoming illustrative events **only when the event table is empty**. Each sample event starts with 60 seats.

### Demonstration dataset (optional, non-production)

For a presentation with example accounts, bookings and blocked seats, add a generated test password to your private `.env`:

```dotenv
DEMO_SEED_PASSWORD=put-your-own-12-plus-character-demo-password-here
```

Then run:

```bash
python -m flask --app run.py seed-demo
```

This creates **demo.student@campus.example**, **demo.staff@campus.example**, and **demo.admin@campus.example** with your password, plus example reserved/cancelled bookings and blocked seats. Repeated runs don't duplicate records. The command **refuses production mode**. These are strictly fictional accounts; never use the demo credentials on a public service.

### Create your own administrator

Register normally; registrations always receive the `student` role. Then, in a trusted local terminal:

```bash
python -m flask --app run.py set-role your-email@campus.edu admin
```

Sign out/in and visit `/admin/`. Administrative role assignment is never exposed to public registration.

## Version 5 reporting

The **Reports** tab on `/admin/` links to `/admin/reports/`. It offers:

- **Booking report:** filter by status (`all`, `reserved`, `cancelled`) and/or an event. Columns include booking ID, UTC creation time, event, seat, owner's name/email, status and saved price.
- **Event report:** all events with start time, venue, category, price, total seats, active reservations, blocked seats and available seats.
- **PDF:** landscape pages with repeated table headers, metadata and page numbers, generated in memory by ReportLab.
- **CSV:** UTF-8 (BOM) exports for spreadsheet editing; user-entered values that look like formulas are safely prefixed.

All export routes are **GET but admin-authorized**, set attachment and `no-store` headers, and limit output to **2,000 PDF rows** or **10,000 CSV rows**. Large reports require narrowing filters or adding a proper background report pipeline. Exports can contain personal information; distribute only through authorized channels.

## Core pages and endpoints

| Path | Access | Purpose |
| --- | --- | --- |
| `/`, `/events`, `/events/<id>` | Public | Discovery and public catalog |
| `/register`, `/login`, `POST /logout`, `/account` | Accounts | Authentication and account details |
| `/events/<id>/seats`, `POST /events/<id>/booking/{review,confirm}` | Signed-in | Seat selection and checkout |
| `/api/events/<id>/seats` | Public | Five-second polling availability JSON |
| `/bookings`, `POST /bookings/<id>/cancel` | Owner | Booking history/cancellation |
| `/admin/` | Admin | Metrics and recent bookings |
| `/admin/events...`, `/admin/events/<id>/seats` | Admin | Event CRUD, seats and sections |
| `/admin/users`, `/admin/bookings` | Admin | Roles and booking oversight |
| `/admin/reports/` | Admin | Export dashboard |
| `/admin/reports/bookings.csv`, `bookings.pdf` | Admin | Filtered booking exports |
| `/admin/reports/events.csv`, `events.pdf` | Admin | Event inventory exports |

## Booking and email behavior

Seat availability refreshes every five seconds. A confirmation **rechecks** seat ownership, blocks, availability and future event time. The SQLite partial unique index prevents two active bookings on one seat; three SQLite triggers forbid booking blocked seats or blocking seats with active bookings. Multi-seat checkout commits together or rolls back together. Cancellation keeps historical booking records and frees the seat.

`MAIL_BACKEND=console` prints booking confirmation/cancellation previews in restricted local logs; `MAIL_BACKEND=smtp` can use Ethereal or a configured SMTP service. Notifications happen *after* the database commits, so failures are logged and do not reverse bookings. There is no durable outbox or retry queue. See [Email development](docs/email-development.md).

## Security improvements in v5

- Global CSRF checks on POST forms, including logout, checkout, admin mutations and cancellation; tokens expire after 1 hour.
- Flask-Limiter: 300 requests/hour by IP by default, 5 login or registration POSTs/minute (25/hour), 12 confirmations/minute and 60 availability GETs/minute.
- Controlled event price, password length (12–128 chars), section dimensions and safe query filter values.
- `MAX_CONTENT_LENGTH` 128 KiB; security headers for CSP, no framing, referrers, permissions, and MIME-sniffing prevention.
- `SESSION_COOKIE_HTTPONLY` and `SameSite=Lax`; HTTPS-only cookies, HSTS and trusted host enforcement for `APP_ENV=production`.
- SQLite foreign-key enforcement; security-sensitive exports remain private and are formula-safe for CSV.
- Default dev limiter uses `memory://` **only for local development**. Production requires shared storage (Redis) and proper reverse-proxy configuration. Never blindly trust `X-Forwarded-For`.

See [SECURITY.md](SECURITY.md) and [Installation & deployment](docs/installation-deployment.md).

## Upgrade from Version 4 (preserve bookings)

1. Stop V4 and **make a SQLite backup** before copying data.
2. Extract V5 to a new folder. Copy `CSTBS-v4/instance/cstbs.db` to `CSTBS-v5/instance/cstbs.db` while both servers are stopped. Copy any locally configured secrets into the new private `.env`.
3. Install V5 requirements, configure a strong key, and run `python -m flask --app run.py init-db` once. Existing V1–V4 compatibility scripts are idempotent for their documented schema changes. No V5 DB columns are required for reports.
4. Run the full tests, check login, existing booking history, admin workflows and CSV/PDF report downloads **before** switching your users.

**Important:** The bundled scripts are specific SQLite compatibility steps, not full data migrations. For a larger or live installation, use a reviewed Alembic-based migration process, rehearsal, rollback and backup plan. Never copy a database while it is being actively written.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q app config.py run.py
```

V1–V4 integration tests remain, and `tests/test_reports.py` adds admin authorization, report content, CSV-injection escaping, filtering, PDF generation and security-header checks. Locally verify SMTP, mobile viewports, backup/restore, concurrency and reverse-proxy behavior separately.

## Documentation and release

- [User Manual](docs/user-manual.md)
- [Admin Manual](docs/admin-manual.md)
- [Installation & Deployment Guide](docs/installation-deployment.md)
- [Requirements & acceptance criteria](docs/requirements.md)
- [UML / PlantUML](docs/uml.md)
- [Database Design](docs/database-design.md)
- [Security guidance](SECURITY.md)
- [Changelog (v1–v5)](CHANGELOG.md)
- [GitHub v5.0 release description](docs/github-release-v5.0.md)
- [Version 5 PDF change report](docs/version-5-changes.pdf)

GitHub release tag: **`v5.0`**. No secrets, local database, generated cache or virtual environments are part of the ZIP. Pin exact dependency versions and complete security testing prior to a public deployment.
