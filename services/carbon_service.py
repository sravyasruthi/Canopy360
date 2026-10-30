# services/carbon_service.py - simplified CO2 absorption estimate
#
# IMPORTANT: This is a SIMPLIFIED ESTIMATE for a college project.
# It is NOT a scientifically exact carbon measurement.
#
# Formula used:
#   1. Biomass (kg)      = 0.0509 x wood_density x diameter(cm)^2 x height(m)
#                          (a commonly used simplified tree biomass equation,
#                           wood_density assumed 0.6)
#   2. Carbon stored (kg)= biomass x 0.5      (about half of dry biomass is carbon)
#   3. CO2 stored (kg)   = carbon x 3.67      (ratio of CO2 to C molecular weight)
#   4. CO2 per year (kg) = CO2 stored / age   (average yearly absorption)

WOOD_DENSITY = 0.6
CARBON_FRACTION = 0.5
CO2_FACTOR = 3.67

DISCLAIMER = ("Estimated Carbon Absorption - a simplified estimate for "
              "educational purposes, not an exact scientific measurement.")


def estimate_co2(age, diameter_cm, height_m):
    """Returns a dictionary with total stored CO2 and yearly/monthly values."""
    age = max(float(age or 1), 1)
    diameter_cm = max(float(diameter_cm or 0), 0)
    height_m = max(float(height_m or 0), 0)

    biomass = 0.0509 * WOOD_DENSITY * (diameter_cm ** 2) * height_m
    carbon = biomass * CARBON_FRACTION
    co2_total = carbon * CO2_FACTOR
    co2_year = co2_total / age

    return {
        "biomass_kg": round(biomass, 2),
        "carbon_kg": round(carbon, 2),
        "total_co2_kg": round(co2_total, 2),
        "yearly_co2_kg": round(co2_year, 2),
        "monthly_co2_kg": round(co2_year / 12, 2),
    }


def tree_yearly_co2(tree):
    """Yearly CO2 for a Tree database object."""
    return estimate_co2(tree.tree_age, tree.diameter_cm, tree.height_m)["yearly_co2_kg"]


def total_yearly_co2(trees):
    """Sum of yearly CO2 for a list of trees."""
    return round(sum(tree_yearly_co2(t) for t in trees), 2)


def growth_curve(age, diameter_cm, height_m):
    """
    Estimated yearly absorption for each year of the tree's life so far.
    Used for the 'carbon absorption over time' chart. Assumes the tree
    grew in a straight line from size zero to its current size.
    """
    age = max(int(age or 1), 1)
    points = []
    for year in range(1, age + 1):
        fraction = year / age
        values = estimate_co2(year, diameter_cm * fraction, height_m * fraction)
        points.append((year, values["yearly_co2_kg"]))
    return points


# ---------- Size estimate for users who do not know diameter / height ----------
# Matched against the species text (common and scientific names)
FAST_GROWERS = ["neem", "azadirachta", "gulmohar", "delonix", "pongamia",
                "eucalyptus", "subabul", "bamboo", "banana", "casuarina", "silver oak"]
SLOW_GROWERS = ["tamarind", "tamarindus", "banyan", "ficus benghalensis",
                "peepal", "ficus religiosa", "teak", "mahogany", "jamun",
                "syzygium", "sal ", "ebony"]


def estimate_size(age, species=""):
    """
    Rough guess of (diameter_cm, height_m) from age and species growth speed.
    This is only an approximation, used when the real size is not known.
    """
    age = max(float(age or 1), 1)
    name = (species or "").lower()

    if any(word in name for word in FAST_GROWERS):
        d_rate, h_rate = 3.0, 1.0      # cm of diameter and metres of height per year
    elif any(word in name for word in SLOW_GROWERS):
        d_rate, h_rate = 1.5, 0.5
    else:
        d_rate, h_rate = 2.0, 0.7      # average growth

    diameter = min(max(age * d_rate, 2.0), 150.0)
    height = min(max(age * h_rate + 1.0, 1.0), 30.0)
    return round(diameter, 1), round(height, 1)