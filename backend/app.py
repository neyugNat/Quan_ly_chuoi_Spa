import click
from flask import Flask, redirect, url_for

from backend.config import Config
from backend.extensions import db
from backend.models import ensure_seed_data
from backend.web import web_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    app.register_blueprint(web_bp)

    @app.get("/")
    def root():
        return redirect(url_for("web.index"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        print("init-db: ok")

    @app.cli.command("seed")
    def seed_command():
        db.create_all()
        ensure_seed_data()
        print("seed: ok")

    @app.cli.command("reset-db")
    @click.option("--seed/--no-seed", default=True)
    def reset_db_command(seed: bool):
        db.drop_all()
        db.create_all()
        if seed:
            ensure_seed_data()
        print("reset-db: ok")

    with app.app_context():
        db.create_all()

    return app


app = create_app()
