# services/map_service.py - builds the interactive tree map with Folium
import html
import folium
from config import Config

# Marker colour for each health status
MARKER_COLORS = {
    "Healthy": "green",
    "Needs Care": "orange",
    "Needs Water": "blue",
    "Critical": "red",
}


def build_tree_map(trees, zoom=11):
    """Returns the full map as an HTML string (free OpenStreetMap tiles)."""
    tree_map = folium.Map(
        location=[Config.DEFAULT_LAT, Config.DEFAULT_LON],
        zoom_start=zoom, tiles="OpenStreetMap", zoom_control=True)

    points = []
    for tree in trees:
        if tree.latitude is None or tree.longitude is None:
            continue   # trees without GPS coordinates cannot be placed

        planted = tree.planting_date.strftime("%d %b %Y") if tree.planting_date else "-"
        if tree.age_estimated:
            planted += " (approx.)"
        owner = tree.owner.name if tree.owner else "-"

        # html.escape stops user-typed text from breaking the popup
        popup_html = (
            f"<b>{html.escape(tree.tree_name)}</b><br>"
            f"Species: {html.escape(tree.species or '-')}<br>"
            f"Location: {html.escape(tree.location)}<br>"
            f"Health: {html.escape(tree.health_status)}<br>"
            f"Planted: {planted}<br>"
            f"Owner: {html.escape(owner)}"
        )
        folium.Marker(
            location=[tree.latitude, tree.longitude],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=tree.tree_name,
            icon=folium.Icon(color=MARKER_COLORS.get(tree.health_status, "green"),
                             icon="tree", prefix="fa"),
        ).add_to(tree_map)
        points.append([tree.latitude, tree.longitude])

    # Zoom the map so that every marker is visible
    if points:
        tree_map.fit_bounds(points, padding=(30, 30), max_zoom=15)

    return tree_map.get_root().render()