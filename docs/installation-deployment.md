# CSTBS v5.0 — Installation & Deployment Guide

## Supported environment

- Python **3.10+**, virtual environment, all packages from `requirements.txt`.
- SQLite on a **single persistent host**, with backup and limited traffic; do not put `instance/cstbs.db` on ephemeral storage.
- Gunicorn for Linux/Unix application serving behind HTTPS-enabled reverse proxy. Local `python run.py` is only a loopback development server.
- An SMTP provider for real email delivery and Redis shared rate limiting for deployment.

## 1. Local setup

```bash
unzip CSTBS-v5.zip && cd CSTBS-v5
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated secret into `.env` under `SECRET_KEY`. On Windows use `.venv\Scripts\Activate.ps1` and `Copy-Item .env.example .env`. No webpack/NPM is necessary.

```bash
python -m flask --app run.py init-db
python -m flask --app run.py seed-events
python -m unittest discover -s tests -v
python run.py
```

Browse `http://127.0.0.1:5000/`. Create a local admin as described in README.

## 2. Environment variables

| Setting | Development | Deployment |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` |
| `SECRET_KEY` | Random and private | Random 32+ chars, stable and private |
| `DATABASE_URL` | `sqlite:///cstbs.db` | Persistent SQLite path/volume; plan real migrations |
| `SESSION_COOKIE_SECURE` | `false` | `true`, HTTPS required |
| `TRUSTED_HOSTS` | Optional | **Required**: comma-separated allowed DNS names |
| `RATELIMIT_STORAGE_URI` | `memory://` | **Required**: Redis URL, e.g. `redis://127.0.0.1:6379/0` |
| `MAIL_BACKEND` | `console` or `smtp` | **Required**: `smtp` |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` | Optional test SMTP | Protected live SMTP account |
| `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_DEFAULT_SENDER` | Test settings | Configure per mail provider |
| `DEMO_SEED_PASSWORD` | Optional local demo only | **Never set/run** |

`APP_ENV=production` refuses startup without the required secret length, trusted host list, secure cookies, non-memory rate-limit backend, and non-console mail. For a Redis backend, install the relevant extra with `python -m pip install 'Flask-Limiter[redis]>=3.10,<5'` after the base requirements. Production packages must be pinned to tested exact versions in a deployment lockfile.

## 3. Example small single-host deployment (Linux)

1. Create a dedicated low-privilege OS user and a private install directory, e.g. `/srv/cstbs`.
2. Install Python 3.10+, create `.venv`, install requirements and `Flask-Limiter[redis]` extra. Run Redis as an appropriately secured service accessible only to your application.
3. Configure a private `.env`, for example:

```dotenv
APP_ENV=production
SECRET_KEY=<replace-with-long-generated-private-value>
DATABASE_URL=sqlite:////srv/cstbs/instance/cstbs.db
SESSION_COOKIE_SECURE=true
TRUSTED_HOSTS=stadium.example.edu
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
MAIL_BACKEND=smtp
MAIL_SERVER=smtp.your-provider.example
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=<private-value>
MAIL_PASSWORD=<private-value>
MAIL_DEFAULT_SENDER=CSTBS <noreply@stadium.example.edu>
```

4. Ensure the application user can write to `instance/`, but **web/static hosting cannot read the database**. Set file/dir permissions to least privilege.
5. After **making and checking backups**, run schema setup explicitly:

```bash
python -m flask --app run.py init-db
```

6. Use a single Gunicorn worker while using local SQLite. Keep request load modest and test multi-thread write contention; for substantial traffic migrate to PostgreSQL with proper migrations before using multiple workers.

```bash
gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 4 --timeout 30 'run:app'
```

7. Put Nginx/Caddy/your campus reverse proxy in front. Terminate HTTPS, set the correct hostname, forward only necessary headers, restrict proxy access, and add system service supervision and log rotation. **Do not expose Gunicorn directly**. The application uses the actual connecting peer for rate limits; it does *not* trust arbitrary `X-Forwarded-For`. If you later choose to install proxy middleware, configure exact trusted hop counts only after network verification.
8. Set TLS certificates, log-access controls, off-host encrypted backups, monitoring and vulnerability scanning. Try a full backup restoration and a test booking/cancellation before announcing availability.

### Operational caveats

- **Schema:** V1–V4 compatibility scripts and `db.create_all()` are not an Alembic migration system. In production mode the app does **not** create/upgrade tables on every web start; `flask init-db` is explicit. Review schema changes/restore procedures before upgrades.
- **Times:** Event start is stored as a naive timestamp representing a consistently chosen campus timezone; do not deploy across multiple local zones without redesigning timezone handling.
- **Email:** Notification sending is synchronous after commit and best effort. For a large installation, introduce a durable outbox and job queue.
- **Seats:** Five-second availability polling is near-real-time, not a seat hold or WebSocket push. Database constraints protect active seat uniqueness; SQLite is not suited to high-concurrency sales.
- **Data privacy:** Report downloads include names/email; use HTTPS, authorized admin distribution, retention policies, and logs with restricted permissions.
- **Security:** Current CSP allows inline **styles** because the inherited dynamic seat grid uses an inline CSS custom property. No inline script permission is granted. A future stricter CSP should eliminate dynamic inline styling.

## 4. Back up or migrate a V4 database

1. Stop all processes writing the database.
2. Use the SQLite backup API or copy `instance/cstbs.db` while it is offline. Store an encrypted off-host copy and test restore.
3. Extract V5 into its own directory. Copy the backed-up database file to `CSTBS-v5/instance/cstbs.db`, set the `DATABASE_URL` if different, and preserve the `SECRET_KEY` where ongoing sessions must remain valid.
4. Run `python -m flask --app run.py init-db` once with a reviewed backup/rollback plan. No V5 schema columns are added: reports aggregate existing V1–V4 entities.
5. Run integration tests against a **copy** of the database; validate old bookings, seating blocks and admin functions. Switch traffic only after acceptance.

## 5. Validation and release checklist

```bash
python -m unittest discover -s tests -v
python -m compileall -q app config.py run.py
```

- [ ] Home, Events and responsive seat selection work on mobile and desktop.
- [ ] Registration/login/logout, roles, CSRF and 403 tests work.
- [ ] Multi-seat checkout and owner/admin cancellation preserve booking records.
- [ ] Console/SMTP booking mail works; no credentials are logged.
- [ ] Admin PDF/CSV reports work and exported data is treated as confidential.
- [ ] Redis-backed rate limiting, trusted hosts, HTTPS/secure cookies and proxy IP behavior are confirmed.
- [ ] Databases/backups remain excluded from Git and off-host recovery was rehearsed.
- [ ] Deployment has monitoring, appropriate logging, updates, threat review and tested dependencies.

This is a **deployment-oriented reference application** rather than a certified high-traffic ticketing product. Scale-out, full transactional audit logs, password recovery, production migrations, queue-backed mail and operational compliance remain separate work.
