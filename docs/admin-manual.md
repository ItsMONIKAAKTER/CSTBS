# Administrator Manual — CSTBS v5.2

## First administrator: zero Notepad or code editing

1. Open PowerShell inside the project, activate `.venv`, and run `python run.py`.
2. If no administrator exists, the server prompts for **administrator email** and **full name**; answer in PowerShell. This creates the admin account in SQLite with a securely random unusable password.
3. Copy the key printed under `CSTBS ADMIN LOGIN KEY` in that terminal.
4. Visit **http://127.0.0.1:5000/admin/login**, enter the same email and the key, then **Sign in to dashboard**.
5. The key expires after **20 minutes** and is consumed at successful login. Your authenticated session continues independently of key expiry.

**No admin registration page and no need to paste a key into Notepad, `.env`, PyCharm or SQLite.**

## Login again / expired or lost key

From a **second PowerShell window** in this folder (with `.venv` active):

```powershell
python -m flask --app run.py admin-key admin@university.edu
```

The new key is printed immediately. Copy it into `/admin/login`. Issuing a new key revokes older unused keys for the same account. If no admin was ever provisioned, use `python -m flask --app run.py admin-setup`, which asks for the first email/name.

If multiple admin users exist, starting `python run.py` prompts which admin email should receive a new key. Admins are **never** authenticated solely by knowing an arbitrary email; keys are tied to an existing admin record.

## Add another administrator without admin registration

1. New person registers as a student (requires a Student ID) or uses an already-existing account.
2. While signed in as admin, open **Admin Dashboard → Users** and change that account's role to **admin**. This requires an authorized admin session.
3. Click **Generate login key** on that administrator's row. The 20-minute key is shown once on a protected no-cache page; share it privately with that person. They sign in at `/admin/login` with the email on that row.
4. Existing admins can regenerate their own keys in the local PowerShell terminal at any time.

## Administration features retained

- `/admin/`: system metrics and recent booking activity.
- `/admin/events`: manage events and schedules.
- `/admin/events/<event_id>/seats`: block/unblock seats and manage seating sections.
- `/admin/users`: roles, Student IDs and one-time admin login keys.
- `/admin/bookings`: manage and cancel reservations.
- `/admin/reports/`: PDF and CSV booking/event reports.
- Booking/cancellation email notifications via console backend or configured SMTP.

The system is for **free university reservations**; no payment gateway. Access is protected by Flask-Login, CSRF, per-IP request limits and role checks. Keep key output, emails, student IDs and exported reports confidential.
