# routes/carbon.py - Carbon Calculator page (size can be estimated)
import math
from datetime import date
from flask import Blueprint, render_template, request, flash, session
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Tree, CarbonRecord
from routes.auth import login_required, is_admin, visible_trees, can_access_tree
from routes.trees import read_number
from services.carbon_service import (estimate_co2, estimate_size, growth_curve,
                                     total_yearly_co2, tree_yearly_co2, DISCLAIMER)
from services.chart_service import bar_chart, line_chart

bp = Blueprint("carbon", __name__)

# (value, text shown). Numbers are the diameter in cm / height in metres.
TRUNK_CHOICES = [
    ("estimate", "Not sure - estimate from age and species"),
    ("8", "Thin - about as thick as my wrist or arm (about 8 cm)"),
    ("20", "Thigh-thick (about 20 cm)"),
    ("35", "Waist-thick (about 35 cm)"),
    ("60", "Wider than I can hug with both arms (about 60 cm)"),
    ("100", "Very large, needs several people to hug it (about 100 cm)"),
    ("circumference", "I measured around the trunk (cm)"),
    ("diameter", "I know the trunk diameter (cm)"),
]
HEIGHT_CHOICES = [
    ("estimate", "Not sure - estimate from age and species"),
    ("2", "Shorter than a person (about 2 m)"),
    ("4", "About as tall as a single-storey house (about 4 m)"),
    ("7", "About as tall as a two-storey building (about 7 m)"),
    ("10", "About as tall as a three-storey building (about 10 m)"),
    ("15", "Taller than a four-storey building (about 15 m)"),
    ("exact", "I know the height (m)"),
]


def recent_records():
    """Latest saved results (only for the trees this user may see)."""
    query = CarbonRecord.query.join(Tree)
    if not is_admin():
        query = query.filter(Tree.user_id == session["user_id"])
    return query.order_by(CarbonRecord.id.desc()).limit(6).all()


def resolve_size(form, age, species, errors):
    """
    Works out the trunk diameter (cm) and height (m) to use.
    Returns (diameter, height, notes). Problems are added to 'errors'.
    """
    est_d, est_h = estimate_size(age, species)
    notes = []
    diameter = height = None

    # ----- trunk -----
    trunk = form.get("trunk", "estimate")
    if trunk not in dict(TRUNK_CHOICES):
        errors.append("Please choose a valid trunk option.")
    elif trunk == "estimate":
        diameter = est_d
        notes.append(f"Trunk diameter was estimated from age and species: about {est_d} cm.")
    elif trunk == "diameter":
        diameter = read_number(form, "trunk_value", "Trunk diameter",
                               float, 0.5, 1000, True, errors)
    elif trunk == "circumference":
        circumference = read_number(form, "trunk_value", "Trunk circumference",
                                    float, 1.5, 3000, True, errors)
        if circumference is not None:
            diameter = round(circumference / math.pi, 1)
            notes.append(f"Diameter worked out from the circumference "
                         f"({circumference} cm / 3.14 = about {diameter} cm).")
    else:
        diameter = float(trunk)   # one of the preset sizes
        notes.append(f"Trunk diameter taken from your choice: about {diameter:g} cm.")

    # ----- height -----
    height_choice = form.get("height", "estimate")
    if height_choice not in dict(HEIGHT_CHOICES):
        errors.append("Please choose a valid height option.")
    elif height_choice == "estimate":
        height = est_h
        notes.append(f"Height was estimated from age and species: about {est_h} m.")
    elif height_choice == "exact":
        height = read_number(form, "height_value", "Tree height",
                             float, 0.3, 150, True, errors)
    else:
        height = float(height_choice)
        notes.append(f"Height taken from your choice: about {height:g} m.")

    return diameter, height, notes


@bp.route("/carbon", methods=["GET", "POST"])
@login_required
def calculator():
    try:
        trees = visible_trees().order_by(Tree.tree_name).all()
        recent = recent_records()
    except SQLAlchemyError:
        db.session.rollback()
        flash("Could not load data. Please check that MySQL is running.", "danger")
        trees, recent = [], []

    values = {}
    result = None
    growth_chart = None
    used_d = used_h = None
    notes = []

    if request.method == "POST":
        values = request.form
        errors = []
        age = read_number(request.form, "age", "Tree Age", int, 1, 500, True, errors)
        tree_id = request.form.get("tree_id", type=int)

        # Species: typed by the user, or taken from the chosen tree
        species = request.form.get("species", "").strip()
        if not species and tree_id:
            chosen = next((t for t in trees if t.id == tree_id), None)
            species = chosen.species if chosen else ""

        diameter, height, notes = resolve_size(request.form, age or 1, species, errors)

        if errors:
            for message in errors:
                flash(message, "danger")
            notes = []
        else:
            used_d, used_h = diameter, height
            result = estimate_co2(age, diameter, height)
            points = growth_curve(age, diameter, height)
            growth_chart = line_chart([p[0] for p in points], [p[1] for p in points],
                                      xlabel="Tree age (years)", ylabel="kg CO2 / year")

            # "Calculate & Save Result" stores the estimate for the chosen tree
            if request.form.get("action") == "save":
                if not tree_id:
                    flash("Choose a tree from the list to save this result.", "warning")
                else:
                    try:
                        tree = db.session.get(Tree, tree_id)
                        if not can_access_tree(tree):
                            flash("That tree does not exist.", "danger")
                        else:
                            db.session.add(CarbonRecord(
                                tree_id=tree.id, recorded_on=date.today(),
                                co2_kg_per_year=result["yearly_co2_kg"]))
                            db.session.commit()
                            flash(f"Result saved for {tree.tree_name}.", "success")
                            recent = recent_records()
                    except SQLAlchemyError:
                        db.session.rollback()
                        flash("Could not save the result. Please try again.", "danger")

    elif request.args.get("tree_id", type=int):
        # Opened with ?tree_id=3 : pre-fill the form from that tree
        wanted = request.args.get("tree_id", type=int)
        tree = next((t for t in trees if t.id == wanted), None)
        if tree:
            values = {"tree_id": str(tree.id), "age": str(max(tree.tree_age, 1)),
                      "species": tree.species or "",
                      "trunk": "diameter", "trunk_value": str(tree.diameter_cm),
                      "height": "exact", "height_value": str(tree.height_m)}

    # Totals for every tree this user can see
    yearly = total_yearly_co2(trees)
    stored = round(sum(estimate_co2(t.tree_age, t.diameter_cm, t.height_m)["total_co2_kg"]
                       for t in trees), 2)
    ranked = sorted(trees, key=tree_yearly_co2, reverse=True)[:10]
    all_chart = bar_chart([t.tree_name.split()[0] for t in ranked],
                          [tree_yearly_co2(t) for t in ranked], ylabel="kg CO2 / year")

    return render_template("carbon.html", trees=trees, values=values, result=result,
                           growth_chart=growth_chart, all_chart=all_chart,
                           used_d=used_d, used_h=used_h, notes=notes,
                           trunk_choices=TRUNK_CHOICES, height_choices=HEIGHT_CHOICES,
                           total_yearly=yearly, total_monthly=round(yearly / 12, 2),
                           total_stored=stored, recent=recent, note=DISCLAIMER)