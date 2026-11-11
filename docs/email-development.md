# CSTBS v4.0 — Email Development Guide

V4 sends booking confirmation and cancellation messages **only after successful booking database commits**. The service uses `flask_mail.Message` with two selectable development transports.

## 1. Console preview — default

Set `MAIL_BACKEND=console` in `.env` (already the default). The app logs a preview in the Flask server console, including recipient, subject and booking details. No SMTP connection is made. Example:

```text
CSTBS EMAIL PREVIEW
To: student@example.edu
Subject: CSTBS booking confirmed: Campus Football Night

Hello ...
Your CSTBS reservation is confirmed.
...
```

Be cautious: console logs contain user identifiers and seat bookings. Never stream application logs to a public website or version-control them.

## 2. Ethereal test SMTP

Create Ethereal credentials (see https://ethereal.email/), then configure `.env`:

```dotenv
MAIL_BACKEND=smtp
MAIL_SERVER=smtp.ethereal.email
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your-ethereal-username
MAIL_PASSWORD=your-ethereal-password
MAIL_DEFAULT_SENDER=CSTBS <no-reply@campus.example>
MAIL_SUPPRESS_SEND=false
```

Restart Flask, confirm a booking and inspect Ethereal's web inbox. Ethereal is a test SMTP provider; messages do not go to real recipients. Keep credentials in `.env` only, never commit them. The `MAIL_DEFAULT_SENDER` placeholder should be replaced when using a real outbound mail service in a future release.

## 3. Scenarios

| Action | Mail |
| --- | --- |
| User confirms several seats at once | **One** confirmation message listing all selected seats and their informational total. |
| User cancels one of their bookings | **One** cancellation message to owner. |
| Admin cancels somebody else's active booking | **One** cancellation message to owner. |
| User attempts invalid/stale confirmation | **No** notification. |
| Booking is already cancelled | **No** repeated notification. |
| Mail transport fails after saving | Saved booking remains; error is logged; delivery may need manual follow-up. |

## 4. Verification & future operations

Run `python -m unittest discover -s tests -v` after installing requirements. In addition, test with `MAIL_BACKEND=smtp` against Ethereal if desired. The notification component does not guarantee delivery, retries, background processing or a durable outbox. These are out of scope for V4 and should be implemented before production use. Authentication sessions, SMTP secrets and CSRF tokens should never appear in email bodies.
