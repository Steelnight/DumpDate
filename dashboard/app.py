"""
This module contains a Flask-based web dashboard to display KPIs and system logs.
"""
from flask import Flask, render_template

from schedule_parser.facade import WasteManagementFacade

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Renders the main dashboard page."""
    facade: WasteManagementFacade = app.config["FACADE"]
    data = facade.get_dashboard_data()
    return render_template(
        'dashboard.html',
        events=data.get('events', []),
        subscriptions=data.get('subscriptions', []),
        logs=data.get('logs', []),
        error=data.get('error')
    )


def run_dashboard(facade: WasteManagementFacade):
    """Runs the Flask development server."""
    app.config["FACADE"] = facade
    # Running on 0.0.0.0 makes it accessible from outside the container
    app.run(host="0.0.0.0", port=8080)
