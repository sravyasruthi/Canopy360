# clear_trees.py - deletes ALL trees and their records. Users are kept.
import os
from sqlalchemy import text
from app import app
from extensions import db
from models import Tree, WateringRecord, FertilizerSchedule, CarbonRecord

with app.app_context():
    total = Tree.query.count()
    print(f"This will permanently delete {total} tree(s) and all their records.")
    if input("Type YES to continue: ").strip() != "YES":
        print("Cancelled. Nothing was deleted.")
        raise SystemExit

    photos = [t.photo for t in Tree.query.all() if t.photo]

    # Delete the child records first, then the trees
    for model in (WateringRecord, FertilizerSchedule, CarbonRecord):
        model.query.delete()
    Tree.query.delete()
    db.session.commit()

    # Delete the uploaded photo files
    removed = 0
    for name in photos:
        path = os.path.join(app.config["UPLOAD_FOLDER"], os.path.basename(name))
        if os.path.exists(path):
            os.remove(path)
            removed += 1

    # Start the ID numbers from 1 again (optional tidy-up)
    for table in ("watering_records", "fertilizer_schedules", "carbon_records", "trees"):
        try:
            db.session.execute(text(f"ALTER TABLE {table} AUTO_INCREMENT = 1"))
        except Exception:
            db.session.rollback()
    db.session.commit()

    print(f"Done. Deleted {total} tree(s) and {removed} photo file(s).")