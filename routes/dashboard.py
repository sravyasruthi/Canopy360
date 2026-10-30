# routes/dashboard.py - the main dashboard page
from datetime import date
from flask import Blueprint, redirect, url_for, render_template, flash, session
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Tree, FertilizerSchedule
from routes.auth import login_required, is_admin, visible_trees
from services.weather_service import get_cached_weather
from services.watering_service import overall_recommendation, watering_status
from services.carbon_service import tree_yearly_co2, total_yearly_co2, DISCLAIMER
from services.chart_service import bar_chart
from services.map_service import build_tree_map

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def index():
    # 1. Load data from MySQL (the page still opens if this fails)
    try:
        trees = visible_trees().order_by(Tree.id).all()
        recent_trees = visible_trees().order_by(Tree.id.desc()).limit(5).all()
        upcoming_query = (FertilizerSchedule.query.join(Tree)
                             .filter(FertilizerSchedule.completed.is_(False)))
        if not is_admin():
               upcoming_query = upcoming_query.filter(Tree.user_id == session["user_id"])
        upcoming = (upcoming_query
                       .order_by(FertilizerSchedule.application_date)
                       .limit(5).all())
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not load data. Please check that MySQL is running.", "danger")
        trees, recent_trees, upcoming = [], [], []

    # 2. Weather and watering advice
    weather, weather_message = get_cached_weather()
    recommendation = overall_recommendation(weather)

    # 3. Statistic cards (all calculated from the database)
    today = date.today()
    species_count = len({t.species for t in trees if t.species and t.species != "Unknown"})
    need_watering = sum(
        1 for t in trees
        if t.health_status == "Needs Water"
        or watering_status(t, weather)[0] == "Needs Water")
    # "Under care this week" = trees watered in the last 7 days
    under_care = sum(
        1 for t in trees
        if t.last_watered and (today - t.last_watered).days <= 7)

    # 4. Interactive map
    try:
        map_html = build_tree_map(trees)
    except Exception:
        map_html = None

    # 5. Carbon chart (yearly CO2 for the biggest absorbers)
    ranked = sorted(trees, key=tree_yearly_co2, reverse=True)[:8]
    carbon_chart = bar_chart(
        [t.tree_name.split()[0] for t in ranked],
        [tree_yearly_co2(t) for t in ranked],
        ylabel="kg CO2 / year")

    return render_template(
        "dashboard.html",
        total_trees=len(trees), species_count=species_count,
        need_watering=need_watering, under_care=under_care,
        weather=weather, weather_message=weather_message,
        recommendation=recommendation, map_html=map_html,
        carbon_chart=carbon_chart, total_carbon=total_yearly_co2(trees),
        carbon_note=DISCLAIMER,
        recent_trees=recent_trees, upcoming=upcoming)