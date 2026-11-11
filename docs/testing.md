# CSTBS V5.4 — Test & Release Checklist

## Verified offline in the build environment

- Python syntax and compilation across application, config and tests.
- All 29 Jinja2 templates parse; all three JavaScript files pass Node syntax checks.
- The **actual V5.4 SQLite migration** ran twice against an old schema: backfilled event gates, retained ticket identities, rejected assignment of another event's gate, and added the check-in gate audit field.
- A generated signed-shaped QR image is decoded correctly by the bundled OpenCV/Pillow decoding path; malformed images are rejected.
- Final PDF rendered and ZIP archive checked after packaging.

## Not yet verified in this environment

Flask and extensions could not be installed from this runner's package source, so **live Flask HTTP integration tests, device camera permissions on Windows/phones, multi-scanner concurrency tests, and production email/Redis tests have not been executed**. Their success must be demonstrated on a dependency-enabled machine and via GitHub Actions before public admission.

## Local/CI commands

```powershell
python -m pip install -r requirements.txt
python -m pip check
python -m unittest discover -s tests -v
python -m compileall -q app config.py run.py tests
```

## Acceptance scenario

1. Install as a student; register with unique Student ID; verify dashboard and one active ticket per event, including classmate booking attempts.
2. As administrator open `/admin/`, create an event, configure gates per section, open all gates and then close one gate individually.
3. As staff select a gate under `/entry/scan`, check QR with live camera over HTTPS/localhost **and** with QR photograph upload in a browser without BarcodeDetector.
4. Verify each possible outcome: unknown/altered, cancelled, checked in, valid-entry-not-open, wrong gate, individually closed gate and correct open gate.
5. Verify only the correct gate with explicit CSRF-protected POST allows the first check-in, while a second POST cannot double-admit.
6. Inspect the ticket details for date/time/venue/gate/section/row/seat/Student ID/status.
7. Back up and upgrade a copy of a V5.3 database twice; ensure existing records, QR credentials and reports survive, and ensure `.env`/DB/private secrets are never committed.
8. Require successful GitHub CI and campus operator sign-off before staging or production deploy.

# CSTBS v5.3 — Verification and release checklist

## Checks completed in the build environment

- All Python files compile successfully with Python 3.13 (`python -m compileall`). The project targets Python 3.10+, and CI tests Python 3.10/3.11/3.12.
- All 27 Jinja2 templates parse successfully.
- All application JavaScript files pass `node --check`.
- The SVG static asset parses successfully.
- The **real** `upgrade_v53()` function was executed twice against a synthetic V5.2 SQLite schema and passed checks for schema changes, backfilling duplicate legacy bookings as unassigned, live-ticket uniqueness, admin activation state, and booking-cancellation trigger behavior.
- A sample QR payload can be encoded by the `qrcode` package with `itsdangerous` signing and rendered as PNG; the PDF change report rendered successfully and its pages were inspected.
- The ZIP was checked for integrity and for excluded `.env`, `.db`, `.local_secret_key`, backup and virtual-environment files.

## Checks not executed in this environment

The Flask application integration tests and browser-based QR camera/HTTPS/SMTP/load tests **could not be run here** because Flask and its extensions are not installed and the package index is inaccessible from this runner. The GitHub Actions test workflow includes the full Python integration suite and runs after source code is pushed. It is not evidence of a successful run until GitHub CI reports green.

## Tests to run before release

```powershell
python -m pip install -r requirements.txt
python -m pip check
python -m unittest discover -s tests -v
python -m compileall -q app config.py run.py tests
```

Manual staging checks: initial admin activation and post-activation password login, expired/reused key failure, admin recovery, student registration and unique IDs, multi-student booking, one ticket per student/event, race between two seat bookings, QR generation, cancelled/used QR rejection, staff camera permission on HTTPS, CSV/PDF exports, V5.2 database upgrade (including backup), and full restore drill. Require institutional privacy/security review and concurrency load tests before production use.
