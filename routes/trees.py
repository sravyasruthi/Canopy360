# routes/trees.py - add, list, view, edit, delete trees + map page
import os
import uuid
from datetime import date, datetime, timedelta

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, session, jsonify)
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from PIL import Image
from werkzeug.utils import secure_filename

from extensions import db
from models import Tree, FertilizerSchedule
from routes.auth import login_required, visible_trees, can_access_tree
from services.weather_service import get_cached_weather
from services.watering_service import watering_status, weekly_watering_need
from services.carbon_service import estimate_co2, estimate_size, DISCLAIMER
from services.map_service import build_tree_map
from services.species_service import find_species
from services.geocode_service import find_coordinates

bp = Blueprint("trees", __name__)

HEALTH_OPTIONS = ["Healthy", "Needs Care", "Needs Water", "Critical"]
SORT_COLUMNS = {
    "tree_name": Tree.tree_name,
    "location": Tree.location,
    "health_status": Tree.health_status,
    "last_watered": Tree.last_watered,
    "planting_date": Tree.planting_date,
}
PER_PAGE = 8

# Rough age stages for people who do not know the planting date: (key, text, age in years)
AGE_STAGES = [
    ("young", "Young tree - planted in the last 1 to 3 years (about 2 years)", 2),
    ("growing", "Growing tree - about 3 to 10 years old (about 6 years)", 6),
    ("mature", "Mature tree - about 10 to 30 years old (about 20 years)", 20),
    ("old", "Old tree - more than 30 years old (about 40 years)", 40),
]


@bp.app_context_processor
def inject_age_stages():
    """Makes the stage list available to the Add/Edit form."""
    return {"age_stages": AGE_STAGES}


# ---------------------------------------------------------------- helpers
def read_number(form, key, label, cast, low, high, required, errors):
    """Reads one numeric field and records an error message if invalid."""
    raw = form.get(key, "").strip()
    if raw == "":
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        value = cast(raw)
    except ValueError:
        errors.append(f"{label} must be a valid number.")
        return None
    if value < low or value > high:
        errors.append(f"{label} must be between {low} and {high}.")
        return None
    return value


def read_date(form, key, label, required, errors):
    """Reads one date field (YYYY-MM-DD). Future dates are not allowed."""
    raw = form.get(key, "").strip()
    if raw == "":
        if required:
            errors.append(f"{label} is required.")
        return None
    try:
        value = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{label} is not a valid date.")
        return None
    if value > date.today():
        errors.append(f"{label} cannot be in the future.")
        return None
    return value


def validate_form(form):
    """Checks every field. Returns (clean_data, list_of_error_messages)."""
    errors = []
    data = {}

    data["tree_name"] = form.get("tree_name", "").strip()
    if not data["tree_name"]:
        errors.append("Tree Name is required.")
    elif len(data["tree_name"]) > 100:
        errors.append("Tree Name must be 100 characters or fewer.")

    # If the species is empty, work it out from the tree name (e.g. "Neem Tree")
    data["species"] = form.get("species", "").strip()[:100]
    if not data["species"] or data["species"].lower() == "unknown":
        data["species"] = find_species(data["tree_name"]) or "Unknown"

    data["location"] = form.get("location", "").strip()
    if not data["location"]:
        errors.append("Location is required.")
    elif len(data["location"]) > 200:
        errors.append("Location must be 200 characters or fewer.")

    data["latitude"] = read_number(form, "latitude", "Latitude", float, -90, 90, False, errors)
    data["longitude"] = read_number(form, "longitude", "Longitude", float, -180, 180, False, errors)
    if (data["latitude"] is None) != (data["longitude"] is None):
        errors.append("Enter both Latitude and Longitude, or leave both empty.")

    # How is the age known? A planting date, an approximate age, or a rough stage
    age_source = form.get("age_source", "date")
    data["age_estimated"] = age_source in ("years", "stage")
    data["planting_date"] = None
    data["tree_age"] = None
    today = date.today()

    if age_source == "years":
        age = read_number(form, "approx_age", "Approximate age", int, 0, 500, True, errors)
        if age is not None:
            data["tree_age"] = age
    elif age_source == "stage":
        chosen = {key: years for key, _text, years in AGE_STAGES}.get(form.get("age_stage", ""))
        if chosen is None:
            errors.append("Please choose a rough age stage.")
        else:
            data["tree_age"] = chosen
    else:
        data["age_estimated"] = False
        planted = read_date(form, "planting_date", "Planting Date", True, errors)
        if planted:
            data["planting_date"] = planted
            years = today.year - planted.year - ((today.month, today.day) < (planted.month, planted.day))
            data["tree_age"] = max(years, 0)

    # Planting date unknown: work backwards from the age (approximate)
    if data["planting_date"] is None and data["tree_age"] is not None:
        data["planting_date"] = today - timedelta(days=int(data["tree_age"] * 365.25))

    height = read_number(form, "height_m", "Height", float, 0, 150, False, errors)
    diameter = read_number(form, "diameter_cm", "Diameter", float, 0, 1000, False, errors)
    # If the user does not know the size, estimate it from age and species
    est_diameter, est_height = estimate_size(data["tree_age"] or 1, data["species"])
    data["height_m"] = height if height is not None else est_height
    data["diameter_cm"] = diameter if diameter is not None else est_diameter

    data["health_status"] = form.get("health_status", "")
    if data["health_status"] not in HEALTH_OPTIONS:
        errors.append("Please choose a valid Health Status.")

    data["watering_frequency"] = read_number(
        form, "watering_frequency", "Watering Frequency", int, 1, 7, True, errors)
    data["last_watered"] = read_date(form, "last_watered", "Last Watered Date", False, errors)
    data["notes"] = form.get("notes", "").strip()[:2000] or None
    return data, errors


