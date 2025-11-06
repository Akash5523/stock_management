from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)
    db.init_app(app)
    CORS(app)

    # ✅ Import models here so Alembic can detect them
    from .models import StockItem

    # Register routes (blueprint)
    from .routes import main
    app.register_blueprint(main)

    return app
