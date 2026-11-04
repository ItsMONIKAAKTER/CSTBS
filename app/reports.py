"""Administrator-only booking and event exports (PDF and CSV).

The report layer intentionally never mutates data. Filters are validated before
queries are executed, access control runs on every endpoint, and response bytes
are generated in memory rather than written into the public static directory.
"""

import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from flask import Blueprint, abort, render_template, request, send_file
from flask_login import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from . import db
from .authz import admin_required
from .models import Booking, Event, Seat, Ticket

reports = Blueprint("reports", __name__, url_prefix="/admin/reports")
EXPORT_MAX_CSV_ROWS = 10000
EXPORT_MAX_PDF_ROWS = 2000


def _read_filters():
    """Allow only documented query arguments, with strict types and limits."""
    status = request.args.get("status", "all")
    raw_event_id = request.args.get("event_id", "")
    if status not in {"all", "reserved", "cancelled"}:
        abort(400, "Invalid status filter.")
    if raw_event_id and (not raw_event_id.isascii() or not raw_event_id.isdecimal()
                         or len(raw_event_id) > 10 or int(raw_event_id) < 1):
        abort(400, "Invalid event filter.")
    return status, (int(raw_event_id) if raw_event_id else None)


def _booking_records(status, event_id, max_rows):
    query = select(Booking).join(Seat).options(
        joinedload(Booking.user),
        joinedload(Booking.seat).joinedload(Seat.event),
    )
    if status != "all":
        query = query.where(Booking.status == status)
    if event_id is not None:
        query = query.where(Seat.event_id == event_id)
    rows = db.session.scalars(query.order_by(Booking.created_at.desc(), Booking.id.desc())
                              .limit(max_rows + 1)).all()
    if len(rows) > max_rows:
        abort(413, f"Export exceeds {max_rows:,} rows. Narrow your filters.")
    return rows


def _event_records(max_rows):
    # Correlated SQL counts avoid loading every Seat/Booking into memory.
    total_seats = (select(func.count(Seat.id)).where(Seat.event_id == Event.id)
                   .correlate(Event).scalar_subquery())
    blocked_seats = (select(func.count(Seat.id)).where(
        Seat.event_id == Event.id, Seat.is_blocked.is_(True))
        .correlate(Event).scalar_subquery())
    reserved_seats = (select(func.count(Booking.id)).join(Seat).where(
        Seat.event_id == Event.id, Booking.status == "reserved")
        .correlate(Event).scalar_subquery())
    rows = db.session.execute(select(Event, total_seats, blocked_seats, reserved_seats)
        .order_by(Event.starts_at.desc(), Event.id.desc()).limit(max_rows + 1)).all()
    if len(rows) > max_rows:
        abort(413, f"Export exceeds {max_rows:,} events.")
    return rows


def _booking_table(records):
    headings = ["Booking ID", "Created (UTC)", "Event", "Seat", "User", "Email", "Status", "Admission (CNY)"]
    rows = [
        [str(b.id), b.created_at.strftime("%Y-%m-%d %H:%M"), b.event.title,
         b.seat.display_label, b.user.full_name, b.user.email,
         b.status, "0.00"]
        for b in records
    ]
    summary = f"{len(records)} bookings | {sum(b.status == 'reserved' for b in records)} active | University admission free (CNY 0.00)"
    return headings, rows, summary


def _event_table(records):
    headings = ["Event ID", "Event", "Category", "Venue", "Start (campus)", "Admission (CNY)", "Seats", "Reserved", "Blocked", "Available"]
    rows = [
        [str(event.id), event.title, event.category, event.venue,
         event.starts_at.strftime("%Y-%m-%d %H:%M"), "0.00",
         str(total), str(reserved), str(blocked), str(max(total - reserved - blocked, 0))]
        for event, total, blocked, reserved in records
    ]
    return headings, rows, f"{len(records)} events | {sum(row[6] != '0' for row in rows)} with seating inventory"


def _safe_csv_cell(value):
    """Prevent spreadsheet formula evaluation when user-entered data is exported."""
    cell = str(value)
    if cell.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + cell
    return cell


def _make_csv(headings, rows):
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(headings)
    writer.writerows([_safe_csv_cell(cell) for cell in row] for row in rows)
    return BytesIO(("\ufeff" + stream.getvalue()).encode("utf-8"))


