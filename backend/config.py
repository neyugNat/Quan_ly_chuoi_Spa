import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "spa-mvp-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///spa_mvp.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
