"""
This script runs the Flask web dashboard.
"""

from dashboard.app import app

if __name__ == "__main__":
    # Running on 0.0.0.0 makes it accessible from outside the container
    app.run(host="0.0.0.0", port=8080)
