# CSTBS Security and Privacy

CSTBS manages university student identities and stadium entry credentials. The project should be deployed publicly only after full integration tests, an institutional privacy review and independent security assessment.

## Security controls

- Passwords are stored as Werkzeug hashes. Administrators activate their accounts using one-time, expiring, hashed keys and use passwords thereafter.
- Students have one active ticket per event. Attendee names and Student IDs must match registered student accounts. Seat and ticket uniqueness are database-enforced.
- Flask-Login sessions, role checks, global Flask-WTF CSRF protection and rate limiting protect state-changing actions.
- Ticket QR codes contain only signed opaque identifiers; verification checks the current database record and event/gate status. Each QR is usable for check-in only once.
- QR scanning is restricted to staff/admin accounts. Camera permissions require a secure browser context; the photo decoder accepts bounded image uploads and does not retain uploaded images.
- PDFs and CSVs are admin-only; CSV data is escaped to avoid spreadsheet formula injection. Sensitive downloads use private no-cache headers.
- SQLite foreign keys, uniqueness rules and triggers protect bookings, blocked seats and ticket identity.

## Protect secrets and private data

Never commit `.env`, local secret files, `instance/*.db`, backups, live tickets or student records. For production, set separate, persistent `SECRET_KEY` and `TICKET_SIGNING_KEY` values. Keep both stable across deployments, use HTTPS, secure cookies, a trusted host configuration, real SMTP, shared rate limiting, and regular recoverable backups.

## Responsible disclosure

Do not post student data, QR tokens, private keys or production database contents in public issues. Report a security issue privately to the maintainers through the repository's supported security-reporting mechanism.
