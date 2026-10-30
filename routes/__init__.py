# routes/__init__.py - registers every route module that exists
import importlib

# Each module below must define a Blueprint named "bp"
MODULES = ["home", "auth", "dashboard", "trees", "weather", "carbon",
           "fertilizer", "reports", "users", "settings"]


def register_blueprints(app):
    for name in MODULES:
        try:
            module = importlib.import_module(f"routes.{name}")
        except ModuleNotFoundError as error:
            # Skip only if the route file itself doesn't exist yet
            if error.name == f"routes.{name}":
                continue
            raise
        app.register_blueprint(module.bp)