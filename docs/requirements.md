# CSTBS Version 1 — Requirements Analysis

## 1. Purpose

Build a responsive, read-only web prototype for the Campus Stadium Ticket Booking System (CSTBS). The prototype demonstrates how visitors will discover campus stadium events. It **does not** sell tickets, create bookings, or authenticate users.

## 2. Stakeholders and actors

- **Visitor:** Browse the homepage, event catalog, and individual event details.
- **Prospective account holder:** View and try UI-only login and registration forms.
- **Project maintainer:** Configure the application, review the schema, and extend it in later versions.

## 3. Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Homepage | `/` shows introductory content and up to three upcoming events. |
| FR-02 | Event listing | `/events` lists demo events with name, date, venue, and entry price. |
| FR-03 | Event details | `/events/<id>` shows full description, date, time, venue, category, and price; unknown IDs return 404. |
| FR-04 | Login UI | `/login` presents a CSRF-protected Flask-WTF form and a notice that authentication is disabled. |
| FR-05 | Registration UI | `/register` presents a CSRF-protected Flask-WTF form and a notice that no account is created. |
| FR-06 | Navigation | Shared navbar links to Home, Events, Login, and Register. |
| FR-07 | Seed data | An empty SQLite database is initialized with four clearly illustrative events. |
| FR-08 | Schema | User, Event, Seat, and Booking tables are defined for future work. |

## 4. Non-functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| NFR-01 | Maintainability | Flask app factory, routes, forms, models, and templates are separated. |
| NFR-02 | Portability | Runs on Python 3.10+ with SQLite, without a separate database server. |
| NFR-03 | Responsiveness | Layout adapts to phones, tablets, and desktops. |
| NFR-04 | Basic accessibility | Semantic landmarks, labels, keyboard focus, and mobile navigation controls exist. |
| NFR-05 | Configuration security | Secret key comes from untracked `.env`; forms include CSRF tokens. |
| NFR-06 | Git readiness | Dependencies, setup instructions, `.env.example`, and `.gitignore` are included. |

## 5. Scope boundaries

**Included:** Read-only event catalog, UI-only account forms, SQLite schema, sample data, responsive styling, requirements/design documentation.

**Explicitly excluded:** Real authentication, password hashing workflows, user creation, event administration, seat selection, booking logic, inventory locking, payment processing, emails, real-time availability, deployment configuration, migration tooling. Database fields for later versions are **design placeholders**, not implemented features.

## 6. User journeys

1. Visitor opens homepage, views upcoming highlights, selects **Explore events**.
2. Visitor opens an event card and reads its details and illustrative price.
3. Visitor clicks **Login** or **Register**, sees a clear prototype notice, and can submit sample values for validation; no credentials are checked or saved.

## 7. Assumptions and constraints

- Event descriptions, prices, and dates are demo data, not live university announcements.
- Event start times are naive **campus-local** times for the prototype; the campus time zone must be specified before production use.
- `User`, `Seat`, and `Booking` tables remain empty in V1.
- An auto-created SQLite file is intended for **local development**, not concurrent production ticket sales.
- This version uses `db.create_all()` for a fresh schema; it does not alter an existing schema after model changes.

## 8. Version 1 acceptance checklist

- [ ] Install dependencies in a virtual environment.
- [ ] Set a non-placeholder `SECRET_KEY` in `.env`.
- [ ] Start `python run.py` and open `/`.
- [ ] Browse `/events` and open an event detail page.
- [ ] Confirm an unknown event ID returns 404.
- [ ] Open `/login` and `/register`, inspect errors, and confirm no account is created.
- [ ] Confirm `instance/cstbs.db` contains the four schema tables.
- [ ] Inspect layouts on mobile and desktop widths.
