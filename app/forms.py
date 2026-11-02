"""Flask-WTF demo forms; neither form performs authentication in Version 1."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

EMAIL_VALIDATORS = [
    DataRequired(),
    Length(max=254),
    Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="Enter a valid email address."),
]


class LoginForm(FlaskForm):
    """UI-only sign-in fields."""

    email = StringField("Email address", validators=EMAIL_VALIDATORS)
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    """UI-only registration fields; submitted data is never saved."""

    full_name = StringField(
        "Full name", validators=[DataRequired(), Length(min=2, max=120)]
    )
    email = StringField("Email address", validators=EMAIL_VALIDATORS)
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8)]
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")
