# routes/settings.py - profile, password, app settings, API + database status
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import User, Tree
from routes.auth import login_required, is_admin, visible_trees
from routes.users import EMAIL_RE, MIN_PASSWORD
from services.weather_service import get_cached_weather

bp = Blueprint("settings", __name__)


def weather_api_status():
    """Describes the OpenWeather connection in plain words."""
    key = current_app.config.get("OPENWEATHER_API_KEY", "")
    key_set = bool(key) and key != "your_openweather_api_key"
    weather, message = get_cached_weather()

    if not weather.get("is_demo"):
        return {"label": "Connected", "css": "success", "key_set": True,
                "detail": "Live weather data is being used."}
    if not key_set:
        return {"label": "API key missing", "css": "warning", "key_set": False,
                "detail": "Add OPENWEATHER_API_KEY to your .env file and restart the app."}
    return {"label": "Not working", "css": "danger", "key_set": True,
            "detail": message or "The weather service did not respond."}


def database_status():
    """Runs a tiny query to prove the MySQL connection works."""
    cfg = current_app.config
    info = {"host": cfg.get("DB_HOST"), "port": cfg.get("DB_PORT"),
            "name": cfg.get("DB_NAME")}
    try:
        info["version"] = db.session.execute(text("SELECT VERSION()")).scalar()
        info["users"] = User.query.count()
        info["trees"] = visible_trees().count()
        info["ok"] = True
    except SQLAlchemyError as error:
        db.session.rollback()
        info["ok"] = False
        info["error"] = "Could not connect to MySQL. Check that it is running."
    return info


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    try:
        user = db.session.get(User, session["user_id"])
    except SQLAlchemyError:
        db.session.rollback()
        user = None
    if user is None:
        session.clear()
        flash("Your account could not be loaded. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    profile_values = {"name": user.name, "email": user.email}

    if request.method == "POST":
        which = request.form.get("form")

        # ---------- Update name and email ----------
        if which == "profile":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            errors = []
            if not name:
                errors.append("Name is required.")
            elif len(name) > 100:
                errors.append("Name must be 100 characters or fewer.")
            if not email or len(email) > 120 or not EMAIL_RE.match(email):
                errors.append("Please enter a valid email address.")
            else:
                try:
                    other = User.query.filter_by(email=email).first()
                    if other and other.id != user.id:
                        errors.append("Another user already has that email address.")
                except SQLAlchemyError:
                    db.session.rollback()
                    errors.append("Could not check the email. Please try again.")

            if not errors:
                user.name, user.email = name, email
                try:
                    db.session.commit()
                    flash("Profile updated.", "success")
                    return redirect(url_for("settings.settings_page"))
                except SQLAlchemyError:
                    db.session.rollback()
                    errors.append("Database error. Changes were not saved.")
            for message in errors:
                flash(message, "danger")
            profile_values = {"name": name, "email": email}

        # ---------- Change password ----------
        elif which == "password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not user.check_password(current):
                flash("Your current password is not correct.", "danger")
            elif len(new) < MIN_PASSWORD:
                flash(f"The new password must be at least {MIN_PASSWORD} characters.", "danger")
            elif new != confirm:
                flash("The new password and the confirmation do not match.", "danger")
            elif new == current:
                flash("The new password must be different from the current one.", "danger")
            else:
                user.set_password(new)
                try:
                    db.session.commit()
                    flash("Password changed successfully.", "success")
                    return redirect(url_for("settings.settings_page"))
                except SQLAlchemyError:
                    db.session.rollback()
                    flash("Database error. The password was not changed.", "danger")

    # System information is only prepared (and sent to the page) for admins
    show_system = is_admin()
    app_settings = api = dbinfo = None
    if show_system:
        cfg = current_app.config
        app_settings = [
            ("Application name", "Canopy360 - Smart Tree Care & Sustainability Platform"),
            ("Default city", cfg.get("DEFAULT_CITY")),
            ("Default map position", f"{cfg.get('DEFAULT_LAT')}, {cfg.get('DEFAULT_LON')}"),
            ("Allowed photo types", ", ".join(sorted(cfg.get("ALLOWED_EXTENSIONS", [])))),
            ("Maximum photo size", f"{cfg.get('MAX_CONTENT_LENGTH', 0) // (1024 * 1024)} MB"),
            ("Photos folder", "static/uploads"),
            ("Reports folder", "reports"),
        ]
        api = weather_api_status()
        dbinfo = database_status()

    return render_template("settings.html", user=user, values=profile_values,
                           show_system=show_system, app_settings=app_settings,
                           api=api, dbinfo=dbinfo)