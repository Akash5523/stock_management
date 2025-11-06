import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "devkey123")
    SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://root:test_db%40123@localhost/stockdb"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
