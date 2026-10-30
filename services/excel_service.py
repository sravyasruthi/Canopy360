# services/excel_service.py - builds the Excel report with openpyxl (no pandas needed)
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

FILENAME = "Canopy360_Tree_Report.xlsx"


def _style_header(sheet):
    """Dark green header row with white bold text."""
    fill = PatternFill("solid", fgColor="0B3D2E")
    font = Font(bold=True, color="FFFFFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center")


def _fit_columns(sheet):
    """Make each column as wide as its longest value."""
    for column in sheet.columns:
        longest = max(len(str(c.value)) if c.value is not None else 0 for c in column)
        sheet.column_dimensions[column[0].column_letter].width = min(longest + 4, 50)


def create_excel_report(stats, rows, folder):
    """Creates Canopy360_Tree_Report.xlsx in the folder and returns its path."""
    path = os.path.join(folder, FILENAME)
    workbook = Workbook()

    # ----- Sheet 1: trees -----
    trees = workbook.active
    trees.title = "Trees"
    trees.append(["Tree Name", "Location", "Health Status", "Planting Date",
                  "Last Watered", "Carbon Estimate (kg CO2/year)"])
    for r in rows:
        trees.append([r["name"], r["location"], r["health"],
                      r["planting_date"], r["last_watered"], r["carbon"]])

    # Show dates as 25-Oct-2026
    for row in trees.iter_rows(min_row=2, min_col=4, max_col=5):
        for cell in row:
            cell.number_format = "DD-MMM-YYYY"

    # ----- Sheet 2: summary -----
    summary = workbook.create_sheet("Summary")
    summary.append(["Measure", "Value"])
    summary.append(["Total Trees", stats["total_trees"]])
    summary.append(["Total Species", stats["total_species"]])
    summary.append(["Healthy Trees", stats["healthy"]])
    summary.append(["Trees Needing Water", stats["needs_water"]])
    summary.append(["Trees Needing Care", stats["needs_care"]])
    summary.append(["Critical Trees", stats["critical"]])
    summary.append(["Estimated Carbon Absorption (kg CO2/year)", stats["carbon_total"]])

    for sheet in (trees, summary):
        _style_header(sheet)
        _fit_columns(sheet)

    workbook.save(path)
    return path