def apply_data(tree, data):
    """Copies the validated values onto a Tree object."""
    for key, value in data.items():
        setattr(tree, key, value)


def tree_to_values(tree):
    """Turns a Tree into plain strings so the edit form can be pre-filled."""
    def text(value):
        return "" if value is None else str(value)
    return {
        "tree_name": tree.tree_name, "species": text(tree.species),
        "location": tree.location,
        "latitude": text(tree.latitude), "longitude": text(tree.longitude),
        "planting_date": tree.planting_date.isoformat() if tree.planting_date else "",
        "tree_age": text(tree.tree_age), "height_m": text(tree.height_m),
        "age_source": "years" if tree.age_estimated else "date",
        "approx_age": text(tree.tree_age),
        "diameter_cm": text(tree.diameter_cm),
        "health_status": tree.health_status,
        "watering_frequency": text(tree.watering_frequency),
        "last_watered": tree.last_watered.isoformat() if tree.last_watered else "",
        "notes": text(tree.notes),
    }


def save_photo(file_storage):
    """
    Validates, resizes and saves an uploaded photo.
    Returns (filename, error_message). Both are None if no file was chosen.
    """
    if not file_storage or file_storage.filename == "":
        return None, None

    name = file_storage.filename
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return None, "Photo must be a JPG, JPEG, PNG or WEBP image."

    # Pillow opens the file to prove it is really an image (not a renamed file)
    try:
        image = Image.open(file_storage.stream)
        image.load()
    except Exception:
        return None, "The uploaded file is not a valid image."

    image.thumbnail((1200, 1200))   # shrink large photos, keep proportions
    base = secure_filename(os.path.splitext(name)[0])[:30] or "tree"
    filename = f"{base}_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    try:
        if ext in ("jpg", "jpeg"):
            image.convert("RGB").save(path, "JPEG", quality=85)
        elif ext == "png":
            image.save(path, "PNG")
        else:
            image.save(path, "WEBP", quality=85)
    except OSError:
        return None, "The photo could not be saved. Please try again."
    return filename, None


def remove_photo(filename):
    """Deletes a photo file from static/uploads (ignores problems)."""
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def get_tree_or_none(tree_id):
    try:
        tree = db.session.get(Tree, tree_id)
           # Trees of other users look like they do not exist
        return tree if can_access_tree(tree) else None
    except SQLAlchemyError:
        db.session.rollback()
        return None


# ---------------------------------------------------------------- error handler
@bp.app_errorhandler(413)
def file_too_large(error):
    flash("That file is too large. The maximum photo size is 5 MB.", "danger")
    return redirect(request.referrer or url_for("trees.all_trees"))

def auto_locate(data):
    """If no GPS was entered, try to find it from the location text."""
    if data["latitude"] is None and data["longitude"] is None:
        coords = find_coordinates(data["location"])
        if coords:
            data["latitude"], data["longitude"] = coords
            flash("Map position was found automatically from the location.", "info")

@bp.route("/trees/species-lookup")
@login_required
def species_lookup():
    """Used by the Add/Edit form to fill the species while typing the name."""
    name = request.args.get("name", "")
    return jsonify({"species": find_species(name) or ""})

# ---------------------------------------------------------------- routes
@bp.route("/trees")
@login_required
def all_trees():
    q = request.args.get("q", "").strip()
    health = request.args.get("health", "")
    sort = request.args.get("sort", "tree_name")
    order = request.args.get("order", "asc")
    page = request.args.get("page", 1, type=int)

    if sort not in SORT_COLUMNS:
        sort = "tree_name"
    if order not in ("asc", "desc"):
        order = "asc"

    query = visible_trees()
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Tree.tree_name.ilike(like),
                                 Tree.location.ilike(like),
                                 Tree.species.ilike(like)))
    if health in HEALTH_OPTIONS:
        query = query.filter(Tree.health_status == health)
    column = SORT_COLUMNS[sort]
    query = query.order_by(column.desc() if order == "desc" else column.asc())

    try:
        pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not load trees. Please check that MySQL is running.", "danger")
        return redirect(url_for("dashboard.index"))

    return render_template("trees/all.html", pagination=pagination, trees=pagination.items,
                           q=q, health=health, sort=sort, order=order,
                           health_options=HEALTH_OPTIONS)


