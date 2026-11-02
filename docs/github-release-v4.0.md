# CSTBS v4.0 — Administration

## Overview

Campus Stadium Ticket Booking System Version 4.0 extends the authenticated event catalog and seat reservation features from v3.0 with a role-protected administration console, seating inventory controls, account-role management, cross-user reservation oversight, and booking email notifications.

## What's new

- **Admin Dashboard:** Overview of total users, events, active bookings and blocked seats; recent reservation activity and management navigation.
- **Event Administration:** Full event creation, editing and safe deletion, retained and surfaced in the admin panel.
- **Seat and Section Management:** Block/unblock seats, create seating sections, rename sections and delete unused sections while preserving booking history.
- **User Role Management:** Promote or demote users between student, staff and admin, with safeguards against self-demotion and removing the final administrator.
- **Booking Oversight:** Browse, filter and paginate all users' booking records; administratively cancel active bookings.
- **Email Notifications:** Flask-Mail booking confirmation and cancellation messages, with console preview mode by default and optional Ethereal SMTP for development.
- **Database Safety:** Non-destructive seat-block flag migration; SQLite triggers prevent reserving blocked seats or blocking reserved seats, alongside the existing double-booking constraint.
- **Updated UI and Documentation:** Responsive admin screens and sectioned seat map; refreshed README, CHANGELOG, requirements, UML, database design, email guide and integration tests.

## Compatibility

Preserves V1–V3 public browsing, Flask-Login accounts, roles, event CRUD, multi-seat reservations, personal booking history and own-booking cancellation. Existing V3 SQLite data can be migrated in place after making a backup.

## Technical stack

Python 3.10+, Flask, Flask-Login, Flask-Mail, Flask-WTF, Flask-SQLAlchemy, SQLAlchemy, SQLite, Werkzeug, Jinja2, python-dotenv, HTML/CSS/JavaScript.

## Scope and limitations

This is a development release. It does not implement payments, refunds, QR tickets, WebSocket pushes, a background email queue, or production-scale database migrations. Email delivery is best-effort and defaults to a local console preview.

**Release tag:** `v4.0`  
**Release title:** `CSTBS v4.0 — Administration`

## Suggested commands

After reviewing and committing the V4 changes in your Git repository:

```bash
git add .
git commit -m "feat: introduce CSTBS v4.0 administration"
git tag -a v4.0 -m "CSTBS v4.0 - Administration"
git push origin main
git push origin v4.0
```
