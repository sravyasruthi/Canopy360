# config.py - reads all settings from the .env file
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()  # loads values from .env into environment variables

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    # Database settings (quote_plus keeps special characters in the password safe)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "canopy360")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB maximum upload size

    # Reports are saved here
    REPORTS_FOLDER = os.path.join(BASE_DIR, "reports")

    # Weather API (never hardcode the key; it comes from .env)
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    DEFAULT_CITY = "Hyderabad"
    DEFAULT_LAT = 17.3850
    DEFAULT_LON = 78.4867