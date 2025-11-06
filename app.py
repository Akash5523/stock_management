from flask_migrate import Migrate
from stockapp import create_app, db
from stockapp.models import StockItem
from sqlalchemy import text

# Create the Flask app
app = create_app()

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Optional: quick connection test
with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        print("✅ Database connected successfully!")
    except Exception as e:
        print("❌ Database connection failed:", e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
