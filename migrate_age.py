# migrate_age.py - run ONCE: adds the age_estimated column to the trees table
from sqlalchemy import inspect, text
from app import app
from extensions import db

with app.app_context():
    columns = [c["name"] for c in inspect(db.engine).get_columns("trees")]
    if "age_estimated" not in columns:
        db.session.execute(text(
            "ALTER TABLE trees ADD COLUMN age_estimated TINYINT(1) NOT NULL DEFAULT 0"))
        db.session.commit()
        print("Added the age_estimated column.")
    else:
        print("The age_estimated column already exists.")