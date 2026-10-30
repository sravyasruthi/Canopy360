# routes/home.py - public landing page (no login needed)
from flask import Blueprint, render_template, session

bp = Blueprint("home", __name__)


@bp.route("/")
def landing():
    return render_template("home.html", logged_in=bool(session.get("user_id")))