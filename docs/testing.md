# Testing and Release Checklist

Run `python -m unittest discover -s tests -v` with all requirements installed. GitHub Actions performs this on supported Python versions, plus compilation and JavaScript checks. Tests keep CSRF and role authorization active.

Before publishing, verify: registration and unique student IDs; one active ticket per student per event; group attendee name/ID matching; blocked-seat and duplicate-seat rejection; admin activation/password and revoked keys; all role permissions; event/seat/gate controls; QR signing, incorrect gate, closed entry, cancellation and duplicate check-in; photo scanning on an actual device; PDF/CSV exports; and database backup/migration restoration.

**Windows SQLite tests:** raw connections and test engines must be closed/disposed before removing temporary directories.

**Integration warning:** compile-only or schema-only tests do not replace running the full Flask test suite, verifying a phone scanner over HTTPS, and rehearsing restore from backup.
