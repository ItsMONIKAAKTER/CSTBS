"""Launch the CSTBS Version 2 local development server."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Never run Flask's interactive debugger in a public environment.
    app.run(debug=True)