def _make_pdf(title, headings, rows, summary, subtitle):
    out = BytesIO()
    document = SimpleDocTemplate(out, pagesize=landscape(A4), leftMargin=17 * mm,
        rightMargin=17 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=title, author="CSTBS Administration")
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle("ReportTitle", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#14243B"))
    normal_style = ParagraphStyle("ReportCell", fontName="Helvetica", fontSize=7.2,
        leading=9.5, spaceAfter=0)
    head_style = ParagraphStyle("ReportHeader", parent=normal_style,
        fontName="Helvetica-Bold", textColor=colors.white)
    intro_style = ParagraphStyle("ReportIntro", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#516278"), spaceAfter=6)

    def text_cell(value, style):
        # ReportLab's built-in fonts are intentionally ASCII-friendly; foreign
        # glyphs are replaced in the PDF while CSV retains original Unicode.
        raw = str(value).encode("latin-1", "replace").decode("latin-1")
        if len(raw) > 110:
            raw = raw[:107] + "..."
        return Paragraph(escape(raw), style)

    body = [Paragraph(escape(title), heading_style),
            Paragraph(escape(subtitle), intro_style),
            Paragraph(escape(summary), intro_style), Spacer(1, 9)]
    matrix = [[text_cell(value, head_style) for value in headings]]
    matrix += [[text_cell(value, normal_style) for value in row] for row in rows]
    if not rows:
        matrix.append([text_cell("No records found.", normal_style)] + [""] * (len(headings) - 1))
    # Evenly sized columns, with a little extra room for titles, names and email.
    weights = ([.7, 1.3, 1.8, 1, 1.3, 1.7, .8, .9] if len(headings) == 8 else
               [.65, 1.7, 1, 1.3, 1.25, .75, .65, .7, .65, .7])
    available_width = landscape(A4)[0] - 34 * mm
    widths = [available_width * weight / sum(weights) for weight in weights]
    table = Table(matrix, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17314A")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7FA")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), .5, colors.HexColor("#17314A")),
    ]))
    body.append(table)

    def page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#68768A"))
        canvas.drawString(17 * mm, 11 * mm, "CSTBS  |  Confidential administrative report")
        canvas.drawRightString(landscape(A4)[0] - 17 * mm, 11 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(body, onFirstPage=page_footer, onLaterPages=page_footer)
    out.seek(0)
    return out


def _download(stream, filename, mimetype):
    response = send_file(stream, mimetype=mimetype, as_attachment=True,
                         download_name=filename, max_age=0)
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@reports.get("/")
@login_required
@admin_required
def index():
    """Report hub and export form for administrators."""
    events = db.session.scalars(select(Event).order_by(Event.starts_at.desc())).all()
    return render_template("admin/reports.html", events=events)


@reports.get("/bookings.<format>")
@login_required
@admin_required
def bookings_export(format):
    """Download all matching bookings with the selected status/event filters."""
    if format not in ("csv", "pdf"):
        abort(404)
    status, event_id = _read_filters()
    records = _booking_records(status, event_id,
                               EXPORT_MAX_CSV_ROWS if format == "csv" else EXPORT_MAX_PDF_ROWS)
    headings, rows, summary = _booking_table(records)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if format == "csv":
        return _download(_make_csv(headings, rows), f"cstbs-bookings-{stamp}.csv", "text/csv; charset=utf-8")
    subtitle = f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC | Status: {status} | Event ID: {event_id or 'all'}"
    return _download(_make_pdf("Booking report", headings, rows, summary, subtitle),
                     f"cstbs-bookings-{stamp}.pdf", "application/pdf")


@reports.get("/events.<format>")
@login_required
@admin_required
def events_export(format):
    """Download event inventory and occupancy statistics."""
    if format not in ("csv", "pdf"):
        abort(404)
    records = _event_records(EXPORT_MAX_CSV_ROWS if format == "csv" else EXPORT_MAX_PDF_ROWS)
    headings, rows, summary = _event_table(records)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if format == "csv":
        return _download(_make_csv(headings, rows), f"cstbs-events-{stamp}.csv", "text/csv; charset=utf-8")
    subtitle = f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC | Live capacity snapshot"
    return _download(_make_pdf("Event inventory report", headings, rows, summary, subtitle),
                     f"cstbs-events-{stamp}.pdf", "application/pdf")


@reports.get("/attendance.<format>")
@login_required
@admin_required
def attendance_export(format):
    """Private attendance audit export, not a public QR validation endpoint."""
    if format not in ("pdf", "csv"):
        abort(404)
    limit = EXPORT_MAX_CSV_ROWS if format == "csv" else EXPORT_MAX_PDF_ROWS
    results = db.session.scalars(select(Ticket).order_by(Ticket.id.desc()).limit(limit + 1)).all()
    if len(results) > limit:
        abort(413, "Narrow the attendance export at the database/reporting layer.")
    headings = ["Ticket", "Event", "Attendee", "Student ID", "Seat", "Status", "Entry time (UTC)", "Booking owner"]
    rows = [[str(t.id), t.event.title, t.attendee_name, t.attendee_student_id or "",
        t.seat.display_label, t.status,
        t.checked_in_at.strftime("%Y-%m-%d %H:%M") if t.checked_in_at else "",
        t.booking.user.email] for t in results]
    summary = f"{len(results)} tickets | {sum(t.status == 'checked_in' for t in results)} checked in"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if format == "csv":
        return _download(_make_csv(headings, rows), f"cstbs-attendance-{stamp}.csv", "text/csv; charset=utf-8")
    subtitle = f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC | Confidential student attendance"
    return _download(_make_pdf("Stadium attendance report", headings, rows, summary, subtitle),
                     f"cstbs-attendance-{stamp}.pdf", "application/pdf")
