"""CSRF-protected account and event forms for CSTBS Version 2."""

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    DecimalField,
    IntegerField,
    SelectField,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Regexp,
)

EMAIL_VALIDATORS = [
    DataRequired(),
    Length(max=254),
    Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="Enter a valid email address."),
]


class LoginForm(FlaskForm):
    """Authenticate an existing user."""

    email = StringField("Email address", validators=EMAIL_VALIDATORS)
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    """Register a new student account (never an admin account)."""

    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email address", validators=EMAIL_VALIDATORS)
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")


class EventForm(FlaskForm):
    """Validate an event before an administrator saves it."""

    title = StringField("Event title", validators=[DataRequired(), Length(min=3, max=150)])
    category = StringField("Category", validators=[DataRequired(), Length(max=40)])
    description = TextAreaField(
        "Description", validators=[DataRequired(), Length(min=10, max=5000)]
    )
    venue = StringField("Venue", validators=[DataRequired(), Length(max=120)])
    starts_at = DateTimeLocalField(
        "Starts at (campus local time)",
        format="%Y-%m-%dT%H:%M",
        validators=[InputRequired()],
    )
    price = DecimalField(
        "Entry price (USD)", places=2, validators=[InputRequired(), NumberRange(min=0)]
    )
    submit = SubmitField("Save event")


class DeleteEventForm(FlaskForm):
    """Dedicated POST-only form for destructive event actions."""

    submit = SubmitField("Delete event")


class CreateSectionForm(FlaskForm):
    """Generate seating inventory in a distinct event section."""
    name = StringField("Section name", validators=[DataRequired(), Length(min=2, max=30),
        Regexp(r"^[A-Za-z0-9][A-Za-z0-9 _-]*$", message="Use letters, numbers, spaces, _ or -." )])
    rows = IntegerField("Rows", validators=[InputRequired(), NumberRange(min=1, max=20)])
    seats_per_row = IntegerField("Seats per row",
        validators=[InputRequired(), NumberRange(min=1, max=30)])
    submit = SubmitField("Add section")


class RenameSectionForm(FlaskForm):
    """Change a section's display name without altering bookings."""
    old_name = StringField("Existing section", validators=[DataRequired(), Length(max=30)])
    new_name = StringField("New section name", validators=[DataRequired(), Length(min=2, max=30),
        Regexp(r"^[A-Za-z0-9][A-Za-z0-9 _-]*$")])
    submit = SubmitField("Rename section")


class RoleForm(FlaskForm):
    """Admin-only role change; cannot be supplied during registration."""
    role = SelectField("Role", choices=[("student", "Student"), ("staff", "Staff"),
                                        ("admin", "Admin")], validators=[DataRequired()])
    submit = SubmitField("Update role")
