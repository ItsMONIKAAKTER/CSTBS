# Database Design — CSTBS v5.2

The core `User`, `Event`, `Seat` and `Booking` relational schema from earlier releases remains unchanged. Students have a unique nullable-for-legacy `User.student_id`; fresh student registration requires 6–20 alphanumeric characters. `User.role` is `student`, `staff` or `admin`, controlled by the server.

## Administrator login-key records

The existing V5.1 `admin_invitations` table is retained for compatibility but now represents **administrator login keys**, not registration invitations:

| Column | Meaning |
|---|---|
| `id` | PK |
| `token_hash` | Unique HMAC-SHA256 fingerprint (never plaintext) |
| `target_user_id` | FK `users.id`, required by the V5.2 login verification logic |
| `created_by_id` | Optional admin who issued via dashboard |
| `bootstrap` | True for first local setup |
| `created_at`, `expires_at` | UTC timestamps; lifetime 20 minutes |
| `used_at`, `used_by_id` | Audit of successful use or revocation |

V5.1 tokens lacking `target_user_id` are invalidated. New keys are only issued for `User.role='admin'`, and verification requires both matching HMAC and the **same admin email** as the target FK. Atomic `UPDATE ... WHERE used_at IS NULL AND expires_at > now` prevents replay. New keys revoke previous unused keys to the same admin.

## Compatibility

`app/migrations_v52.py` adds `target_user_id` and its index with SQLite `ALTER TABLE`/`CREATE INDEX` if missing, and revokes legacy unbound tokens. It preserves student IDs, all users, events, seats, existing bookings, historic amounts and role records. Back up the DB before upgrading and use reviewed migrations for production deployment.
