from flask import g, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user

from sqlalchemy_oso.flask import AuthorizedSQLAlchemy
from oso import Oso
from flask_oso import FlaskOso
from sqlalchemy_oso import register_models, set_get_session
from sqlalchemy_oso.roles import enable_roles
from sqlalchemy_oso.auth import authorize_model


base_oso = Oso()
current_action = "READ"
db = AuthorizedSQLAlchemy(
    get_oso=lambda: base_oso,
    get_user=lambda: current_user,
    get_action=lambda: current_action,
)


def init_oso(app):
    oso = FlaskOso(base_oso)

    register_models(base_oso, db.Model)
    set_get_session(base_oso, lambda: db.session)
    enable_roles(base_oso)
    base_oso.load_file("app/authorization.polar")
    app.oso = oso

    return base_oso


def get_authorized_filter(model, actor=None, action=None):
    return authorize_model(
        current_app.oso._oso,
        current_user._get_current_object(),
        g.current_action,
        db.session,
        model,
    )


def get_current_user():
    return current_user._get_current_object()