@bp.route("/trees/add", methods=["GET", "POST"])
@login_required
def add_tree():
    if request.method == "POST":
        data, errors = validate_form(request.form)
        if not errors:
            auto_locate(data)
        filename = None
        if not errors:
            filename, photo_error = save_photo(request.files.get("photo"))
            if photo_error:
                errors.append(photo_error)

        if not errors:
            tree = Tree()
            apply_data(tree, data)
            tree.photo = filename
            tree.user_id = session["user_id"]
            try:
                db.session.add(tree)
                db.session.commit()
                flash(f"{tree.tree_name} was added successfully.", "success")
                return redirect(url_for("trees.view_tree", tree_id=tree.id))
            except SQLAlchemyError:
                db.session.rollback()
                remove_photo(filename)
                errors.append("Database error. The tree was not saved.")

        for message in errors:
            flash(message, "danger")
        return render_template("trees/add.html", values=request.form,
                               health_options=HEALTH_OPTIONS, edit_mode=False)

    defaults = {"health_status": "Healthy", "watering_frequency": "3"}
    return render_template("trees/add.html", values=defaults,
                           health_options=HEALTH_OPTIONS, edit_mode=False)


@bp.route("/trees/<int:tree_id>")
@login_required
def view_tree(tree_id):
    tree = get_tree_or_none(tree_id)
    if tree is None:
        flash("That tree does not exist.", "danger")
        return redirect(url_for("trees.all_trees"))

    weather, weather_message = get_cached_weather()
    water_text, water_class = watering_status(tree, weather)
    times, reasons = weekly_watering_need(weather, tree.species, tree.tree_age)
    carbon = estimate_co2(tree.tree_age, tree.diameter_cm, tree.height_m)

    next_fert = (FertilizerSchedule.query
                 .filter_by(tree_id=tree.id, completed=False)
                 .order_by(FertilizerSchedule.application_date).first())

    try:
        map_html = build_tree_map([tree], zoom=15) if tree.latitude is not None else None
    except Exception:
        map_html = None

    return render_template("trees/details.html", tree=tree, carbon=carbon,
                           carbon_note=DISCLAIMER, water_text=water_text,
                           water_class=water_class, times=times,
                           next_fert=next_fert, map_html=map_html)


@bp.route("/trees/<int:tree_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tree(tree_id):
    tree = get_tree_or_none(tree_id)
    if tree is None:
        flash("That tree does not exist.", "danger")
        return redirect(url_for("trees.all_trees"))

    if request.method == "POST":
        data, errors = validate_form(request.form)
        if not errors:
            auto_locate(data)
        new_photo = None
        if not errors:
            new_photo, photo_error = save_photo(request.files.get("photo"))
            if photo_error:
                errors.append(photo_error)

        if not errors:
            old_photo = tree.photo
            apply_data(tree, data)
            if new_photo:
                tree.photo = new_photo
            try:
                db.session.commit()
                if new_photo:
                    remove_photo(old_photo)
                flash(f"{tree.tree_name} was updated.", "success")
                return redirect(url_for("trees.view_tree", tree_id=tree.id))
            except SQLAlchemyError:
                db.session.rollback()
                remove_photo(new_photo)
                errors.append("Database error. Changes were not saved.")

        for message in errors:
            flash(message, "danger")
        return render_template("trees/edit.html", tree=tree, values=request.form,
                               health_options=HEALTH_OPTIONS, edit_mode=True)

    return render_template("trees/edit.html", tree=tree, values=tree_to_values(tree),
                           health_options=HEALTH_OPTIONS, edit_mode=True)


@bp.route("/trees/<int:tree_id>/delete", methods=["POST"])
@login_required
def delete_tree(tree_id):
    tree = get_tree_or_none(tree_id)
    if tree is None:
        flash("That tree does not exist.", "danger")
        return redirect(url_for("trees.all_trees"))

    name, photo = tree.tree_name, tree.photo
    try:
        db.session.delete(tree)   # also deletes its related records
        db.session.commit()
        remove_photo(photo)
        flash(f"{name} was deleted.", "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not delete the tree. Please try again.", "danger")
    return redirect(url_for("trees.all_trees"))


@bp.route("/map")
@login_required
def map_view():
    trees, map_html = [], None
    try:
        trees = visible_trees().order_by(Tree.tree_name).all()
        map_html = build_tree_map(trees, zoom=12)
    except Exception:
        db.session.rollback()
        flash("The map could not be loaded.", "danger")

    # Trees without a saved GPS position cannot be drawn
    missing = [t for t in trees if t.latitude is None or t.longitude is None]
    return render_template("trees/map.html", map_html=map_html, count=len(trees),
                           on_map=len(trees) - len(missing), missing=missing)