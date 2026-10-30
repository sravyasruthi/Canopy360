# routes/auth.py - login, logout and access-control decorators
from functools import wraps
import re
from extensions import db
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash)
from sqlalchemy.exc import SQLAlchemyError
from models import User, Tree

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 6

bp = Blueprint("auth", __name__)


def login_required(view):
    """Use @login_required above a route to protect it."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Only users with the Admin role can open the page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        if session.get("role") != "Admin":
            flash("Only administrators can open that page.", "danger")
            return redirect(url_for("dashboard.index"))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        try:
            user = User.query.filter_by(email=email).first()
        except SQLAlchemyError:
            flash("Database problem. Please check that MySQL is running.", "danger")
            return render_template("login.html")

        if user is None or not user.check_password(password):
            flash("Invalid email or password.", "danger")
        elif user.status != "Active":
            flash("This account is inactive. Contact the administrator.", "danger")
        else:
            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for("dashboard.index"))

    return render_template("login.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


# ---------- Ownership helpers: used by every page that shows trees ----------
def is_admin():
    return session.get("role") == "Admin"


def visible_trees():
    """A Tree query limited to the trees this user may see (admins see all)."""
    query = Tree.query
    if not is_admin():
        query = query.filter(Tree.user_id == session.get("user_id"))
    return query


def can_access_tree(tree):
    """True if the tree exists and belongs to this user (or the user is an admin)."""
    return tree is not None and (is_admin() or tree.user_id == session.get("user_id"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Public sign-up. New accounts always get the 'User' role."""
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    values = {}
    if request.method == "POST":
        values = request.form
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        errors = []

        if not name:
            errors.append("Please enter your name.")
        elif len(name) > 100:
            errors.append("Name must be 100 characters or fewer.")

        if not email or len(email) > 120 or not EMAIL_RE.match(email):
            errors.append("Please enter a valid email address.")

        if len(password) < MIN_PASSWORD:
            errors.append(f"Password must be at least {MIN_PASSWORD} characters.")
        elif password != confirm:
            errors.append("The password and the confirmation do not match.")

        if not errors:
            try:
                if User.query.filter_by(email=email).first():
                    errors.append("An account with this email already exists. Please log in.")
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("Database problem. Please check that MySQL is running.")

        if not errors:
            user = User(name=name, email=email, role="User", status="Active")
            user.set_password(password)    # stored hashed, never as plain text
            try:
                db.session.add(user)
                db.session.commit()
                flash("Your account was created. Please log in.", "success")
                return redirect(url_for("auth.login"))
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("Database error. Your account was not created.")

        for message in errors:
            flash(message, "danger")

    return render_template("register.html", values=values)