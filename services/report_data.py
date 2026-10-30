# services/report_data.py - collects the numbers used in every report
from services.carbon_service import tree_yearly_co2


def collect_report_data(trees):
    """Returns (stats_dict, rows_list) built from a list of Tree objects."""
    rows = []
    for tree in trees:
        rows.append({
            "name": tree.tree_name,
            "species": tree.species or "-",
            "location": tree.location,
            "health": tree.health_status,
            "planting_date": tree.planting_date,
            "last_watered": tree.last_watered,
            "carbon": tree_yearly_co2(tree),
        })

    species = {t.species for t in trees if t.species and t.species != "Unknown"}
    stats = {
        "total_trees": len(trees),
        "total_species": len(species),
        "healthy": sum(1 for t in trees if t.health_status == "Healthy"),
        "needs_water": sum(1 for t in trees if t.health_status == "Needs Water"),
        "needs_care": sum(1 for t in trees if t.health_status == "Needs Care"),
        "critical": sum(1 for t in trees if t.health_status == "Critical"),
        "carbon_total": round(sum(r["carbon"] for r in rows), 2),
    }
    return stats, rows