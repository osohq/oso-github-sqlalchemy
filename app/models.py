from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.orm import relationship, scoped_session, backref

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_oso import authorized_sessionmaker
from sqlalchemy_utils.types.choice import ChoiceType

from sqlalchemy_oso.roles import resource_role_class

from .db import db

from flask_login import LoginManager

login_manager = LoginManager()

# Base = declarative_base()

## MODELS ##


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    base_repo_role = db.Column(db.String())
    billing_address = db.Column(db.String())

    def repr(self):
        return {"id": self.id, "name": self.name}


class User(db.Model):
    __tablename__ = "users"

    email = db.Column(db.String(), primary_key=True)
    authenticated = db.Column(db.Boolean, default=False)

    def is_active(self):
        return True

    def get_id(self):
        return self.email

    def is_authenticated(self):
        return self.is_authenticated

    def is_anonymous(self):
        return False

    def repr(self):
        return {"email": self.email}


@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))

    # many-to-one relationship with organizations
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"))
    organization = relationship("Organization", backref="teams", lazy=True)

    def repr(self):
        return {"id": self.id, "name": self.name}


class Repository(db.Model):
    __tablename__ = "repositories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))

    # many-to-one relationship with organizations
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"))
    organization = relationship("Organization", backref="repositories", lazy=True)

    # time info
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow)

    def repr(self):
        return {"id": self.id, "name": self.name}


class Issue(db.Model):
    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    repository_id = db.Column(db.Integer, db.ForeignKey("repositories.id"))
    repository = relationship("Repository", backref="issues", lazy=True)


## ROLE MODELS ##
RepositoryRoleMixin = resource_role_class(
    declarative_base=db.Model,
    user_model=User,
    resource_model=Repository,
    role_choices=["READ", "TRIAGE", "WRITE", "MAINTAIN", "ADMIN"],
)


class RepositoryRole(db.Model, RepositoryRoleMixin):
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"))
    team = relationship("Team", backref="repository_roles", lazy=True)

    def repr(self):
        return {"id": self.id, "name": str(self.name)}


OrganizationRoleMixin = resource_role_class(
    db.Model, User, Organization, ["OWNER", "MEMBER", "BILLING"]
)


class OrganizationRole(db.Model, OrganizationRoleMixin):
    def repr(self):
        return {"id": self.id, "name": str(self.name)}


TeamRoleMixin = resource_role_class(db.Model, User, Team, ["MAINTAINER", "MEMBER"])


class TeamRole(db.Model, TeamRoleMixin):
    def repr(self):
        return {"id": self.id, "name": str(self.name)}
