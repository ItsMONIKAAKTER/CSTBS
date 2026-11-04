"""WSGI entry point: `gunicorn 'run:app'` or `python run.py` locally."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Bind to loopback only. Never enable the interactive debugger on public hosts.
    app.run(host="127.0.0.1", port=5000, debug=False)
