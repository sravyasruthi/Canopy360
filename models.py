# models.py - database tables (each class is one MySQL table)
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="User")        # Admin or User
    status = db.Column(db.String(20), default="Active")    # Active or Inactive
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        """Store only a hashed password, never plain text."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Tree(db.Model):
    __tablename__ = "trees"

    # Owner of the tree: each user only sees their own trees
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    owner = db.relationship("User", backref="trees")

    id = db.Column(db.Integer, primary_key=True)
    tree_name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(100), default="Unknown")
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    planting_date = db.Column(db.Date, nullable=True)
    age_estimated = db.Column(db.Boolean, default=False)   # True when the age was only approximate
    tree_age = db.Column("tree_age", db.Integer, default=1)   # stored backup value

    @property
    def tree_age(self):
        """Age in whole years, always calculated from the planting date."""
        if self.planting_date:
            today = date.today()
            years = today.year - self.planting_date.year
            if (today.month, today.day) < (self.planting_date.month, self.planting_date.day):
                years -= 1
            return max(years, 0)
        return self._tree_age or 1

    @tree_age.setter
    def tree_age(self, value):
        self._tree_age = value             # years
    height_m = db.Column(db.Float, default=1.0)               # metres
    diameter_cm = db.Column(db.Float, default=5.0)            # centimetres
    health_status = db.Column(db.String(30), default="Healthy")
    watering_frequency = db.Column(db.Integer, default=3)     # times per week
    last_watered = db.Column(db.Date, nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships: deleting a tree also deletes its related records
    watering_records = db.relationship(
        "WateringRecord", backref="tree", cascade="all, delete-orphan")
    fertilizer_schedules = db.relationship(
        "FertilizerSchedule", backref="tree", cascade="all, delete-orphan")
    carbon_records = db.relationship(
        "CarbonRecord", backref="tree", cascade="all, delete-orphan")


class WateringRecord(db.Model):
    __tablename__ = "watering_records"

    id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("trees.id"), nullable=False)
    watered_on = db.Column(db.Date, default=date.today)
    amount_litres = db.Column(db.Float, default=10.0)
    notes = db.Column(db.String(200), nullable=True)


class FertilizerSchedule(db.Model):
    __tablename__ = "fertilizer_schedules"

    id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("trees.id"), nullable=False)
    fertilizer_type = db.Column(db.String(100), nullable=False)
    application_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.String(50), nullable=True)        # e.g. "2 kg"
    notes = db.Column(db.String(200), nullable=True)
    completed = db.Column(db.Boolean, default=False)

    @property
    def status(self):
        """Status is worked out automatically from the date."""
        if self.completed:
            return "Completed"
        today = date.today()
        if self.application_date < today:
            return "Overdue"
        if self.application_date == today:
            return "Due Today"
        return "Upcoming"


class CarbonRecord(db.Model):
    __tablename__ = "carbon_records"

    id = db.Column(db.Integer, primary_key=True)
    tree_id = db.Column(db.Integer, db.ForeignKey("trees.id"), nullable=False)
    recorded_on = db.Column(db.Date, default=date.today)
    co2_kg_per_year = db.Column(db.Float, nullable=False)


class WeatherRecord(db.Model):
    __tablename__ = "weather_records"

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Integer)
    wind_kmh = db.Column(db.Float)
    rain_mm = db.Column(db.Float, default=0)
    description = db.Column(db.String(100))
    recorded_at = db.Column(db.DateTime, default=datetime.now)