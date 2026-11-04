# Installation & Deployment — CSTBS v5.2

## Quick start: Windows 10/11

Use Python 3.10+ and PowerShell. Extract `CSTBS-v5.2.zip` and open PowerShell **inside** its top-level folder.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app run.py init-db
python -m flask --app run.py seed-events
python run.py
```

For activation policy errors run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and retry activation. The local app automatically saves a secret to `instance/.local_secret_key` (Git-ignored). No `.env` or Notepad editing is needed for the local default. The *administrator key* is generated and stored in hashed form by the app; **never paste it into any file**.

On first interactive startup when no admin exists, type your admin email and optional name when prompted. Copy the 20-minute key printed in PowerShell. Open `http://127.0.0.1:5000/admin/login` and use the **same admin email + key**. For expired keys open a second PowerShell and run:

```powershell
python -m flask --app run.py admin-key admin@university.edu
```

If setup was skipped because the server was started without an interactive terminal, run `python -m flask --app run.py admin-setup` first. No public admin registration or manual database insertion is required. The current login session is not affected by key expiration.

## Upgrade from V5.1

1. Stop both applications and **back up** `instance/cstbs.db`, `.env`, and any private secret file. Copy your existing database to V5.2 `instance/`; maintain the same `SECRET_KEY` as before if using `.env`.
2. `flask init-db` applies an idempotent migration: `admin_invitations.target_user_id` and its index, invalidates any unused V5.1 registration invitations, and retains the existing users, roles, events, seats and booking history.
3. Run `python run.py`. If at least one admin exists, the terminal prints a new targeted login key (with only one admin) or prompts you to select an existing admin email (multiple admins).
4. Use `/admin/login`. Former admin email/password login is intentionally replaced by one-time key login. Students still use email/password.

## Production safety

Local terminal provisioning is disabled on production WSGI app imports; only deliberate trusted-operator CLI commands can create keys. For a production host, provision the first admin from a **restricted operator terminal** using `flask admin-setup`, and generate login keys using `flask admin-key EMAIL`. The process user / console must be protected: whoever controls the server terminal has privileged credential-issuance power. Terminal-only login keys are inconvenient for a public multi-admin deployment; university SSO with MFA is recommended for real campus use.

Production requires explicit `APP_ENV=production`, a strong stable private `SECRET_KEY`, HTTPS-only cookies, `TRUSTED_HOSTS`, Redis shared rate limits and configured SMTP. The app refuses startup without these. Use a persistent data volume, backups, tested migrations, proxy hardening and audit logs for wider deployment. SQLite supports a small controlled deployment, not high-concurrency ticket releases.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Git hygiene

Do not commit `.env`, `instance/.local_secret_key`, SQLite databases, logs, plaintext access keys, student IDs or private reports. See `SECURITY.md`.
