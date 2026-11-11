# CSTBS v5.2 — Simplified Administrator Login

## Overview

Version 5.2 replaces complicated administrator self-registration with a secure, single-screen administrator login experience. **No need to paste keys into Notepad, `.env`, PyCharm or SQLite.**

## What's New

- Administrators sign in at `/admin/login` with **email + one-time access key**.
- The login key is automatically generated in the local server terminal, linked to the correct admin account, valid for **20 minutes**, and expires after use.
- On first local startup, a simple PowerShell prompt creates the first admin account without code or database editing.
- Added `flask admin-key EMAIL` for instant key regeneration and `flask admin-setup` for first-time provisioning.
- Existing admins can generate login keys for other approved admin accounts through the Users dashboard.
- Removed the public admin registration form. No public key can grant admin rights to an arbitrary email.
- Local development automatically generates a persistent private Flask secret if none is configured, simplifying Windows setup.
- Existing users, student IDs, free seat bookings, event management, PDF/CSV reports and RMB/CNY displays are preserved.
- Updated database migration, tests, README, security notes and manuals.

## Security

- Secure random single-use keys, email-specific binding, HMAC-SHA256 hashed key storage, 20-minute expiry, replay protection, CSRF and request rate limits.
- Only an already-approved administrator account can redeem a key.
- Production still needs controlled provisioning, HTTPS, MFA/SSO planning and deployment security reviews.

**Version:** 5.2.0  
**GitHub tag:** `v5.2`  
**Release title:** CSTBS v5.2 — Simplified Administrator Login
