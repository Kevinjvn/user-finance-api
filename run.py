from app import create_app
import sys

app = create_app()

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        print(f"Failed to start application: {e}", file=sys.stderr)
        sys.exit(1)
