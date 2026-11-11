# CSTBS v5.0 — Final Release: Reporting, Security & Documentation

## Overview

Campus Stadium Ticket Booking System **v5.0** completes the five-version Flask/SQLite development milestone. It integrates authentication, role-based access, event CRUD, interactive reservations, seat administration and booking notifications, adding administrator PDF/CSV exports, tightened security and full operational documentation.

## New in v5.0

- **Booking reports:** admin-only PDF and CSV exports, filtered by event and reservation status; include owner, seat, event, date, booking status and price-at-booking.
- **Event reports:** PDF and CSV exports with event details and seat capacity, reserved, blocked and available counts.
- **PDF rendering:** ReportLab landscape reports with repeated table headers, confidentiality footer and page numbering.
- **Export safety:** CSV formula-injection protection, UTF-8 export, private/no-store attachments and 2,000 PDF / 10,000 CSV row caps.
- **Application security:** Flask-Limiter rate limits, strong password-length requirement, bounded event prices and request sizes, CSRF expiry, secure headers, SQLite FK enforcement and production configuration gates.
- **Deployment improvements:** explicit `flask init-db` command, no debug mode by default, localhost-bound development server and an environment-based configuration guide.
- **Demonstration:** improved home-page experience, Reports dashboard and optional local demo users, reservations and blocked seats seeded with a private password.
- **Documentation:** full User Manual, Admin Manual, Installation & Deployment Guide, SECURITY.md, updated requirements, UML, database design, README and complete V1–V5 changelog.
- **Tests:** V5 report access, formats, filters and CSV safety coverage added to the existing V1–V4 suite.

## Preserved from previous versions

- **v1.0:** Responsive Flask/Jinja2 prototype and database foundation.
- **v2.0:** Flask-Login accounts, password hashing, student/staff/admin roles and event CRUD.
- **v3.0:** Interactive seat map, atomic seat reservations, booking history/cancellation and double-booking prevention.
- **v4.0:** Admin dashboard, seat/section management, user roles, all-booking administration and Flask-Mail notifications.

## Technology

Python 3.10+, Flask, SQLAlchemy, Flask-SQLAlchemy, SQLite, Flask-Login, Flask-WTF, Flask-Mail, Flask-Limiter, ReportLab, Werkzeug, python-dotenv, Jinja2, HTML, CSS, JavaScript and Gunicorn for Unix deployments.

## Scope and release notes

No payments, issued tickets or refunds. This remains a **small-installation/deployment-oriented reference application** using SQLite, near-real-time polling and best-effort mail. Public campus rollout requires security review, production DB migration planning, backup/restore testing and approved infrastructure.

**Version:** `5.0.0`  
**GitHub tag:** `v5.0`  
**Release title:** `CSTBS v5.0 — Final Release: Reporting, Security & Documentation`

The attached ZIP contains the complete source, manuals, tests and Version 5 change-report PDF. Never upload `.env` or a live SQLite database.
