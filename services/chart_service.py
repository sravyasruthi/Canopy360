# services/chart_service.py - draws charts with Matplotlib as embedded images
import base64
import io
from matplotlib.figure import Figure


def _to_data_uri(fig):
    """Converts a Matplotlib figure into a PNG that can go inside <img src=...>."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight", transparent=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def bar_chart(labels, values, color="#1b9a55", ylabel=""):
    """Simple bar chart. Returns None when there is no data."""
    if not labels:
        return None
    fig = Figure(figsize=(5.2, 2.8))
    ax = fig.subplots()
    ax.bar(labels, values, color=color, width=0.6)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(axis="x", labelsize=8, rotation=30)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    return _to_data_uri(fig)


def line_chart(x_values, y_values, color="#1b9a55", xlabel="", ylabel=""):
    """Simple line chart with a light fill. Returns None when there is no data."""
    if not x_values:
        return None
    fig = Figure(figsize=(5.2, 2.8))
    ax = fig.subplots()
    ax.plot(x_values, y_values, color=color, marker="o", linewidth=2)
    ax.fill_between(x_values, y_values, color=color, alpha=0.12)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.25)
    return _to_data_uri(fig)


def doughnut_chart(labels, values, colors):
    """Doughnut chart. Zero values are left out. Returns None if nothing to show."""
    pairs = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
    if not pairs:
        return None
    fig = Figure(figsize=(5.2, 2.8))
    ax = fig.subplots()
    wedges, _texts, _auto = ax.pie(
        [p[1] for p in pairs], colors=[p[2] for p in pairs], startangle=90,
        wedgeprops={"width": 0.42, "edgecolor": "white"},
        autopct=lambda pct: f"{pct:.0f}%", pctdistance=0.79,
        textprops={"fontsize": 8, "color": "white"})
    ax.legend(wedges, [f"{p[0]} ({p[1]})" for p in pairs], loc="center left",
              bbox_to_anchor=(1, 0.5), fontsize=8, frameon=False)
    return _to_data_uri(fig)


def line_chart_labels(labels, values, color="#1b9a55", ylabel=""):
    """Line chart with text labels on the x-axis (for example years)."""
    if not labels:
        return None
    fig = Figure(figsize=(5.2, 2.8))
    ax = fig.subplots()
    ax.plot(labels, values, color=color, marker="o", linewidth=2)
    ax.fill_between(labels, values, color=color, alpha=0.12)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(axis="x", labelsize=8, rotation=30)
    ax.tick_params(axis="y", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.25)
    return _to_data_uri(fig)