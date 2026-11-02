# Campus Stadium Ticket Booking System (CSTBS) — Version 1

A responsive **Flask + SQLite** campus stadium event-discovery prototype. V1 includes an event catalog, event detail pages, and UI-only login/registration forms, plus the initial schema for users, events, seats, and bookings.

> **Prototype only:** No real accounts, authentication, ticket purchases, seat reservations, or payments are implemented. All event data and prices are illustrative. Do not enter real passwords into the demo forms.

## Technology

- Python 3.10+
- Flask / Jinja2
- SQLAlchemy + Flask-SQLAlchemy
- SQLite
- Flask-WTF
- python-dotenv
- Plain CSS and JavaScript (no frontend framework)

## Quick start

Open a terminal in the `CSTBS-v1` folder:

```bash
# 1. Create and activate a virtual environment.
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

# 2. Install dependencies.
python -m pip install -r requirements.txt

# 3. Create your local environment file.
cp .env.example .env
# On Windows PowerShell: Copy-Item .env.example .env

# 4. Generate a strong development secret and paste it into .env
# to replace "replace-with-a-random-secret".
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Run the local development server.
python run.py
```

Visit **http://127.0.0.1:5000/**. The database is created at `instance/cstbs.db` on first startup. Four demo events are added to an empty catalog. The `.env` file and generated database are intentionally excluded from Git.

**Important:** `python run.py` enables Flask's debug mode for local development only. Do not expose this development server publicly.

## Pages

| URL | V1 behavior |
| --- | --- |
| `/` | Hero and featured upcoming events |
| `/events` | Complete sample event catalog |
| `/events/<id>` | Event detail, venue, date/time, illustrative price |
| `/login` | CSRF-protected form preview; never authenticates |
| `/register` | CSRF-protected form preview; never creates accounts |

The login/register forms validate sample input and display an informational message; submissions are **not persisted**.

## Project layout

```text
CSTBS-v1/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── run.py
├── config.py
├── docs/
│   ├── requirements.md
│   ├── uml.md
│   └── database-design.md
├── app/
│   ├── __init__.py
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
│       └── register.html
└── instance/
    └── .gitkeep
```

## Documentation

- [`docs/requirements.md`](docs/requirements.md) — scope, requirements, acceptance checklist.
- [`docs/uml.md`](docs/uml.md) — use case, class, component, and sequence diagrams with PlantUML source.
- [`docs/database-design.md`](docs/database-design.md) — tables, constraints, relationships, and V1 limitations.

## Development notes

- To regenerate demonstration data, **stop the server**, then delete `instance/cstbs.db` (this discards local data) and restart.
- `db.create_all()` is a local-development shortcut, **not** a migration solution.
- Event times are displayed as campus-local, without time-zone conversion in V1.
- No database administrative or booking routes are exposed.

## Create a ZIP archive

From the directory *containing* `CSTBS-v1`:

```bash
# macOS / Linux (omit local .env, .venv, database, caches):
zip -r CSTBS-v1.zip CSTBS-v1 -x '*/.env' '*/.venv/*' '*/__pycache__/*' '*/instance/*.db'
```

Or right-click the `CSTBS-v1` folder and select **Compress / Send to ZIP**. Exclude `.env`, `.venv`, and SQLite database files when sharing.
