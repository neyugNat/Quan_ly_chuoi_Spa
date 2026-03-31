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

    MAIL_MODE = os.getenv("MAIL_MODE", "console")  # console | smtp | off
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@lotusspa.local")
    MAIL_HOST = os.getenv("MAIL_HOST", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1") == "1"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "0") == "1"
    CUSTOMER_RESET_URL_BASE = os.getenv(
        "CUSTOMER_RESET_URL_BASE",
        "http://localhost:5173/login?mode=customer&view=reset",
    )


class DevConfig(Config):
    DEBUG = True
