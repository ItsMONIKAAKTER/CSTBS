"""WSGI entry point: `gunicorn 'run:app'` or `python run.py` locally."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # First-run admin keys are printed only by the local interactive server,
    # not by `flask init-db`, migrations or production WSGI worker imports.
    if app.config.get("APP_ENV") != "production":
        from app.admin_keys import ensure_local_bootstrap_key
        with app.app_context():
            ensure_local_bootstrap_key()
    # Bind to loopback only. Never enable the interactive debugger on public hosts.
    app.run(host="127.0.0.1", port=5000, debug=False)
