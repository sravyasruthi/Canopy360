# locate_trees.py - run when needed: finds GPS positions for trees that have none
import time
from sqlalchemy import or_
from app import app
from models import Tree
from extensions import db
from services.geocode_service import find_coordinates

with app.app_context():
    trees = Tree.query.filter(or_(Tree.latitude.is_(None), Tree.longitude.is_(None))).all()
    print(f"{len(trees)} tree(s) have no GPS position.")
    for tree in trees:
        coords = find_coordinates(tree.location)
        if coords:
            tree.latitude, tree.longitude = coords
            print(f"  Found: {tree.tree_name} ({tree.location}) -> {coords}")
        else:
            print(f"  Not found: {tree.tree_name} ({tree.location})")
        time.sleep(1.1)   # be polite to the free search service
    db.session.commit()
    print("Done.")