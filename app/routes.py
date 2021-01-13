from copy import deepcopy
from flask import Blueprint, g, request, current_app
from flask_oso import authorize
from .models import User, Organization, Team, Repository, Issue
from .models import RepositoryRole, OrganizationRole, TeamRole

from sqlalchemy_oso import roles as oso_roles
from oso import Variable

bp = Blueprint("routes", __name__)


@bp.route("/", methods=["GET"])
def hello():
    if "current_user" in g:
        return g.current_user.repr()
    else:
        return f'Please "log in"'


@bp.route("/orgs", methods=["GET"])
def orgs_index():
    # get all allowed organizations
    g.current_action = Variable("action")
    new_auth_session = current_app.auth_sessionmaker()
    orgs = new_auth_session.query(Organization).all()
    # get allowed actions
    actions = {org.name: get_allowed_actions(current_app.oso._oso, org) for org in orgs}

    return {
        "orgs": [{"org": org.repr(), "actions": actions.get(org.name)} for org in orgs]
    }


@bp.route("/orgs/<int:org_id>/repos", methods=["GET"])
def repos_index(org_id):
    org = g.basic_session.query(Organization).filter(Organization.id == org_id).first()
    current_app.oso.authorize(org, actor=g.current_user, action="LIST_REPOS")

    # get all allowed repositories
    g.current_action = Variable("action")
    new_auth_session = current_app.auth_sessionmaker()
    repos = new_auth_session.query(Repository).filter_by(organization=org)
    # get allowed actions
    actions = {
        repo.name: get_allowed_actions(current_app.oso._oso, repo) for repo in repos
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
    org = g.basic_session.query(Organization).filter(Organization.id == org_id).first()
    repo = Repository(name=repo_name, organization=org)

    # Authorize repo creation + save
    current_app.oso.authorize(repo, actor=g.current_user, action="CREATE")
    g.basic_session.add(repo)
    g.basic_session.commit()
    return f"created a new repo for org: {org_id}, {repo_name}"


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>", methods=["GET"])
def repos_show(org_id, repo_id):
    # Get repo
    repo = g.basic_session.query(Repository).filter(Repository.id == repo_id).one()

    # Authorize repo access
    current_app.oso.authorize(repo, actor=g.current_user, action="READ")

    ## EXPERIMENTAL START
    # Get allowed actions on the repo
    results = current_app.oso._oso.query_rule(
        "allow", g.current_user, Variable("action"), repo
    )
    actions = list(set([result.get("bindings").get("action") for result in results]))
    ## EXPERIMENTAL END
    return {"repo": repo.repr(), "actions": actions}


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>/issues", methods=["GET"])
def issues_index(org_id, repo_id):
    repo = g.basic_session.query(Repository).filter(Repository.id == repo_id).one()
    current_app.oso.authorize(repo, actor=g.current_user, action="LIST_ISSUES")

    # Get authorized issues
    issues = g.auth_session.query(Issue).filter(Issue.repository.has(id=repo_id))
    return {
        f"issues for org {org_id}, repo {repo_id}": [issue.repr() for issue in issues]
    }


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>/roles", methods=["GET", "POST"])
def repo_roles_index(org_id, repo_id):
    if request.method == "GET":
        repo = g.basic_session.query(Repository).filter(Repository.id == repo_id).one()
        current_app.oso.authorize(repo, actor=g.current_user, action="LIST_ROLES")
        roles = oso_roles.get_resource_roles(g.auth_session, repo)
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
        # new_auth_session = current_app.auth_sessionmaker()
        user = g.auth_session.query(User).filter_by(email=user_email).first()
        repo = g.auth_session.query(Repository).filter_by(id=repo_id).first()
        oso_roles.add_user_role(g.auth_session, user, repo, role_name, commit=True)
        return f"created a new repo role for repo: {repo_id}, {role_name}"


@bp.route("/orgs/<int:org_id>/teams", methods=["GET"])
def teams_index(org_id):
    org = g.basic_session.query(Organization).filter(Organization.id == org_id).first()
    current_app.oso.authorize(org, actor=g.current_user, action="LIST_TEAMS")

    teams = g.auth_session.query(Team).filter(Team.organization.has(id=org_id))
    return {f"teams for org_id {org_id}": [team.repr() for team in teams]}


@bp.route("/orgs/<int:org_id>/teams/<int:team_id>", methods=["GET"])
def teams_show(org_id, team_id):
    team = g.basic_session.query(Team).get(team_id)
    current_app.oso.authorize(team, action="READ")
    return team.repr()


@bp.route("/orgs/<int:org_id>/billing", methods=["GET"])
def billing_show(org_id):
    org = g.basic_session.query(Organization).filter(Organization.id == org_id).first()
    current_app.oso.authorize(org, actor=g.current_user, action="READ_BILLING")
    return {f"billing_address": org.billing_address}


@bp.route("/orgs/<int:org_id>/roles", methods=["GET"])
def org_roles_index(org_id):
    # Get authorized roles for this organization
    org = g.basic_session.query(Organization).filter_by(id=org_id).first()
    current_app.oso.authorize(org, actor=g.current_user, action="LIST_ROLES")

    roles = oso_roles.get_resource_roles(g.auth_session, org)
    return {
        f"roles": [{"user": role.user.repr(), "role": role.repr()} for role in roles]
    }


def get_allowed_actions(oso, resource):
    # Get allowed actions on the repo
    results = oso.query_rule("allow", g.current_user, Variable("action"), resource)
    return list(set([result.get("bindings").get("action") for result in results]))