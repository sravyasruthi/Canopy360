# services/geocode_service.py - finds GPS coordinates from a place name (OpenStreetMap)
import requests

# Search only inside this country (2-letter code). Use "" to search the whole world.
COUNTRY = "in"


def find_coordinates(place):
    """Returns (latitude, longitude) for a place name, or None if not found."""
    place = (place or "").strip()
    if not place:
        return None

    params = {"q": place, "format": "json", "limit": 1}
    if COUNTRY:
        params["countrycodes"] = COUNTRY

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers={"User-Agent": "Canopy360-College-Project/1.0"},
            timeout=5)
        if response.status_code != 200:
            return None
        results = response.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None   # no internet or unknown place: the tree is saved without GPS