from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.fields import SelectField
from wtforms.validators import DataRequired

from .models import RepositoryRole


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password")


class RepositoryRoleForm(FlaskForm):
    name = StringField(render_kw={"readonly": True})
    role = SelectField(choices=RepositoryRole.choices)
