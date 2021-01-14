from flask import g, Flask, request

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .fixtures import load_fixture_data
from .db import db
from .models import login_manager

from werkzeug.exceptions import Unauthorized

from flask_oso import FlaskOso
from oso import Oso
from sqlalchemy_oso import authorized_sessionmaker, register_models, set_get_session
from sqlalchemy_oso.roles import enable_roles


def create_app(db_path=None, load_fixtures=False):
    from . import routes

    # init app
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    app.secret_key = b"\xc7\xbbl;\xabn\xfd'8T\xe5i\xf4\x95\x9c\x80"

    # init db
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///roles.db"
    db.init_app(app)

    with app.app_context():
        # create tables
        db.create_all()
        # optionally load fixture data
        if load_fixtures:
            load_fixture_data(db.session)

    login_manager.login_view = "routes.login"
    login_manager.init_app(app)

    # init oso
    oso = init_oso(app)

    @app.before_request
    def set_current_session():

        # Set action for this request
        actions = {"GET": "READ", "POST": "CREATE"}
        g.current_action = actions[request.method]

    return app


def init_oso(app):
    base_oso = Oso()
    oso = FlaskOso(base_oso)

    register_models(base_oso, db.Model)
    set_get_session(base_oso, lambda: db.session)
    enable_roles(base_oso)
    base_oso.load_file("app/authorization.polar")
    app.oso = oso

    return base_oso
