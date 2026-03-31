import os


class Config:
    # NOTE: Defaults are for local assignment use only.
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///spa.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "spa-web-dev-secret-change-me")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))

    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")


class DevConfig(Config):
    DEBUG = True
