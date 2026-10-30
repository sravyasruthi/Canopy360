# services/watering_service.py - simple, transparent rule-based watering logic
# No machine learning: just points added or subtracted by clear rules.
from datetime import date

# Species that need more or less water (keywords matched in the species name)
THIRSTY_SPECIES = ["banana", "bamboo", "willow", "mango", "banyan"]
DROUGHT_TOLERANT = ["neem", "tamarind", "babul", "acacia", "peepal", "pongamia"]


def weekly_watering_need(weather, species="", age=1):
    """
    Returns (times_per_week, explanation_list).
    Start from a base of 3 waterings per week, then adjust by rules.
    """
    times = 3
    reasons = ["Base need: 3 times per week"]

    # Rule 1: temperature
    if weather["temperature"] >= 35:
        times += 2
        reasons.append("Very hot weather (35C or more): +2")
    elif weather["temperature"] >= 30:
        times += 1
        reasons.append("Hot weather (30C or more): +1")
    elif weather["temperature"] <= 18:
        times -= 1
        reasons.append("Cool weather (18C or less): -1")

    # Rule 2: humidity
    if weather["humidity"] >= 75:
        times -= 1
        reasons.append("High humidity (75% or more): -1")
    elif weather["humidity"] <= 35:
        times += 1
        reasons.append("Dry air (35% or less): +1")

    # Rule 3: rainfall
    if weather["rain_mm"] >= 5:
        times -= 2
        reasons.append("Good rainfall (5 mm or more): -2")
    elif weather["rain_mm"] > 0:
        times -= 1
        reasons.append("Light rain: -1")

    # Rule 4: species
    name = (species or "").lower()
    if any(s in name for s in THIRSTY_SPECIES):
        times += 1
        reasons.append("Species needs more water: +1")
    elif any(s in name for s in DROUGHT_TOLERANT):
        times -= 1
        reasons.append("Drought-tolerant species: -1")

    # Rule 5: age (young trees have shallow roots)
    if age is not None and age <= 2:
        times += 1
        reasons.append("Young tree (2 years or less): +1")

    times = max(1, min(times, 7))  # keep between 1 and 7
    return times, reasons


def watering_status(tree, weather):
    """
    Returns (status_text, css_class) for a single tree, using the
    last watered date and the weather-adjusted weekly need.
    """
    times, _ = weekly_watering_need(weather, tree.species, tree.tree_age)

    if tree.last_watered is None:
        return "Needs Water", "danger"

    days_since = (date.today() - tree.last_watered).days
    gap_days = max(1, round(7 / times))   # days allowed between waterings

    if days_since > gap_days + 1:
        return "Needs Water", "danger"
    if days_since >= gap_days:
        return "Water Soon", "warning"
    return "Watered", "success"


def overall_recommendation(weather):
    """Short message for the dashboard card."""
    times, reasons = weekly_watering_need(weather)
    if weather["rain_mm"] >= 5:
        level = "Rain is expected to help."
    elif weather["temperature"] >= 32:
        level = "Weather is hot."
    elif weather["temperature"] <= 18:
        level = "Weather is cool."
    else:
        level = "Weather is moderate."
    return {
        "headline": level,
        "advice": f"Water your trees {times} times this week.",
        "times": times,
        "reasons": reasons,
    }