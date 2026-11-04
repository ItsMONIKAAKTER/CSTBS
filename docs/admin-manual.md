# CSTBS v5.0 — Administrator Manual

**Audience:** trusted campus administrators. All `/admin` routes require an authenticated `admin` account. A `staff` user can reserve seats but does not administer the system.

## 1. Obtain administrator access

Register your account through the website, then ask a trusted operator with terminal access to run:

```bash
python -m flask --app run.py set-role admin@campus.edu admin
```

Replace the email with the registered address. Sign out and sign back in, then open **Admin dashboard**. Never give admin privileges to untrusted accounts. The UI prevents an admin from changing their own role and prevents removing the final admin through the web panel.

## 2. Dashboard (`/admin/`)

The dashboard shows total registered users, events, active reservations and blocked seats, plus recent activity. It links to Events, Users, Bookings and **Reports**. Figures are snapshots; refresh to update.

## 3. Manage events (`/admin/events`)

- **Create:** enter event title, category, description, venue, future campus-local start time and USD price. New events receive 60 default seats in the `Main` section.
- **Edit:** update valid event details. Historical booking prices are stored separately at booking time; editing the current event price does not rewrite existing booking price snapshots.
- **Delete:** delete only events without any booking history. Events with even cancelled reservations are protected from deletion so historical data remains intact.

Double-check event times before publishing; current dates are stored as campus-local naive datetimes, so one consistent timezone must be documented for your venue.

## 4. Manage seats and sections

Open **Events & seats → Manage seats** for the desired event.

- **Block / unblock:** toggle an available seat. Blocking a seat with an active reservation is prohibited by both route checks and SQLite triggers.
- **Add a section:** use a distinct 2–30 character name, 1–20 rows and 1–30 seats per row. The app creates numbered seats.
- **Rename:** change a section label without reassigning seat IDs or historical bookings.
- **Delete a section:** permitted only if no seat in that section has ever been booked.

Blocking changes public availability immediately on the next poll (within about five seconds). Do not use the seat-block feature as a temporary user seat hold.

## 5. Manage users (`/admin/users`)

Set another user's role to **student**, **staff** or **admin**. Only the admin role grants admin-panel permissions. Check email identity before promotion; role editing is a security-sensitive action. Admins cannot edit their own role in the browser.

## 6. Manage bookings (`/admin/bookings`)

Use the status and event dropdowns to filter reservations, 25 entries per page. Click **Cancel** to revoke an active booking; the record stays in history, the seat becomes available, and the owner receives a cancellation notification or console preview. Review the owner and seat before cancelling; there is no undo operation.

## 7. Create PDF and CSV reports (`/admin/reports/`)

**Booking report:** choose status and optionally one event, then **Download CSV** or **Download PDF**. Data includes owner names and email addresses, seat labels, created-at timestamps, statuses and informational prices. **Cancelled** records remain visible.

**Event report:** export events and seating counts to PDF or CSV. `Available = Total - Reserved - Blocked`. Note that the export is a current data snapshot; counts may change immediately after download.

| Format | Best use | Limit |
| --- | --- | --- |
| PDF | Administrative meeting, readable landscape tables | 2,000 rows |
| CSV | Spreadsheet pivot tables, data analysis | 10,000 rows |

Exports are downloaded as attachments with no-cache response headers. **Treat them as confidential records** and share only with personnel authorized to access reservation/identity data. User-provided spreadsheet-like formulas are escaped in CSV. If an export is too large, narrow booking filters; for larger systems, implement an audited asynchronous reporting service.

## 8. Email operations

`MAIL_BACKEND=console` writes notification previews to restricted server logs. `MAIL_BACKEND=smtp` sends via Flask-Mail to the configured SMTP service. Emails are sent after a database commit; delivery failures do not undo bookings. This version does not retry email or maintain an outbox. Test confirmation/cancellation with Ethereal before connecting a real provider. Do not store real recipient data in exposed demo logs.

## 9. Demo day checklist

1. Run `seed-events` once; optionally configure `DEMO_SEED_PASSWORD` and `seed-demo` in development mode only.
2. Open Home and Events and test responsive navigation.
3. Sign in as demo student; book/cancel a free seat; observe console email previews.
4. Sign in as demo admin; show KPIs, seat blocking and user role editor.
5. Filter bookings, export both PDF/CSV formats and inspect report metadata.
6. Explain that the prototype does **not** charge cards or issue tickets.

## 10. Operational checklist

Back up SQLite before updating versions; retain encrypted backups and test restore. Monitor 403, 429 and exception logs. Review permissions and admin membership periodically. Configure a stable secret, HTTPS, trusted hosts, SMTP credentials and shared rate-limit store before deployment. Consult [Installation & Deployment](installation-deployment.md) and [SECURITY.md](../SECURITY.md).
