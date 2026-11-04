# Installation and Deployment Guide

The root `README.md` is the authoritative project overview, architecture diagram and setup guide.

## Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run.py init-db
.\.venv\Scripts\python.exe -m flask --app run.py seed-events
.\.venv\Scripts\python.exe run.py
```

If Python 3.12 is not installed, substitute an available supported 3.10–3.12 runtime and verify compatible dependency wheels. Run tests with `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.

## Backups and deployment

- Never commit `.env`, `instance/`, generated keys, user data, or SQLite files.
- Keep the original `SECRET_KEY` and `TICKET_SIGNING_KEY` across deployments. Changing the signing key invalidates existing QR codes.
- Before upgrading, stop the server and take an independent copy of the database and secrets. Run `backup-db` and verify restorability.
- Built-in schema compatibility updates preserve old data; production upgrades should be rehearsed on a copy of the database. Do not delete migration code.
- A GitHub push runs tests only; it never deploys or changes the live database automatically. Require successful checks before merging.
- Public deployments require HTTPS for camera access, persistent storage, a WSGI server, secure session cookies, trusted host configuration, shared rate-limit storage, SMTP and institutional security/privacy review.
- SQLite is intended for campus demos and low-concurrency workflows; for high concurrency use a properly migrated production database.
