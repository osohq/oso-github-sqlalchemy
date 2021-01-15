from copy import deepcopy
from flask import Blueprint, g, request, current_app, redirect, render_template, flash
from flask_oso import authorize
from .models import User, Organization, Team, Repository, Issue
from .models import RepositoryRole, OrganizationRole, TeamRole
from .forms import LoginForm
from .auth import db, get_authorized_filter, get_current_user

from sqlalchemy_oso import roles as oso_roles
from sqlalchemy_oso.auth import authorize_model
from oso import Variable

from flask_login import login_required, login_user


bp = Blueprint("routes", __name__)


@bp.route("/", methods=["GET"])
@login_required
def hello():
    return redirect("/orgs")


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.session.query(User).get(email)
        if user:
            user.authenticated = True
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect("/orgs")
        else:
            flash("Login attempt failed")

    return render_template("login.html", form=form)


@bp.route("/orgs", methods=["GET"])
def orgs_index():
    # get all allowed organizations
    filter = get_authorized_filter(Organization, action=Variable("action"))
    orgs = Organization.query.filter(filter)
    # get allowed actions
    actions = {
        org.name: current_app.oso._oso.get_allowed_actions(
            get_current_user(), org, allow_wildcard=True
        )
        for org in orgs
    }

    return {
        "orgs": [{"org": org.repr(), "actions": actions.get(org.name)} for org in orgs]
    }


@bp.route("/orgs/<int:org_id>/repos", methods=["GET"])
def repos_index(org_id):
    org = db.session.query(Organization).filter(Organization.id == org_id).first()
    current_app.oso.authorize(org, actor=get_current_user(), action="LIST_REPOS")

    # get all allowed repositories
    g.current_action = Variable("action")
    repos = db.session.query(Repository).filter_by(organization=org)
    # get allowed actions
    actions = {
        repo.name: current_app.oso._oso.get_allowed_actions(
            get_current_user(), repo, allow_wildcard=True
        )
        for repo in repos
    }
    return {
        "repos": [
            {"repo": repo.repr(), "actions": actions.get(repo.name)} for repo in repos
        ]
    }


@bp.route("/orgs/<int:org_id>/repos", methods=["POST"])
def repos_new(org_id):
    # Create repo
    repo_name = request.get_json().get("name")
    org = db.session.query(Organization).filter(Organization.id == org_id).first()
    repo = Repository(name=repo_name, organization=org)

    # Authorize repo creation + save
    current_app.oso.authorize(repo, actor=current_user, action="CREATE")
    db.session.add(repo)
    db.session.commit()
    return f"created a new repo for org: {org_id}, {repo_name}"


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>", methods=["GET"])
def repos_show(org_id, repo_id):
    # Get repo
    repo = db.session.query(Repository).filter(Repository.id == repo_id).one()

    # Authorize repo access
    current_app.oso.authorize(repo, actor=current_user, action="READ")

    ## EXPERIMENTAL START
    # Get allowed actions on the repo
    actions = current_app.oso._oso.get_allowed_actions(
        current_user, repo, allow_wildcard=True
    )
    ## EXPERIMENTAL END
    return {"repo": repo.repr(), "actions": actions}


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>/issues", methods=["GET"])
def issues_index(org_id, repo_id):
    repo = db.session.query(Repository).filter(Repository.id == repo_id).one()
    current_app.oso.authorize(repo, actor=current_user, action="LIST_ISSUES")

    # Get authorized issues
    issues = db.session.query(Issue).filter(Issue.repository.has(id=repo_id))
    return {
        f"issues for org {org_id}, repo {repo_id}": [issue.repr() for issue in issues]
    }


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>/roles", methods=["GET", "POST"])
def repo_roles_index(org_id, repo_id):
    if request.method == "GET":
        repo = db.session.query(Repository).filter(Repository.id == repo_id).one()
        current_app.oso.authorize(repo, actor=current_user, action="LIST_ROLES")
        roles = oso_roles.get_resource_roles(db.session, repo)
        return {
            "roles": [
                {
                    "user": role.user.repr() if role.user else {"email": "none"},
                    "team": role.team.repr() if role.team else {"name": "none"},
                    "role": role.repr(),
                }
                for role in roles
            ]
        }
    if request.method == "POST":
        # TODO: test this
        content = request.get_json()
        print(content)
        role_info = content.get("role")
        role_name = role_info.get("name")
        user_email = role_info.get("user")
        user = db.session.query(User).filter_by(email=user_email).first()
        repo = db.session.query(Repository).filter_by(id=repo_id).first()
        oso_roles.add_user_role(db.session, user, repo, role_name, commit=True)
        return f"created a new repo role for repo: {repo_id}, {role_name}"


@bp.route("/orgs/<int:org_id>/teams", methods=["GET"])
def teams_index(org_id):
    org = db.session.query(Organization).filter(Organization.id == org_id).first()
    current_app.oso.authorize(org, actor=current_user, action="LIST_TEAMS")

    teams = db.session.query(Team).filter(Team.organization.has(id=org_id))
    return {f"teams for org_id {org_id}": [team.repr() for team in teams]}


@bp.route("/orgs/<int:org_id>/teams/<int:team_id>", methods=["GET"])
def teams_show(org_id, team_id):
    team = db.session.query(Team).get(team_id)
    current_app.oso.authorize(team, action="READ")
    return team.repr()


@bp.route("/orgs/<int:org_id>/billing", methods=["GET"])
def billing_show(org_id):
    org = db.session.query(Organization).filter(Organization.id == org_id).first()
    current_app.oso.authorize(org, actor=current_user, action="READ_BILLING")
    return {f"billing_address": org.billing_address}


@bp.route("/orgs/<int:org_id>/roles", methods=["GET"])
def org_roles_index(org_id):
    # Get authorized roles for this organization
    org = db.session.query(Organization).filter_by(id=org_id).first()
    current_app.oso.authorize(org, actor=current_user, action="LIST_ROLES")

    roles = oso_roles.get_resource_roles(db.session, org)
    return {
        f"roles": [{"user": role.user.repr(), "role": role.repr()} for role in roles]
    }
