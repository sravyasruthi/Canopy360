# services/pdf_service.py - builds the PDF report with ReportLab
import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

GREEN = colors.HexColor("#0b3d2e")
LIGHT = colors.HexColor("#e6f6ec")


def _date(value):
    return value.strftime("%d %b %Y") if value else "-"


def create_pdf_report(stats, rows, folder):
    """Creates the PDF in the given folder and returns its full file path."""
    filename = f"Canopy360_Tree_Report_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    path = os.path.join(folder, filename)

    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title="Canopy360 Tree Management Report")

    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title2", parent=styles["Title"], textColor=GREEN, fontSize=24)
    subtitle = ParagraphStyle("Sub", parent=styles["Heading2"], textColor=GREEN)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=10)
    cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=11)

    story = [
        Paragraph("Canopy360", title),
        Paragraph("Tree Management Report", subtitle),
        Paragraph(f"Generated on {datetime.now():%d %b %Y, %I:%M %p}", small),
        Spacer(1, 8 * mm),
    ]

    # ---- Summary table ----
    summary = [
        ["Total Trees", stats["total_trees"]],
        ["Total Species", stats["total_species"]],
        ["Healthy Trees", stats["healthy"]],
        ["Trees Needing Water", stats["needs_water"]],
        ["Trees Needing Care", stats["needs_care"]],
        ["Critical Trees", stats["critical"]],
        ["Estimated Carbon Absorption", f"{stats['carbon_total']} kg CO2 / year"],
    ]
    summary_table = Table(summary, colWidths=[70 * mm, 60 * mm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfe0d4")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [summary_table, Spacer(1, 8 * mm),
              Paragraph("Tree Details", subtitle)]

    # ---- Tree table (text is wrapped with Paragraph so long names fit) ----
    header = ["Tree Name", "Location", "Health", "Planting Date",
              "Last Watered", "CO2 (kg/year)"]
    data = [header]
    for r in rows:
        data.append([
            Paragraph(escape(r["name"]), cell),
            Paragraph(escape(r["location"]), cell),
            r["health"],
            _date(r["planting_date"]),
            _date(r["last_watered"]),
            f"{r['carbon']}",
        ])
    if not rows:
        data.append(["No trees registered yet.", "", "", "", "", ""])

    widths = [50 * mm, 75 * mm, 32 * mm, 32 * mm, 32 * mm, 35 * mm]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfe0d4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [table, Spacer(1, 6 * mm),
              Paragraph("Carbon values are simplified estimates for educational "
                        "purposes, not exact scientific measurements.", small)]

    doc.build(story)
    return path