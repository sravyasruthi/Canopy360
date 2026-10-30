# routes/reports.py - Reports page, PDF download, Excel download
from datetime import date

from flask import (Blueprint, render_template, redirect, url_for,
                   flash, send_file, current_app)
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Tree
from routes.auth import login_required, visible_trees
from services.report_data import collect_report_data
from services.pdf_service import create_pdf_report
from services.excel_service import create_excel_report
from services.carbon_service import tree_yearly_co2
from services.chart_service import doughnut_chart, bar_chart, line_chart_labels

bp = Blueprint("reports", __name__)

HEALTH_COLORS = {"Healthy": "#1b9a55", "Needs Care": "#f0a020",
                 "Needs Water": "#2f7be0", "Critical": "#e5484d"}
SPECIES_COLORS = ["#1b9a55", "#2f7be0", "#f0a020", "#8e5bd9",
                  "#e5484d", "#138a7a", "#e2832b", "#6b7c73"]


def load_trees():
    """Returns all trees, or None when the database cannot be reached."""
    try:
        return visible_trees().order_by(Tree.tree_name).all()
    except SQLAlchemyError:
        db.session.rollback()
        return None


def trees_added_per_month(trees, months=6):
    """Counts trees by the month they were added (last 6 months)."""
    today = date.today()
    labels, counts = [], []
    for back in range(months - 1, -1, -1):
        month = today.month - back
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        labels.append(date(year, month, 1).strftime("%b %Y"))
        counts.append(sum(1 for t in trees
                          if t.created_at
                          and t.created_at.year == year
                          and t.created_at.month == month))
    return labels, counts


def carbon_by_planting_year(trees):
    """Cumulative yearly CO2 of all trees planted up to each year."""
    dated = [t for t in trees if t.planting_date]
    if not dated:
        return [], []
    first = min(t.planting_date.year for t in dated)
    labels, values = [], []
    for year in range(first, date.today().year + 1):
        total = sum(tree_yearly_co2(t) for t in dated if t.planting_date.year <= year)
        labels.append(str(year))
        values.append(round(total, 2))
    return labels, values


@bp.route("/reports")
@login_required
def reports_page():
    trees = load_trees()
    if trees is None:
        flash("Could not load data. Please check that MySQL is running.", "danger")
        trees = []

    stats, _rows = collect_report_data(trees)

    # Chart 1: tree health
    health_names = list(HEALTH_COLORS)
    health_chart = doughnut_chart(
        health_names,
        [sum(1 for t in trees if t.health_status == n) for n in health_names],
        [HEALTH_COLORS[n] for n in health_names])

    # Chart 2: species distribution
    species_counts = {}
    for t in trees:
        key = t.species if t.species and t.species != "Unknown" else "Other"
        species_counts[key] = species_counts.get(key, 0) + 1
    names = sorted(species_counts, key=species_counts.get, reverse=True)
    species_chart = doughnut_chart(
        [n.split("(")[0][:22] for n in names],
        [species_counts[n] for n in names],
        [SPECIES_COLORS[i % len(SPECIES_COLORS)] for i in range(len(names))])

    # Chart 3: carbon absorption over time
    years, totals = carbon_by_planting_year(trees)
    carbon_chart = line_chart_labels(years, totals, ylabel="kg CO2 / year")

    # Chart 4: trees added per month
    month_labels, month_counts = trees_added_per_month(trees)
    monthly_chart = (bar_chart(month_labels, month_counts, color="#2f7be0",
                               ylabel="Trees added") if trees else None)

    return render_template("reports.html", stats=stats,
                           health_chart=health_chart, species_chart=species_chart,
                           carbon_chart=carbon_chart, monthly_chart=monthly_chart)


@bp.route("/reports/pdf")
@login_required
def download_pdf():
    trees = load_trees()
    if trees is None:
        flash("Could not load data. Please check that MySQL is running.", "danger")
        return redirect(url_for("reports.reports_page"))
    try:
        stats, rows = collect_report_data(trees)
        path = create_pdf_report(stats, rows, current_app.config["REPORTS_FOLDER"])
        return send_file(path, as_attachment=True,
                         download_name="Canopy360_Tree_Report.pdf",
                         mimetype="application/pdf")
    except Exception as error:
        flash(f"The PDF report could not be created: {error}", "danger")
        return redirect(url_for("reports.reports_page"))


@bp.route("/reports/excel")
@login_required
def download_excel():
    trees = load_trees()
    if trees is None:
        flash("Could not load data. Please check that MySQL is running.", "danger")
        return redirect(url_for("reports.reports_page"))
    try:
        stats, rows = collect_report_data(trees)
        path = create_excel_report(stats, rows, current_app.config["REPORTS_FOLDER"])
        return send_file(path, as_attachment=True,
                         download_name="Canopy360_Tree_Report.xlsx")
    except Exception as error:
        flash(f"The Excel report could not be created: {error}", "danger")
        return redirect(url_for("reports.reports_page"))