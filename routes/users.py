# routes/users.py - user management (Admin only)
import re
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import User
from routes.auth import admin_required

bp = Blueprint("users", __name__)

ROLES = ["Admin", "User"]
STATUSES = ["Active", "Inactive"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 6


def validate(form, user=None, require_password=True):
    """Checks the form. Returns (clean_data, list_of_error_messages)."""
    errors, data = [], {}

    data["name"] = form.get("name", "").strip()
    if not data["name"]:
        errors.append("Name is required.")
    elif len(data["name"]) > 100:
        errors.append("Name must be 100 characters or fewer.")

    data["email"] = form.get("email", "").strip().lower()
    if not data["email"]:
        errors.append("Email is required.")
    elif len(data["email"]) > 120 or not EMAIL_RE.match(data["email"]):
        errors.append("Please enter a valid email address.")
    else:
        try:
            existing = User.query.filter_by(email=data["email"]).first()
            if existing and (user is None or existing.id != user.id):
                errors.append("Another user already has that email address.")
        except SQLAlchemyError:
            db.session.rollback()
            errors.append("Could not check the email. Please try again.")

    data["role"] = form.get("role", "User")
    if data["role"] not in ROLES:
        errors.append("Please choose a valid role.")

    data["status"] = form.get("status", "Active")
    if data["status"] not in STATUSES:
        errors.append("Please choose a valid status.")

    data["password"] = form.get("password", "")
    if data["password"]:
        if len(data["password"]) < MIN_PASSWORD:
            errors.append(f"Password must be at least {MIN_PASSWORD} characters.")
    elif require_password:
        errors.append("Password is required.")

    return data, errors


def get_user_or_none(user_id):
    try:
        return db.session.get(User, user_id)
    except SQLAlchemyError:
        db.session.rollback()
        return None


@bp.route("/users", methods=["GET", "POST"])
@admin_required
def users_page():
    values = {}

    # ----- Add a new user -----
    if request.method == "POST":
        data, errors = validate(request.form, require_password=True)
        if not errors:
            user = User(name=data["name"], email=data["email"],
                        role=data["role"], status=data["status"])
            user.set_password(data["password"])   # stored hashed, never plain text
            try:
                db.session.add(user)
                db.session.commit()
                flash(f"User {user.name} was added.", "success")
                return redirect(url_for("users.users_page"))
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("Database error. The user was not saved.")
        for message in errors:
            flash(message, "danger")
        values = request.form

    try:
        users = User.query.order_by(User.id).all()
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not load users. Please check that MySQL is running.", "danger")
        users = []

    return render_template("users.html", users=users, values=values,
                           roles=ROLES, statuses=STATUSES,
                           my_id=session.get("user_id"),
                           edit_mode=False, is_self=False)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        flash("That user does not exist.", "danger")
        return redirect(url_for("users.users_page"))

    is_self = (user.id == session.get("user_id"))

    if request.method == "POST":
        data, errors = validate(request.form, user=user, require_password=False)
        if is_self:
            # An admin cannot remove their own admin rights or deactivate themselves
            data["role"], data["status"] = user.role, user.status
        if not errors:
            user.name, user.email = data["name"], data["email"]
            user.role, user.status = data["role"], data["status"]
            if data["password"]:
                user.set_password(data["password"])
            try:
                db.session.commit()
                flash(f"User {user.name} was updated.", "success")
                return redirect(url_for("users.users_page"))
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("Database error. Changes were not saved.")
        for message in errors:
            flash(message, "danger")
        return render_template("user_edit.html", user=user, values=request.form,
                               roles=ROLES, statuses=STATUSES,
                               edit_mode=True, is_self=is_self)

    values = {"name": user.name, "email": user.email,
              "role": user.role, "status": user.status}
    return render_template("user_edit.html", user=user, values=values,
                           roles=ROLES, statuses=STATUSES,
                           edit_mode=True, is_self=is_self)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = get_user_or_none(user_id)
    if user is None:
        flash("That user does not exist.", "danger")
    elif user.id == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
    else:
        try:
            if user.role == "Admin" and User.query.filter_by(role="Admin").count() <= 1:
                flash("You cannot delete the last administrator.", "danger")
            else:
                name = user.name
                db.session.delete(user)
                db.session.commit()
                flash(f"User {name} was deleted.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not delete the user. Please try again.", "danger")
    return redirect(url_for("users.users_page"))