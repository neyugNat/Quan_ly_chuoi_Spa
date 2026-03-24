# pyright: reportMissingImports=false

import os

from flask import Flask

from backend.api import api_bp
from backend.config import DevConfig
from backend.extensions import cors, db, jwt, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object(DevConfig)

    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    app.register_blueprint(api_bp)

    if os.getenv("AUTO_SEED_DEMO") == "1":
        from backend.api.auth import ensure_demo_seed

        with app.app_context():
            ensure_demo_seed()

    @app.cli.command("seed")
    def seed_command():
        from backend.api.auth import ensure_demo_seed

        ensure_demo_seed()
        print("seed: ok")

    return app


app = create_app()
