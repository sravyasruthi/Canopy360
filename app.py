# app.py - main entry point. Run the project with:  python app.py
import os
import sys
from datetime import date, timedelta

from flask import Flask, session, url_for
from werkzeug.routing import BuildError
from services.weather_service import get_cached_weather
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from extensions import db, csrf
from models import User, Tree, FertilizerSchedule
from routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Make sure the upload and report folders exist
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)

    db.init_app(app)       # connect SQLAlchemy to Flask
    csrf.init_app(app)     # turn on CSRF protection for forms
    register_blueprints(app)

    @app.context_processor
    def inject_current_user():
        """Makes 'current_user' available in every template."""
        user = None
        if session.get("user_id"):
            try:
                user = db.session.get(User, session["user_id"])
            except SQLAlchemyError:
                user = None

        return {"current_user": user}

    @app.context_processor
    def inject_helpers():
        """Helpers available in every template."""
        def safe_url(endpoint, **values):
            # Returns '#' if a page isn't built yet, so links never crash
            try:
                return url_for(endpoint, **values)
            except BuildError:
                return "#"

        header_weather = None
        if session.get("user_id"):
            header_weather, _ = get_cached_weather()

        return {
            "safe_url": safe_url,
            "header_weather": header_weather,
            "health_class": {"Healthy": "success", "Needs Care": "warning",
                             "Needs Water": "info", "Critical": "danger"},
            "status_class": {"Completed": "success", "Upcoming": "info",
                             "Due Today": "warning", "Overdue": "danger"},
        }

    return app

def create_default_data():
    """Creates the default admin account on first run only (no demo trees)."""
    if not User.query.filter_by(role="Admin").first():
        admin = User(name="Admin", email="admin@canopy360.com",
                     role="Admin", status="Active")
        admin.set_password("admin123")   # CHANGE THIS for real deployment!
        db.session.add(admin)
        db.session.commit()


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()          # creates all tables if they don't exist
            create_default_data()
        except Exception as error:
            print("\n❌ Could not connect to MySQL or set up the database.")
            print("Please check:")
            print("  1. MySQL is running")
            print("  2. The database 'canopy360' exists (CREATE DATABASE canopy360;)")
            print("  3. DB_USER and DB_PASSWORD in .env are correct\n")
            print("Technical details:", error)
            sys.exit(1)

    print("\n✅ Canopy360 is running at http://127.0.0.1:5000")
    print("   Login: admin@canopy360.com / admin123")
    print("   (Change this password before any real deployment!)\n")
    app.run(debug=True)