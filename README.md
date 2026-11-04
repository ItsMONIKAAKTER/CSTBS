# CSTBS v5.2 — Simplified Administrator Login

Campus Stadium Ticket Booking System (CSTBS) is a Flask/SQLite university event booking website, with **free reservations**, student ID registration, protected administrative tools, and PDF/CSV reporting. Student-facing prices, where shown, are **¥0.00 RMB/CNY**. **No payment gateway.**

## V5.2: no admin registration or Notepad key editing

- **Students:** Register at `/register` with full name, university email, mandatory **unique Student ID (6–20 letters/digits)** and password. Then log in using email/password.
- **Administrators:** There is **no admin registration form**. They log in at `/admin/login` with their **existing admin email** and a **single-use 20-minute key**.
- **First-run setup:** `python run.py` on a local interactive Windows PowerShell terminal asks for the first admin email/name **only if none exists**, creates the admin account and prints the login key in that terminal. No code, `.env`, Notepad or SQLite edits are needed.
- **Later logins:** Starting `python run.py` generates a fresh key for the only administrator, or asks which existing administrator needs a key if there are multiple. Keys are bound to one admin email; creating a new key invalidates older unused keys for that account.
- **If a key expires:** Open another PowerShell in the same project folder and run `python -m flask --app run.py admin-key admin@university.edu`. Copy the newly printed key into the website. Nothing goes into a configuration file.
- **Additional administrators:** An existing admin can promote a trusted user under `/admin/users`, then click **Generate login key** for that account. The key appears once on a no-cache page. A logged-out admin can also generate their own key in the local terminal.
- **Existing V5.1 administrators:** Their accounts/roles are preserved. Use their existing email with a newly generated one-time key. The old registration keys are invalidated by the schema update; password-based admin login is disabled in v5.2.
- **Secret key for local development:** If `SECRET_KEY` is not configured, CSTBS automatically creates a stable, private `instance/.local_secret_key` (ignored by Git) so a fresh installation requires **no `.env` editing at all**. Production **requires** a configured secure `SECRET_KEY`.

## Windows PowerShell - first run

1. Extract `CSTBS-v5.2.zip`. Open PowerShell inside `CSTBS-v5.2`.
2. Install Python 3.10+, then:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app run.py init-db
python -m flask --app run.py seed-events
python run.py
```

PowerShell may block activation; run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in that PowerShell session if needed. A `.env` file is **optional** for local demo defaults. You do not need Notepad for login keys or application secrets in development.

When prompted, enter the first administrator email and name. Copy the 20-minute key from PowerShell and open **http://127.0.0.1:5000/admin/login**. Enter **the same email** and the key. You will go straight to the admin dashboard after login. **The key's expiry does not end an established login session.**

To regenerate (without restarting the web server):

```powershell
# Run in a second PowerShell window in CSTBS-v5.2, with .venv activated
python -m flask --app run.py admin-key admin@university.edu
```

For a noninteractive terminal or initial setup that was skipped:

```powershell
python -m flask --app run.py admin-setup
```

The first command prompts for an email and name and prints a new key. After a valid admin account exists, use `admin-key EMAIL` instead.

## Features retained from V1-V5.1

| Feature | Access |
|---|---|
| Public home, event list and details | Everyone |
| Student registration with Student ID, login, account profile | Students |
| Responsive seat map, reservation (1–6 seats), live availability polling | Signed-in users |
| Cancel own booking; personal booking history | Signed-in users |
| Admin dashboard; event CRUD; sections, blocking seats | Admin only |
| Manage users and roles; cancel bookings | Admin only |
| Booking/event PDF and CSV exports | Admin only |
| Booking confirmation and cancellation email preview / SMTP | Configured backend |
| Free admission, RMB/CNY display | Entire app |

## Database upgrades and backups

Before replacing an earlier V5.x installation, **stop the old server and back up the original `instance/cstbs.db` and its secret**. Copy the DB into this V5.2 folder, preserve your old `.env` `SECRET_KEY` if set (otherwise session cookies and fingerprints change), and run `python -m flask --app run.py init-db`. This idempotent SQLite update adds an administrator-target field to the previous key table and revokes unbound V5.1 registration keys; it does **not** remove accounts, bookings or events. All older admin accounts can request fresh login keys.

**Important:** New users, student IDs and reserved seats are kept. Do not commit real databases, `.env`, secret files or terminal keys to GitHub.

## Security / testing

Keys use `secrets`, HMAC-SHA256 fingerprints, per-admin binding, database-backed expiry, atomic one-time consumption, limited issuance, CSRF checks and login rate limits. No admin account can be created by entering an arbitrary email and key on a public page. Terminal access is privileged: keep your computer and console private. The admin password route cannot bypass the key. For production use HTTPS, trusted hosts, a strong explicit secret, Redis shared rate limits, approved SMTP, robust backups and reviewed migrations. See `SECURITY.md` and `docs/installation-deployment.md`.

Run tests after installing dependencies:

```powershell
python -m unittest discover -s tests -v
```

## Documentation

- `docs/user-manual.md`: student browsing and seat reservations.
- `docs/admin-manual.md`: first-run admin key login and web management.
- `docs/installation-deployment.md`: Windows setup, migration and production guidance.
- `docs/uml.md`, `docs/database-design.md`: models and access flows.
- `CHANGELOG.md`: all releases, including V5.2.
- `docs/github-release-v5.2.md`: ready-to-copy GitHub release notes.

**Release tag:** `v5.2` — *CSTBS v5.2: Simplified Administrator Login*.
