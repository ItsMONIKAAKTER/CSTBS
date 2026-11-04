# CSTBS v5.3 — Installation, Migration and Deployment Guide

## Development on Windows 10/11

Prerequisites: Python 3.10+, PowerShell, local disk access. No XAMPP or separate SQLite server is needed.

```powershell
cd path\to\CSTBS-v5.3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m flask --app run.py init-db
python -m flask --app run.py seed-events
python run.py
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process Bypass` for that PowerShell session only. On initial startup the local terminal prompts for admin email/name and prints a 20-minute activation key; open `/admin/activate`, set a password, then use `/admin/login` thereafter. **No key needs to be pasted into any file.** The SQLite database is located at `instance/cstbs.db` with Flask's default SQLite config.

`GET /health` provides a readiness check. `python -m unittest discover -s tests -v` runs the test suite. JS may be checked with `node --check app/static/js/main.js` and `scanner.js` if Node is installed.

## Migrating V5.2 without losing data

1. Stop both the old and new servers. Preserve a safe, private copy of `instance/cstbs.db` plus your existing `SECRET_KEY` and private `instance/.local_secret_key` if used. Copy the database to the V5.3 folder with the same secret.
2. Run `python -m flask --app run.py init-db` in V5.3. On an old on-disk SQLite schema, the application checks for the missing V5.3 admin-password column and uses SQLite's online backup API to create an **integrity-checked snapshot** in `instance/backups/cstbs-preupgrade-*.sqlite3` before changing the DB. If the backup fails, migration aborts.
3. V5.3 adds `User.password_ready`, `User.auth_version`, `Event.booking_enabled`, `Event.checkin_enabled`, and the `Ticket` table with a partial unique index for live tickets by attendee/event. A cancellation trigger invalidates QR tickets. Existing user/event/seat/booking IDs are retained.
4. Admins preserved from V5.2 are marked as **not activated** once, since V5.2 used key-only logins. Use a 20-minute activation key to create a reusable password. `admin-key EMAIL` issues a key only when password activation is pending; `admin-reset EMAIL` is an explicit recovery action that invalidates active sessions.
5. Legacy bookings are backfilled one ticket each without deleting any record. Only the first active seat for the student's event can be assigned to their own identity; extra seats (or seats owned by users with no Student ID) remain `unassigned`. The administrator verifies another student's name/ID and assigns it through the admin booking page before issuing a usable QR.
6. Re-running `init-db` does **not** rotate QR nonces, reassign attendees, reset admin passwords or delete bookings. Test ticket scanning and capacity counts before admitting students.

**Rollback:** Stop the new server, keep evidence of the failure, restore the pre-upgrade backup to the original database path and re-run V5.2 with its original secrets. New V5.3 tickets/check-ins after a backup are not in that snapshot; reconcile operations before restoring in a live deployment.

## GitHub-safe releases

- `.gitignore` excludes `.env`, `instance/*` (except `.gitkeep`), `.venv/`, caches, IDE settings and local DB/secret files. Never commit QR tokens, student exports, SQL backups or private keys.
- `.github/workflows/tests.yml` runs application integration tests, Python compilation and JS checks on every push/PR. It **does not deploy** and has read-only repository permissions.
- Enable branch protection on `main`: require passing CI and review before merging. Work on a feature branch; tag releases after tests pass.
- Git pushes do **not** change the running server or its database unless you separately configure deployment. Never add an automatic deployment step without explicit approval, migration backup and rollback plans.
- Deploy in this order: maintain a live backup, freeze writes, apply reviewed migration, run tests/health checks, deploy release, reopen writes. Avoid overwriting persistent DB files with ZIP contents. Store secrets in hosting secrets management, not Git.

```bash
git checkout -b feat/v5.3-stadium-entry
# make/verify changes
git add .
git commit -m "feat: add CSTBS v5.3 group tickets and QR check-in"
git push -u origin feat/v5.3-stadium-entry
# merge only after CI passes
# then tag the accepted main commit
git tag -a v5.3 -m "CSTBS v5.3 - Smart Stadium Ticketing"
git push origin v5.3
```

## Production considerations (not automatically satisfied)

This project keeps the required Flask + SQLAlchemy + SQLite stack. SQLite is appropriate for demonstrations and controlled low-volume deployments, but simultaneous scanners and a campus-wide ticket surge need load-testing and, ideally, a centrally managed transactional database. The built-in compatibility migration is **SQLite-specific**; PostgreSQL and other DBs require a separate reviewed Alembic migration plan before adopting them. Do not switch databases by changing a URL alone.

Use a real HTTPS domain; set `APP_ENV=production`, persistent `SECRET_KEY` and **persistent independent `TICKET_SIGNING_KEY`** (both 32+ random characters), `SESSION_COOKIE_SECURE=true`, `TRUSTED_HOSTS`, a shared `RATELIMIT_STORAGE_URI` such as Redis, and approved SMTP (`MAIL_BACKEND=smtp`). Use managed WSGI hosting (Gunicorn on Linux), dedicated runtime user, reverse proxy, persistent private DB volume, daily verified off-site backups, restricted logs, time synchronization, device/physical identity checks and documented recovery procedures. The app refuses production startup without key production settings. Ensure reverse proxies pass the correct trusted Host/HTTPS headers; never enable unrestricted `ProxyFix` without validating proxy count.

For local development, `instance/.local_secret_key` provides a durable secret automatically. **Never use it as a production substitute and never rotate the QR signing key without planning existing ticket invalidation.** Scanners require HTTPS/localhost camera permission and browser support; always provide the native-phone-camera fallback. Consider institutional SSO/MFA and student privacy review before real use.

## Testing and backups

```powershell
python -m unittest discover -s tests -v
python -m flask --app run.py backup-db
python -m flask --app run.py init-db
python run.py
```

Test these workflows manually on staging: first admin activation; password sign-in; student ID registration; one-ticket-per-event and group booking; QR tamper check; cancelled/used QR rejection; simultaneous scanner duplicate check-in; blocked seats; report access control; migration of a V5.2 DB with multiple bookings. If any fail, do not deploy publicly.
