# CSTBS v3.0 — Seat Reservations

**Campus Stadium Ticket Booking System (CSTBS)** is a Flask + SQLite web app for discovering campus events, authenticating campus users, and reserving numbered event seats. Version 3 extends the V2 **Accounts and Events** milestone; it keeps student/staff/admin roles and administrator-only event CRUD.

> **Development project:** V3 implements real seat reservations but **does not process payments**, issue QR tickets, or provide production-ready operations. Price is informational, captured on each booking record. The availability feed polls every 5 seconds (near-real-time); only the database decides which reservation wins.

## Stack

Python 3.10+, Flask, Flask-SQLAlchemy/SQLAlchemy, SQLite, Jinja2, Flask-WTF, Flask-Login, Werkzeug, python-dotenv, and vanilla HTML/CSS/JavaScript. No frontend framework or third-party booking service.

## Quick start

```bash
# In the extracted CSTBS-v3 directory
python -m venv .venv
source .venv/bin/activate               # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env                    # Windows: Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the random value in `.env` as `SECRET_KEY=<your-generated-value>` replacing the example placeholder. Never push `.env` to GitHub. Start with:

```bash
python -m flask --app run.py seed-events
python run.py
```

Open **http://127.0.0.1:5000** and register a student, browse events, choose seats, review your selection, and confirm. The app creates `instance/cstbs.db` on startup and seeds four example events with 60 seats each. `seed-events` is idempotent when the event catalog is not empty.

### V3 booking walkthrough

1. Register or sign in (all public registrations become `student`).
2. Open an upcoming event and select **Choose seats**.
3. Use the responsive A1–F10 seat grid; select up to **6 seats**. Grey seats are reserved.
4. Select **Review reservation** to see the full seat list and total cost.
5. Select **Confirm reservation**. All seat rows save together, or none save if availability changed.
6. Open **My bookings** to view reserved/cancelled seats and cancel your own reservation. Each seat is a separate booking record, and can be cancelled individually. Cancelled rows remain in the history; their seats become available again.

**Availability:** `/api/events/<id>/seats` returns `reserved_seat_ids`, available/total counts, and whether booking remains open. The browser refreshes every **5 seconds** and removes seats that have just become unavailable from the user's selection. These are not temporary holds; a conflict is still possible between refreshes. The server rechecks selection on review and confirmation. A SQLite **partial unique index** on `bookings.seat_id` where `status='reserved'` prevents double-booking at commit time, including racing requests. The web UI handles conflicts by returning the user to the seat map with a message.

## Keep V2 admin accounts & events

Registration, login, logout, role handling, the `/account` page, and public event catalog all continue to work. Only `admin` users can create/edit/delete events. New admin-created events automatically receive a 60-seat inventory. Admin event deletion is allowed for events without **any** booking history, removing their unused seats; it is refused for events with reserved **or cancelled** booking records to preserve history. Staff have regular user booking access, but no admin privileges.

Promote a trusted account **locally** (after registering it):

```bash
python -m flask --app run.py set-role you@campus.edu admin
```

Sign out and back in; open `/admin/events`. The CLI also accepts `staff` and `student`.

## Migrating an existing V2 database

**Back up the entire previous database before upgrading**, and stop the old app first.

1. Copy `CSTBS-v2/instance/cstbs.db` into `CSTBS-v3/instance/cstbs.db` before launching V3 (only if preserving previous local data).
2. Keep a strong local `.env` secret; retaining the V2 `SECRET_KEY` preserves existing session cookies while they are valid.
3. Start the app. The targeted SQLite compatibility code in `app/migrations.py` adds `price_at_booking` to preexisting booking tables and creates the **unique index on active bookings**. If there were old bookings, their initial price snapshot is filled from the current event price. V2 events **with no seats** are automatically assigned 60 labelled seats. Events that already have any seat records are left unchanged.
4. Do **not** manually delete or overwrite the old SQLite database; do **not** attempt this migration without a backup.

If duplicate active bookings already exist for one seat, startup aborts with a helpful error instead of deleting data. This is a narrow local migration, not a general migration framework: use a real migration system for production and stage your upgrades.

## Routes

| Method + path | Access | Purpose |
| --- | --- | --- |
| `GET /`, `GET /events`, `GET /events/<id>` | Public | Event catalog and detail |
| `GET/POST /register`, `GET/POST /login` | Visitor | Accounts |
| `POST /logout`, `GET /account` | Logged in | Session & profile |
| `GET /admin/events`, `GET/POST /admin/events/new` | Admin | Event management |
| `GET/POST /admin/events/<id>/edit`, `POST /admin/events/<id>/delete` | Admin | Edit/delete event |
| `GET /events/<id>/seats` | Logged in | Interactive seat map |
| `GET /api/events/<id>/seats` | Public | Fresh occupancy JSON |
| `POST /events/<id>/booking/review` | Logged in | Validate and display confirmation |
| `POST /events/<id>/booking/confirm` | Logged in | Save selection atomically |
| `GET /bookings` | Logged in | Own booking history |
| `POST /bookings/<id>/cancel` | Owner | Cancel own seat; preserve history |

All state-changing POST endpoints require **CSRF tokens**. Anonymous users are redirected to login, and non-admin users get HTTP 403 on admin URLs. Cancellation requests for another user's booking return HTTP 404. API seat counts are public but reveal no user identities. `booking/confirm` requires a valid reviewed selection in the user's signed session.

## Tests

```bash
python -m unittest discover -s tests -v
```

Coverage includes V2 account/admin behavior and V3 booking flow, CSRF, seat limits, cross-event IDs, history, cancellation, double-booking database constraint, stale review conflicts, and V2 schema upgrade. You should also check narrow-screen horizontal seat scrolling and native keyboard button navigation in a browser.

## Design documents

- [Requirements analysis](docs/requirements.md)
- [PlantUML diagrams](docs/uml.md)
- [Database design and upgrade notes](docs/database-design.md)
- [Version history](CHANGELOG.md)
- [GitHub release text](docs/github-release-v3.0.md)
- [V3 PDF change report](docs/version-3-changes.pdf)

## Limitations / production considerations

The system has no checkout, payment gateways, ticket scanning, refunds, seat holds, email notifications, audit UI, account recovery, rate limiting, or distributed database. It uses an SQLite database suitable for development, not a high-volume stadium sale. `app.run(debug=True)` is **local-development only**; use HTTPS, a WSGI server, secure cookies, and proper migration tooling before internet deployment. Event time strings use **campus-local naive datetimes** as in V2; adopt explicit timezones before multi-campus use. An admin changing a future event's price does not rewrite historical booking price snapshots. Confirmation saves per-seat bookings, not a single group-order entity.
