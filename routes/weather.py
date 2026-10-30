# routes/weather.py - Weather & Watering page
from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, session
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Tree, WateringRecord
from routes.auth import login_required, is_admin, visible_trees, can_access_tree
from services.weather_service import get_cached_weather
from services.watering_service import (overall_recommendation,
                                       watering_status, weekly_watering_need)

bp = Blueprint("weather", __name__)

# Sort order so trees that need water appear first
STATUS_ORDER = {"Needs Water": 0, "Water Soon": 1, "Watered": 2}


@bp.route("/weather")
@login_required
def weather_page():
    weather, weather_message = get_cached_weather()
    recommendation = overall_recommendation(weather)

    try:
        trees = visible_trees().order_by(Tree.tree_name).all()
        history_query = WateringRecord.query.join(Tree)
        if not is_admin():
               history_query = history_query.filter(Tree.user_id == session["user_id"])
        history = history_query.order_by(WateringRecord.id.desc()).limit(8).all()
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not load trees. Please check that MySQL is running.", "danger")
        trees, history = [], []

    today = date.today()
    rows = []
    for tree in trees:
        status_text, status_class = watering_status(tree, weather)
        times, _ = weekly_watering_need(weather, tree.species, tree.tree_age)
        gap_days = max(1, round(7 / times))      # days between waterings

        # Next watering = last watered + gap (never earlier than today)
        if tree.last_watered:
            next_date = max(tree.last_watered + timedelta(days=gap_days), today)
        else:
            next_date = today

        rows.append({"tree": tree, "status": status_text, "css": status_class,
                     "times": times, "next_date": next_date})

    rows.sort(key=lambda r: STATUS_ORDER.get(r["status"], 3))

    return render_template("weather.html", weather=weather,
                           weather_message=weather_message,
                           recommendation=recommendation,
                           rows=rows, history=history)


@bp.route("/weather/water/<int:tree_id>", methods=["POST"])
@login_required
def mark_watered(tree_id):
    """Records that a tree was watered today."""
    try:
        tree = db.session.get(Tree, tree_id)
        if not can_access_tree(tree):
            flash("That tree does not exist.", "danger")
            return redirect(url_for("weather.weather_page"))

        tree.last_watered = date.today()
        if tree.health_status == "Needs Water":
            tree.health_status = "Healthy"
        db.session.add(WateringRecord(tree_id=tree.id, watered_on=date.today(),
                                      amount_litres=10.0))
        db.session.commit()
        flash(f"{tree.tree_name} marked as watered today.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not save the watering record. Please try again.", "danger")
    return redirect(url_for("weather.weather_page"))