"""
This module contains a Flask-based web dashboard to display KPIs and system logs.
"""
from flask import Flask, render_template

# Assuming the facade is initialized similarly to the bot
# In a real app, you'd use a factory or application context
from schedule_parser.services.address_service import AddressService
from schedule_parser.services.persistence_service import PersistenceService
from schedule_parser.services.schedule_service import ScheduleService
from schedule_parser.services.subscription_service import SubscriptionService
from schedule_parser.services.notification_service import NotificationService
from schedule_parser.facade import WasteManagementFacade

app = Flask(__name__)

# --- Facade Initialization ---
address_service = AddressService()
persistence_service = PersistenceService()
schedule_service = ScheduleService()
subscription_service = SubscriptionService(persistence_service)
notification_service = NotificationService(persistence_service)

facade = WasteManagementFacade(
    address_service=address_service,
    schedule_service=schedule_service,
    persistence_service=persistence_service,
    subscription_service=subscription_service,
    notification_service=notification_service,
)
# --- End Facade Initialization ---

@app.route('/')
def dashboard():
    """Renders the main dashboard page."""
    data = facade.get_dashboard_data()
    return render_template(
        'dashboard.html',
        events=data.get('events', []),
        subscriptions=data.get('subscriptions', []),
        logs=data.get('logs', []),
        error=data.get('error')
    )

if __name__ == '__main__':
    app.run(debug=True)
