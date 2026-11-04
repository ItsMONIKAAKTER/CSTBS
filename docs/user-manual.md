# CSTBS v5.0 — User Manual

**Audience:** students, staff, and administrators using the public website. No payment is collected by CSTBS; a confirmed booking reserves seat inventory only.

## 1. Access the website

Open the URL given by your campus administrator. The navigation menu contains **Home**, **Events**, **Login/Register**, and, after login, **My bookings** and **My account**. On narrow screens use the **Menu** button. Keyboard users can press Tab and use the **Skip to content** link.

## 2. Create an account

1. Choose **Register**.
2. Enter your full name, a valid email address, and a password of 12–128 characters.
3. Confirm the password, then submit the form.
4. You are signed in as a **student**. Staff/admin privileges cannot be requested through registration; an authorized administrator controls those roles.

If the email already exists, use **Login** instead. Never reuse sensitive passwords for test accounts. The app does not implement password recovery; ask your campus administrator for assistance using your organization's approved identity-verification process.

## 3. Find events

1. Open **Events** from the navigation.
2. Browse event cards for the date, category and price.
3. Open an event to read its description, venue and campus-local start time.
4. For a future event, select **Choose seats**. A past event cannot be booked.

## 4. Reserve seats

1. Log in if asked.
2. On the seating map, choose up to **six** available seat buttons. Seats are grouped by section and row.
3. Understand the map colors: **available** (selectable), **selected**, **reserved** (already taken) and **blocked** (closed by administration).
4. The screen refreshes seat availability every five seconds. This is a snapshot, not a temporary hold. Another user might reserve a selected seat before you finish.
5. Choose **Review booking**. Check the event, seat labels and informational price total.
6. Choose **Confirm booking** to submit the reservation. The server checks each seat again and saves all selected seats atomically. If a conflict appears, return to the map and select again.
7. View the result under **My bookings**. You will receive a confirmation email when email delivery is configured; the local demo only logs an email preview.

**Notes:** The amount displayed is not a payment request. The system does not issue printable tickets or QR codes.

## 5. View or cancel your booking

1. Open **My bookings** after signing in.
2. Find the reservation. Each seat is listed separately with its event, price and status.
3. Select **Cancel** on an active reservation and confirm the browser prompt.
4. The record changes to **Cancelled** and the seat returns to inventory. Cancelled entries remain visible for history and cannot be reactivated; book again to reserve a seat if still available.

You can cancel only your own bookings. Administrators may cancel any booking for operational reasons and the owner receives a cancellation notification (or console preview). Refunds are not applicable because CSTBS does not take payments.

## 6. Account and session safety

The **My account** page displays your account details and role. Use **Sign out** on shared computers. Do not share passwords. If sign-in attempts are too frequent, the system may return **429 Too Many Requests**; stop retrying and try later. If a form token expires (CSRF validation error), refresh the page and resubmit.

## 7. Troubleshooting

| Problem | Try this |
| --- | --- |
| Seat changed to reserved | Refresh the map and choose another seat. |
| Booking review says selection expired | Return to the map, reselect and confirm. |
| Cannot book a past event | Choose an upcoming event. |
| Cannot sign in | Check email/password; contact your administrator if access is lost. |
| 403 on admin pages | Your account is not in the admin role. |
| Received no email | Check the admin's configured backend; the demo uses console previews. |
| 429 response | Stop repeated requests and try after the rate-limit window. |

Support and campus policies are determined by your deploying institution. No real customer support address is provided in this example system.
