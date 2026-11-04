"""Booking notification service; no email failures can reverse committed bookings.

The console mode uses Flask-Mail's Message formatting without any SMTP calls.
Use the SMTP backend with Ethereal test credentials for end-to-end mail tests.
"""

from flask import current_app
from flask_mail import Message

from . import mail


def _deliver(subject, recipient, body):
    """Send SMTP email or log preview; never expose SMTP secrets."""
    try:
        message = Message(subject=subject, recipients=[recipient], body=body)
        backend = current_app.config.get("MAIL_BACKEND", "console")
        if backend == "console":
            current_app.logger.info("CSTBS EMAIL PREVIEW\nTo: %s\nSubject: %s\n\n%s",
                                    recipient, subject, body)
        elif backend == "smtp":
            mail.send(message)
        else:
            raise ValueError("MAIL_BACKEND must be 'console' or 'smtp'")
    except Exception:
        # The booking has already committed; a notification failure isn't a
        # justification for deleting it or retrying a reservation.
        current_app.logger.exception("Booking email delivery failed; saved booking is unchanged")
        return False
    return True


def notify_booking_confirmed(user, event, bookings):
    """Send one summary email after a multi-seat confirmation commits."""
    names = ", ".join(f"{booking.seat.display_label} ({booking.ticket.attendee_name})" if booking.ticket else booking.seat.display_label for booking in bookings)
    body = (f"Hello {user.full_name},\n\nYour CSTBS reservation is confirmed.\n\n"
            f"Event: {event.title}\nVenue: {event.venue}\n"
            f"When: {event.starts_at:%Y-%m-%d %H:%M} (campus time)\n"
            f"Seats: {names}\nAdmission: Free (CNY ¥0.00); no payment required.\n\n"
            "View each person's QR ticket by signing in to CSTBS. Do not share QR codes publicly.\n")
    return _deliver(f"CSTBS booking confirmed: {event.title}", user.email, body)


def notify_booking_cancelled(booking):
    """Notify the booking owner, including when an admin cancelled it."""
    body = (f"Hello {booking.user.full_name},\n\nYour CSTBS reservation was cancelled.\n\n"
            f"Event: {booking.event.title}\nSeat: {booking.seat.display_label}\n"
            "University reservations are free; no payment or refund is involved.\n")
    return _deliver(f"CSTBS booking cancelled: {booking.event.title}",
                    booking.user.email, body)
