from flask import Flask
from flask_migrate import Migrate
from models import db
from main import app

migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        from flask_migrate import upgrade, init, migrate
        init()  # Initialize migrations directory if it doesn't exist
        migrate()  # Create new migration
        upgrade()  # Apply migration
