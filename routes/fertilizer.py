# routes/fertilizer.py - Fertilizer Scheduler (add, edit, delete, mark complete)
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session)
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Tree, FertilizerSchedule
from routes.auth import login_required, is_admin, visible_trees, can_access_tree

bp = Blueprint("fertilizer", __name__)

FERTILIZER_TYPES = ["Organic Compost", "NPK 19:19:19", "Vermicompost", "Bone Meal"]
STATUS_FILTERS = ["Upcoming", "Due Today", "Overdue", "Completed"]
# Overdue first, completed last
STATUS_ORDER = {"Overdue": 0, "Due Today": 1, "Upcoming": 2, "Completed": 3}


def validate(form):
    """Checks the form. Returns (clean_data, list_of_error_messages)."""
    errors = []
    data = {}

    # Tree must be chosen, must exist and must belong to this user
    tree_id = form.get("tree_id", type=int)
    if not tree_id:
        errors.append("Please choose a tree.")
    else:
        try:
            if not can_access_tree(db.session.get(Tree, tree_id)):
                errors.append("The chosen tree does not exist.")
        except SQLAlchemyError:
            db.session.rollback()
            errors.append("Could not check the tree. Please try again.")
    data["tree_id"] = tree_id

    # Fertilizer type (free text, suggestions come from the list)
    data["fertilizer_type"] = form.get("fertilizer_type", "").strip()
    if not data["fertilizer_type"]:
        errors.append("Fertilizer Type is required.")
    elif len(data["fertilizer_type"]) > 100:
        errors.append("Fertilizer Type must be 100 characters or fewer.")

    # Application date (future dates ARE allowed here, it is a schedule)
    raw_date = form.get("application_date", "").strip()
    data["application_date"] = None
    if not raw_date:
        errors.append("Application Date is required.")
    else:
        try:
            data["application_date"] = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Application Date is not a valid date.")

    data["quantity"] = form.get("quantity", "").strip()[:50] or None
    data["notes"] = form.get("notes", "").strip()[:200] or None
    return data, errors


def schedule_to_values(item):
    """Plain strings used to pre-fill the edit form."""
    return {
        "tree_id": str(item.tree_id),
        "fertilizer_type": item.fertilizer_type,
        "application_date": item.application_date.isoformat(),
        "quantity": item.quantity or "",
        "notes": item.notes or "",
    }


def get_schedule_or_none(schedule_id):
    """Returns the schedule only if its tree belongs to this user."""
    try:
        item = db.session.get(FertilizerSchedule, schedule_id)
        return item if item and can_access_tree(item.tree) else None
    except SQLAlchemyError:
        db.session.rollback()
        return None


@bp.route("/fertilizer", methods=["GET", "POST"])
@login_required
def scheduler():
    values = {}

    # ----- Add a new schedule -----
    if request.method == "POST":
        data, errors = validate(request.form)
        if not errors:
            try:
                db.session.add(FertilizerSchedule(**data))
                db.session.commit()
                flash("Fertilizer schedule added.", "success")
                return redirect(url_for("fertilizer.scheduler"))
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("Database error. The schedule was not saved.")
        for message in errors:
            flash(message, "danger")
        values = request.form

    # ----- Load data for the page -----
    try:
        trees = visible_trees().order_by(Tree.tree_name).all()
        schedule_query = FertilizerSchedule.query.join(Tree)
        if not is_admin():
            schedule_query = schedule_query.filter(Tree.user_id == session["user_id"])
        schedules = schedule_query.order_by(FertilizerSchedule.application_date).all()
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not load data. Please check that MySQL is running.", "danger")
        trees, schedules = [], []

    # Count each status, then apply the optional filter
    counts = {name: 0 for name in STATUS_FILTERS}
    for item in schedules:
        counts[item.status] = counts.get(item.status, 0) + 1

    selected = request.args.get("status", "")
    if selected in STATUS_FILTERS:
        schedules = [s for s in schedules if s.status == selected]
    schedules.sort(key=lambda s: (STATUS_ORDER.get(s.status, 9), s.application_date))

    return render_template("fertilizer.html", trees=trees, schedules=schedules,
                           counts=counts, selected=selected, values=values,
                           fertilizer_types=FERTILIZER_TYPES,
                           status_filters=STATUS_FILTERS, edit_mode=False)


@bp.route("/fertilizer/<int:schedule_id>/edit", methods=["GET", "POST"])
@login_required
def edit_schedule(schedule_id):
    item = get_schedule_or_none(schedule_id)
    if item is None:
        flash("That schedule does not exist.", "danger")
        return redirect(url_for("fertilizer.scheduler"))

    try:
        trees = visible_trees().order_by(Tree.tree_name).all()
    except SQLAlchemyError:
        db.session.rollback()
        trees = []

    if request.method == "POST":
        data, errors = validate(request.form)
        if not errors:
            for key, value in data.items():
                setattr(item, key, value)
            try:
                db.session.commit()
                flash("Fertilizer schedule updated.", "success")
                return redirect(url_for("fertilizer.scheduler"))
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("Database error. Changes were not saved.")
        for message in errors:
            flash(message, "danger")
        return render_template("fertilizer_edit.html", trees=trees, values=request.form,
                               fertilizer_types=FERTILIZER_TYPES, edit_mode=True)

    return render_template("fertilizer_edit.html", trees=trees,
                           values=schedule_to_values(item),
                           fertilizer_types=FERTILIZER_TYPES, edit_mode=True)


@bp.route("/fertilizer/<int:schedule_id>/complete", methods=["POST"])
@login_required
def complete_schedule(schedule_id):
    item = get_schedule_or_none(schedule_id)
    if item is None:
        flash("That schedule does not exist.", "danger")
    else:
        try:
            item.completed = True
            db.session.commit()
            flash(f"Marked complete: {item.fertilizer_type} for {item.tree.tree_name}.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not update the schedule. Please try again.", "danger")
    return redirect(url_for("fertilizer.scheduler"))


@bp.route("/fertilizer/<int:schedule_id>/delete", methods=["POST"])
@login_required
def delete_schedule(schedule_id):
    item = get_schedule_or_none(schedule_id)
    if item is None:
        flash("That schedule does not exist.", "danger")
    else:
        try:
            db.session.delete(item)
            db.session.commit()
            flash("Fertilizer schedule deleted.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash("Could not delete the schedule. Please try again.", "danger")
    return redirect(url_for("fertilizer.scheduler"))