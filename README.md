# CSTBS v4.0 — Administration

**Campus Stadium Ticket Booking System (CSTBS)** is a Python 3.10+ Flask/SQLite application for public event browsing, user accounts, event seating, and seat reservations. Version **4.0** adds an administrator operations console and booking email notifications on top of the complete V3 reservation journey.

> **Development application:** Reservations do not collect payments or create tickets. Email defaults to a **console preview**, not a real mailbox delivery. SQLite and targeted local schema compatibility upgrades are not intended for high-traffic production use.

## Technology stack

Python 3.10+, Flask, Flask-SQLAlchemy, SQLAlchemy, SQLite, Flask-Login, Flask-WTF, Werkzeug password hashing, Flask-Mail, python-dotenv, Jinja2, HTML, CSS, vanilla JavaScript. No frontend frameworks.

## Quick start

```bash
cd CSTBS-v4
python -m venv .venv
source .venv/bin/activate            # PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env                 # PowerShell: Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Replace `SECRET_KEY=replace-with-a-random-secret` in `.env` with the freshly generated secret. Keep `.env` private. By default, **MAIL_BACKEND=console** prints booking email previews to the Flask application log; no SMTP server is required. Do not use real personal email addresses in demo data if you don't need them.

```bash
python -m flask --app run.py seed-events
python run.py
```

Visit **http://127.0.0.1:5000/**. New registrations have the `student` role. To assign your trusted local account as an administrator, first register through the web UI, then run:

```bash
python -m flask --app run.py set-role admin@campus.edu admin
```

Sign out, sign in again and visit **http://127.0.0.1:5000/admin/**. This local CLI command can also set `staff` and `student`; public registration can never assign itself a privileged role.

## Admin console: V4 workflows

1. **Dashboard (`/admin/`)** — four KPI cards (users, events, active bookings, blocked seats), recent booking activity, and links to management screens.
2. **Event CRUD (`/admin/events`)** — create, edit, delete events. New events automatically receive 60 seats in a default `Main` section. Events with any booking history cannot be deleted.
3. **Seat inventory (`/admin/events/<id>/seats`)** — block or unblock individual seats; create sections with 1–20 rows and 1–30 seats per row; rename sections; delete unused sections. Every section name must be unique per event (case-insensitive in the app). A reserved seat cannot be blocked; a section with *any* reserved or cancelled booking record cannot be removed.
4. **Roles (`/admin/users`)** — assign student/staff/admin roles to other accounts. An administrator cannot demote their own account through the UI, and the last administrator cannot be demoted.
5. **Bookings (`/admin/bookings`)** — paginated view of all reservation records, filtered by event or status. Admins may cancel active reservations; the owner receives a cancellation email preview or SMTP mail. Historical rows cannot be deleted through this interface.

All admin routes use Flask-Login plus an admin authorization check. Administrative changes are POST requests protected by CSRF validation. Existing V2 event routes remain valid, and V3 personal booking history still shows only the current user's entries.

## Seats, booking flow and availability

Open an upcoming event, click **Choose seats**, and select up to six unreserved, unblocked seats. The UI now groups seats by **section and row**. A four-state legend differentiates available, selected, reserved and blocked seats. The page polls `GET /api/events/<id>/seats` every five seconds; the no-cache JSON includes `reserved_seat_ids`, **`blocked_seat_ids`**, `available`, `total` and `booking_open`.

After selection: **Review → Confirm → Save**. The server checks event ownership, starting time, number of seats, blocked state and current bookings before saving. SQLite has both a partial UNIQUE index preventing two active bookings on one seat and database triggers preventing a booking on a blocked seat (and blocking a reserved seat) even when admin action and checkout race. If a conflict occurs, the entire multi-seat transaction rolls back.

My bookings (`/bookings`) lists active/cancelled reservations. Each seat is a Booking row with the saved event price. A user may cancel their **own** booking. Admins may cancel any user's booking separately; neither path erases history. Confirmation emits one email per checkout, cancellation emits one email per cancelled booking, **after successful commits**. No payment is captured and there is no refund workflow.

## Email: console (default) or Ethereal SMTP

**Console preview** (`MAIL_BACKEND=console`) uses Flask-Mail `Message` to format notifications, then writes the recipient, subject, and content to the Flask logger. This does not send a real email. The content contains names and booking details; limit log access accordingly.

**Ethereal test SMTP**: create an Ethereal test account outside the app and set the following values in `.env`:

```dotenv
MAIL_BACKEND=smtp
MAIL_SERVER=smtp.ethereal.email
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your-ethereal-user
MAIL_PASSWORD=your-ethereal-password
MAIL_DEFAULT_SENDER=CSTBS <no-reply@campus.example>
```

Messages are sent via Flask-Mail to Ethereal's test inbox for inspection; the recipient address shown in the app need not receive external mail. Do not commit test credentials. `MAIL_SUPPRESS_SEND=true` suppresses SMTP sends when testing. Notification errors are logged *after* the booking transaction commits, so SMTP outages do not lose a saved booking; no retries or delivery guarantees are implemented. Additional details: [Email development guide](docs/email-development.md).

## Upgrade an existing V3 SQLite database (preserve data)

**Stop V3 and back up its whole `instance/cstbs.db` file first.** Copy that database into `CSTBS-v4/instance/cstbs.db` *before* launching V4 (do not copy it while the previous server writes). Copy your private `.env` separately if desired; never push it to GitHub.

V4's startup compatibility upgrade adds `seats.is_blocked BOOLEAN NOT NULL DEFAULT 0` to existing V3 databases and creates SQLite triggers for blocked-seat/active-booking consistency. Existing users, events, seats and bookings are preserved. Earlier V1/V2 upgrades still run. `db.create_all()` does not perform general migrations; for production, replace these targeted scripts with proper Alembic/Flask-Migrate migration versions and review your schema and backups. **Do not overwrite the existing DB with demo data.** `seed-events` is idempotent for an already-populated catalog.

## Main routes

| Route | Access | Description |
| --- | --- | --- |
| `/`, `/events`, `/events/<id>` | Public | Event catalog |
| `/register`, `/login`, `POST /logout`, `/account` | Account-dependent | Login and profile |
| `/events/<id>/seats`, `POST /events/<id>/booking/{review,confirm}` | Logged in | Seat booking |
| `/api/events/<id>/seats` | Public | Availability JSON, no-store |
| `/bookings`, `POST /bookings/<id>/cancel` | Logged in / booking owner | History and personal cancellation |
| `/admin/` | Admin | Operations dashboard |
| `/admin/events`, `/admin/events/new`, `/admin/events/<id>/edit`, `POST /admin/events/<id>/delete` | Admin | Event CRUD |
| `/admin/events/<id>/seats`, `POST /admin/seats/<seat_id>/toggle-block` | Admin | Seat management |
| `POST /admin/events/<id>/sections/{create,rename}`, `POST /admin/events/<id>/sections/<name>/delete` | Admin | Section management |
| `/admin/users`, `POST /admin/users/<id>/role` | Admin | User role management |
| `/admin/bookings`, `POST /admin/bookings/<id>/cancel` | Admin | Booking oversight |

## Tests and documentation

Run the complete tests after installing packages:

```bash
python -m unittest discover -s tests -v
```

The V4 test module covers role protections, seat block/unblock, section lifecycle, owner notifications from admin cancellation, preventing booking on blocked seats, and upgrading an older seat table. V1–V3 test modules are retained. Also manually verify narrow viewport layouts and Ethereal delivery when configured. See [requirements](docs/requirements.md), [UML & PlantUML](docs/uml.md), [database design](docs/database-design.md), [email guide](docs/email-development.md), [change history](CHANGELOG.md), [v4.0 GitHub release notes](docs/github-release-v4.0.md), and [V4 change report](docs/version-4-changes.pdf).

## Security and limitations

Secrets and live databases are excluded by `.gitignore`. Flask-WTF protects state-changing requests against CSRF, hashed credentials are never displayed, and all admin roles are enforced on the server. Blocking rules also have SQLite transaction triggers. For an internet-facing release, add true migrations, dedicated operator accounts, auditing, rate limits, a robust task/email queue, HTTPS, secure cookies, observability and deployment configuration. This version has no payments, ticket delivery, refunds, order batching, seat holds, websocket push, or guaranteed email delivery.
