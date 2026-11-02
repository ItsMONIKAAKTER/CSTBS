"""CSRF-protected account and event forms for CSTBS Version 2."""

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    DecimalField,
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
