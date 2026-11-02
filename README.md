# Campus Stadium Ticket Booking System (CSTBS) — Version 2.0

**Accounts and Events** is the second milestone of the Flask + SQLite campus stadium project. This version makes registration and login functional, adds `student`, `staff`, and `admin` roles, and lets administrators create, edit, and delete event listings.

> **Scope:** No seat selection, booking, checkout, payment, or production deployment setup exists in V2. Events and prices are illustrative unless your administrators replace them. This is a local-development project.

## Technology

- Python 3.10+, Flask, Jinja2, SQLite
- SQLAlchemy and Flask-SQLAlchemy
- Flask-Login for sessions and `@login_required`
- Flask-WTF for validation and CSRF protection
- Werkzeug for password hashing
- python-dotenv for local secrets
- Vanilla CSS/JavaScript; no frontend framework

## Quick start (fresh installation)

```bash
# From the unpacked CSTBS-v2 directory:
python -m venv .venv
source .venv/bin/activate         # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env             # Windows PowerShell: Copy-Item .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the result into `.env` as `SECRET_KEY=<random-value>`, replacing the placeholder. Do not commit `.env`.

```bash
python -m flask --app run.py seed-events
python run.py
```

Open **http://127.0.0.1:5000**. Tables are created on first run at `instance/cstbs.db`. Running `seed-events` adds four sample events **only if the catalog is empty**. Because seeding is explicit, deleted events do not silently reappear when the server restarts.

## Create your administrator account

1. Open `/register` and register a normal account (all public registrations are `student`).
2. Stop the development server or open a second terminal with the virtual environment activated.
3. Promote your own account locally:

```bash
python -m flask --app run.py set-role you@campus.edu admin
```

4. Sign out, sign back in, then open **http://127.0.0.1:5000/admin/events**. Only admins can create, edit, or delete events.

The CLI also supports `set-role you@campus.edu staff` and `set-role you@campus.edu student`. **The browser form cannot assign elevated roles.** `staff` currently has normal account/browse access; no staff-only workflow is introduced in V2.

## Upgrading a V1 SQLite database

**Always back up your local database before upgrading.** If you previously had `CSTBS-v1/instance/cstbs.db`, copy it into `CSTBS-v2/instance/cstbs.db` *before* starting V2. Do not copy your old `.env` into Git; you can reuse its `SECRET_KEY` locally to preserve existing session compatibility.

On startup, `app/migrations.py` checks SQLite's `users` table and adds a `role` column with default `student` **only if missing**. It does not drop user or event rows or change the seat/booking schema. Existing V1 `password_hash` values, if any, are left untouched. V1's UI did not create registered accounts, so users typically register anew.

**Caution:** This is a targeted V1-to-V2 SQLite compatibility step, *not* a general migration framework. `db.create_all()` cannot handle arbitrary schema changes. Do not treat this development app as a production system.

## Routes and access

| Method / URL | Access | Purpose |
| --- | --- | --- |
| `GET /` | Public | Featured upcoming events |
| `GET /events` | Public | All events |
| `GET /events/<id>` | Public | Event details |
| `GET, POST /register` | Visitors | Create a `student` account |
| `GET, POST /login` | Visitors | Authenticate via password hash |
| `POST /logout` | Signed-in users | End session; CSRF required |
| `GET /account` | Signed-in users | Profile and role |
| `GET /admin/events` | Admin | Event management index |
| `GET, POST /admin/events/new` | Admin | Create event |
| `GET, POST /admin/events/<id>/edit` | Admin | Edit event |
| `POST /admin/events/<id>/delete` | Admin | Delete event (requires CSRF) |

Anonymous users are redirected to login from protected endpoints. Signed-in non-admins receive HTTP 403 for admin pages. Event deletion is blocked when an event has attached seats, to avoid silently removing seat/booking records.

## Authentication and security notes

- Passwords are hashed using Werkzeug (`generate_password_hash`, `check_password_hash`), not stored in plaintext.
- Email addresses are normalized to lowercase, with a database uniqueness constraint.
- Public registration always assigns the `student` role on the server.
- Forms and state-changing POST routes require CSRF tokens.
- Sign-out and event deletion use POST, not GET.
- Login's `next` redirect accepts only internal absolute paths.
- `SECRET_KEY` is required from `.env`. Never use Flask debug mode on a public server.
- No password reset, email verification, rate limiting, HTTPS reverse proxy, audit log, or production DB migration system is included in V2. Add these before internet-facing deployment.

## Automated tests

Once dependencies are installed:

```bash
python -m unittest discover -s tests -v
```

Tests cover public routes, registration and password hashing, duplicate emails, login/logout, protected/admin routes, CRUD, CSRF rejection, safe login redirects, seat-aware deletion, seeding, and SQLite V1 schema upgrade.

## Structure

```text
CSTBS-v2/
├── README.md
├── CHANGELOG.md
├── requirements.txt
├── .env.example
├── .gitignore
├── run.py
├── config.py
├── docs/
│   ├── requirements.md
│   ├── uml.md
│   ├── database-design.md
│   └── version-2-changes.pdf
├── app/
│   ├── __init__.py
│   ├── migrations.py
│   ├── models.py
│   ├── routes.py
│   ├── forms.py
│   ├── seed.py
│   ├── static/
│   │   ├── css/styles.css
│   │   ├── js/main.js
│   │   └── images/stadium.svg
│   └── templates/
│       ├── base.html
│       ├── _event_card.html
│       ├── index.html
│       ├── events.html
│       ├── event_detail.html
│       ├── login.html
│       ├── register.html
│       ├── account.html
│       └── admin/
│           ├── events.html
│           └── event_form.html
├── tests/
│   └── test_app.py
└── instance/
    └── .gitkeep
```

## GitHub release

Suggested tag: **`v2.0`**. See `CHANGELOG.md` and the included `CSTBS-v2-Changes.pdf` (provided separately) for the version summary.

```bash
git add .
git commit -m "feat: add CSTBS v2.0 accounts and admin event management"
git tag -a v2.0 -m "CSTBS v2.0 - Accounts and Events"
git push origin main
git push origin v2.0
```

Replace `main` if your repository uses a different default branch. Only tag the release after running the app and tests locally.
