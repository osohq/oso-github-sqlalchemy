import json
import datetime
from enum import Enum

from flask import current_app, g
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.types import Integer, String, DateTime, Boolean
from sqlalchemy.schema import Table, Column, ForeignKey
from sqlalchemy.orm import relationship, scoped_session, backref

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_oso import authorized_sessionmaker
from sqlalchemy_utils.types.choice import ChoiceType

from sqlalchemy_oso.roles import resource_role_class

Base = declarative_base()

## MODELS ##


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String())
    base_repo_role = Column(String())
    billing_address = Column(String())

    def repr(self):
        return {"id": self.id, "name": self.name}


class User(Base):
    __tablename__ = "users"

    email = Column(String(), primary_key=True)
    authenticated = Column(Boolean, default=False)

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


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(256))

    # many-to-one relationship with organizations
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", backref="teams", lazy=True)

    def repr(self):
        return {"id": self.id, "name": self.name}


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    name = Column(String(256))

    # many-to-one relationship with organizations
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", backref="repositories", lazy=True)

    # time info
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.datetime.utcnow)

    def repr(self):
        return {"id": self.id, "name": self.name}


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    name = Column(String(256))
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    repository = relationship("Repository", backref="issues", lazy=True)


## ROLE MODELS ##
RepositoryRoleMixin = resource_role_class(
    declarative_base=Base,
    user_model=User,
    resource_model=Repository,
    role_choices=["READ", "TRIAGE", "WRITE", "MAINTAIN", "ADMIN"],
)


class RepositoryRole(Base, RepositoryRoleMixin):
    team_id = Column(Integer, ForeignKey("teams.id"))
    team = relationship("Team", backref="repository_roles", lazy=True)

    def repr(self):
        return {"id": self.id, "name": str(self.name)}


OrganizationRoleMixin = resource_role_class(
    Base, User, Organization, ["OWNER", "MEMBER", "BILLING"]
)


class OrganizationRole(Base, OrganizationRoleMixin):
    def repr(self):
        return {"id": self.id, "name": str(self.name)}


TeamRoleMixin = resource_role_class(Base, User, Team, ["MAINTAINER", "MEMBER"])


class TeamRole(Base, TeamRoleMixin):
    def repr(self):
        return {"id": self.id, "name": str(self.name)}
