import click
from flask import Flask, redirect, url_for
from sqlalchemy import text

from backend.config import Config
from backend.extensions import db
from backend.models import (
    ensure_seed_data,
    migrate_add_branch_code,
    migrate_add_branch_manager_staff_id,
    migrate_backfill_user_staff_id,
    migrate_cleanup_unused_columns,
    migrate_add_operational_schema,
    migrate_add_user_staff_id,
    migrate_hash_plaintext_passwords,
    migrate_remove_partial_payment_schema,
)
from backend.web import web_bp


def run_schema_migrations() -> None:
    migrate_add_branch_code()
    migrate_add_branch_manager_staff_id()
    migrate_add_user_staff_id()
    migrate_backfill_user_staff_id()
    migrate_remove_partial_payment_schema()
    migrate_add_operational_schema()
    migrate_hash_plaintext_passwords()
    migrate_cleanup_unused_columns()


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
        run_schema_migrations()
        print("init-db: ok")

    @app.cli.command("seed")
    def seed_command():
        db.create_all()
        run_schema_migrations()
        ensure_seed_data()
        print("seed: ok")

    @app.cli.command("reset-db")
    @click.option("--seed/--no-seed", default=True)
    def reset_db_command(seed: bool):
        if db.engine.dialect.name == "sqlite":
            with db.engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys=OFF"))

        db.drop_all()
        db.create_all()
        run_schema_migrations()

        if db.engine.dialect.name == "sqlite":
            with db.engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys=ON"))

        if seed:
            ensure_seed_data()
        print("reset-db: ok")

    with app.app_context():
        db.create_all()
        run_schema_migrations()

    return app


app = create_app()
