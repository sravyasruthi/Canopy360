# services/weather_service.py - gets weather from the OpenWeather API
import requests
from config import Config

# Demo data shown when the API key is missing or the API fails
DEMO_WEATHER = {
    "city": "Hyderabad",
    "country": "IN",
    "temperature": 28.0,
    "feels_like": 30.0,
    "description": "Partly Cloudy",
    "humidity": 60,
    "wind_kmh": 12.0,
    "rain_mm": 0.0,
    "is_demo": True,
}


def get_weather(city=None):
    """
    Returns (weather_dict, message).
    message is None when live data was fetched, otherwise a friendly
    text explaining why demo data is being shown. The site never crashes.
    """
    city = city or Config.DEFAULT_CITY
    api_key = Config.OPENWEATHER_API_KEY

    # 1. No API key set in .env
    if not api_key or api_key == "your_openweather_api_key":
        return dict(DEMO_WEATHER), (
            "OpenWeather API key is missing. Showing demo weather. "
            "Add OPENWEATHER_API_KEY to your .env file to see live data."
        )

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": f"{city},IN", "appid": api_key, "units": "metric"}

    try:
        response = requests.get(url, params=params, timeout=6)

        # 2. Key rejected or city not found
        if response.status_code == 401:
            return dict(DEMO_WEATHER), (
                "OpenWeather rejected the API key (it may be invalid or not "
                "activated yet - new keys can take a couple of hours). "
                "Showing demo weather."
            )
        if response.status_code != 200:
            return dict(DEMO_WEATHER), (
                f"Weather service returned an error ({response.status_code}). "
                "Showing demo weather."
            )

        data = response.json()
        weather = {
            "city": data.get("name", city),
            "country": data.get("sys", {}).get("country", "IN"),
            "temperature": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "description": data["weather"][0]["description"].title(),
            "humidity": data["main"]["humidity"],
            # API gives metres/second, we show km/h
            "wind_kmh": round(data["wind"]["speed"] * 3.6, 1),
            "rain_mm": data.get("rain", {}).get("1h", 0.0),
            "is_demo": False,
        }
        return weather, None

    # 3. No internet, timeout, or unexpected data
    except (requests.RequestException, KeyError, ValueError):
        return dict(DEMO_WEATHER), (
            "Could not reach the weather service. Showing demo weather."
        )


# ---- Simple 10-minute cache so the header doesn't call the API on every page ----
import time

_cache = {"time": 0, "data": None}


def get_cached_weather(max_age=600):
    """Returns (weather_dict, message), reusing a recent result if available."""
    now = time.time()
    if _cache["data"] is None or now - _cache["time"] > max_age:
        _cache["data"] = get_weather()
        _cache["time"] = now
    return _cache["data"]    