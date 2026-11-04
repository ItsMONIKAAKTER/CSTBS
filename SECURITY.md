# Security Policy — CSTBS v5.0

CSTBS v5.0 is a learning/reference deployment with strong baseline web controls, not a payment or production-scale ticket platform. Review and test security against your institution's requirements before public access.

## Implemented controls

- Werkzeug hashed passwords (never store plaintext), Flask-Login sessions and student/staff/admin authorization checks.
- Global Flask-WTF CSRF validation on state-changing requests, including booking review/confirmation and admin modifications.
- IP-based Flask-Limiter defaults: 300/hour, with tighter registration/login POST, seat polling and confirm limits. Limit stores must be shared between workers.
- Host allowlist required in production, HTTPS-only session cookies and HSTS, `SameSite=Lax`/HttpOnly, CSP, no frames, MIME-sniff prevention and maximum POST payload sizes.
- Server-side seat validity and ownership validation; SQLite partial unique active-seat index, blocked-seat triggers and foreign-key checks.
- PDF/CSV exports restricted to admins; CSV cells protected from formula injection; report responses disable caching and cap size.
- No secrets or real SQLite data included in Git; `.env`, instance DB and caches are ignored.

## Before deploying to real campus users

1. Require and test HTTPS, private secret storage, Redis-backed rate limiting, trusted hostnames and an approved SMTP sender.
2. Threat-model account recovery, admin account onboarding, log privacy, credential stuffing, password reset, confirmation emails and escalation prevention.
3. Add reviewed schema migrations, production-grade DB with concurrency testing, detailed administrative audit logs, retention/privacy policy and backups.
4. Use dependency scanning, a pinned lockfile, patch management and automated CI/security tests.
5. Restrict data exports and logs containing student or reservation personal data; arrange approved access and deletion practices.
6. Confirm actual source IP handling through your reverse proxy, never blindly trust forwarded-IP headers.

## Known limits

- Synchronous best-effort email; no durable outbox, delivery guarantee or retry.
- No MFA, password reset, temporary booking holds or payment/identity verification.
- SQLite is suitable for low volume and local demos, not high-traffic onsales.
- CSP allows inline *styles* to support the inherited seat-grid column CSS variable, but disallows inline scripts.
- Rate limits using in-memory storage are appropriate only in local single-process development.

If you identify a vulnerability, **do not publish account credentials or personal data in a public GitHub issue**. Report it privately to the repository maintainer using the host platform's private vulnerability reporting channel if configured.
