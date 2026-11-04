"""WSGI entry point (`python run.py` locally or production WSGI import)."""
import sys
from sqlalchemy import select
from app import create_app, db
from app.models import User
from app.admin_keys import provision_first_admin, print_terminal_login_key, normalize_email

app = create_app()


def interactive_local_admin_key():
    """Set up first admin by terminal prompt, then issue a targeted login key.

    Never run this from a WSGI worker or when standard input isn't interactive.
    """
    if app.config.get("APP_ENV") == "production":
        return
    if not sys.stdin.isatty():
        print("Admin login key: run 'python -m flask --app run.py admin-key EMAIL' "
              "or 'python -m flask --app run.py admin-setup' in PowerShell.")
        return
    with app.app_context():
        admins = db.session.scalars(select(User).where(
            User.role == "admin").order_by(User.id)).all()
        if not admins:
            print("\nCSTBS FIRST ADMIN SETUP (terminal only; no Notepad needed)")
            try:
                email = input("Enter your first administrator email: ").strip()
                name = input("Administrator full name [University Administrator]: ").strip()
                user = provision_first_admin(email, name or "University Administrator")
            except (EOFError, KeyboardInterrupt):
                print("\nSetup cancelled; the site is still available.")
                return
            except ValueError as exc:
                print(f"Setup was not completed: {exc}")
                print("You can retry using: python -m flask --app run.py admin-setup")
                return
            print_terminal_login_key(user, bootstrap=True)
        else:
            if len(admins) == 1:
                user = admins[0]
            else:
                print("\nAdministrators: " + ", ".join(x.email for x in admins))
                try:
                    email = normalize_email(input("Admin email to generate login key for (blank to skip): "))
                except (EOFError, KeyboardInterrupt, ValueError):
                    print("Skipping key generation. Use the admin-key command later.")
                    return
                user = next((x for x in admins if x.email == email), None)
                if user is None:
                    print("No administrator found for that email. Use the admin-key command.")
                    return
            print_terminal_login_key(user)


if __name__ == "__main__":
    interactive_local_admin_key()
    app.run(host="127.0.0.1", port=5000, debug=False)
