from datetime import datetime, timedelta
from flask import Blueprint, g, request, current_app, redirect, render_template, flash
from flask_oso import authorize
from .models import User, Organization, Team, Repository, Issue
from .models import RepositoryRole, OrganizationRole, TeamRole
from .forms import LoginForm, RepositoryRoleForm
from .auth import db, get_authorized_filter, get_current_user

from sqlalchemy_oso import roles as oso_roles
from sqlalchemy_oso.auth import authorize_model
from oso import Variable

from flask_login import login_required, login_user, current_user, logout_user


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
        user = User.query.get(email)
        if user:
            user.authenticated = True
            db.session.commit()
            login_user(user)
            return redirect("/orgs")
        else:
            flash("Login attempt failed")

    return render_template("login.html", form=form)


@bp.route("/logout", methods=["GET"])
@login_required
def logout():
    """Logout the current user."""
    user = current_user
    user.authenticated = False
    db.session.commit()
    logout_user()
    return redirect("/")


@bp.route("/orgs", methods=["GET"])
@login_required
def orgs_index():
    # get all allowed organizations
    auth_filter = get_authorized_filter(Organization)
    orgs = Organization.query.filter(auth_filter).all()
    # get allowed actions
    actions = {
        org.name: current_app.oso._oso.get_allowed_actions(
            get_current_user(), org, allow_wildcard=True
        )
        for org in orgs
    }
    return render_template("orgs/index.html", org_list=orgs, actions=actions)


@bp.route("/orgs/<int:org_id>/repos", methods=["GET"])
@login_required
def repos_index(org_id):
    org = Organization.query.get(org_id)
    current_app.oso.authorize(org, action="LIST_REPOS")

    # get all allowed repositories
    auth_filter = get_authorized_filter(Repository)
    repos = Repository.query.filter_by(organization=org).filter(auth_filter).all()
    # get allowed actions
    actions = {
        repo.name: current_app.oso._oso.get_allowed_actions(
            get_current_user(), repo, allow_wildcard=True
        )
        for repo in repos
    }
    return render_template(
        "repos/index.html", repo_list=repos, actions=actions, org=org
    )


@bp.route("/orgs/<int:org_id>/repos", methods=["POST"])
@login_required
def repos_new(org_id):
    # Create repo
    repo_name = request.get_json().get("name")
    org = db.session.query(Organization).filter(Organization.id == org_id).first()
    repo = Repository(name=repo_name, organization=org)

    # Authorize repo creation + save
    current_app.oso.authorize(repo, action="CREATE")
    db.session.add(repo)
    db.session.commit()
    return f"created a new repo for org: {org_id}, {repo_name}"


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>", methods=["GET"])
@login_required
def repos_show(org_id, repo_id):
    # Get repo
    repo = Repository.query.get(repo_id)
    contributors = len(repo.name)
    commits = contributors * 17
    last_updated = datetime.now() - timedelta(hours=commits, minutes=contributors)

    # Authorize repo access
    current_app.oso.authorize(repo, action="READ")

    ## EXPERIMENTAL START
    # Get allowed actions on the repo
    actions = current_app.oso._oso.get_allowed_actions(
        get_current_user(), repo, allow_wildcard=True
    )
    ## EXPERIMENTAL END
    return render_template(
        "repos/show.html",
        repo=repo,
        org_id=org_id,
        commits=commits,
        contributors=contributors,
        last_updated=last_updated,
        actions=actions,
    )
    return {"repo": repo.repr(), "actions": actions}


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>/issues", methods=["GET"])
@login_required
def issues_index(org_id, repo_id):
    repo = Repository.query.get(repo_id)
    current_app.oso.authorize(repo, action="LIST_ISSUES")

    # Get authorized issues
    auth_filter = get_authorized_filter(Issue)
    issues = (
        Issue.query.filter(Issue.repository.has(id=repo_id)).filter(auth_filter).all()
    )
    return render_template(
        "issues/index.html", issue_list=issues, org=repo.organization, repo=repo
    )


@bp.route("/orgs/<int:org_id>/repos/<int:repo_id>/roles", methods=["GET", "POST"])
@login_required
def repo_roles_index(org_id, repo_id):
    if request.method == "GET":
        repo = Repository.query.get(repo_id)
        current_app.oso.authorize(repo, action="LIST_ROLES")
        roles = oso_roles.get_resource_roles(db.session, repo)
        # Create forms for view
        user_forms = []
        team_forms = []
        for role in roles:
            form = RepositoryRoleForm()
            form.role.data = role.name
            if role.user:
                form.name.data = role.user.email
                user_forms.append(form)
            elif role.team:
                form.name.data = role.team.name
                team_forms.append(form)

        user_forms.sort(key=lambda x: x.name.data)
        team_forms.sort(key=lambda x: x.name.data)

        return render_template(
            "repos/roles.html",
            org=repo.organization,
            repo=repo,
            user_forms=user_forms,
            team_forms=team_forms,
        )
    if request.method == "POST":
        role_name = request.values.get("role")
        email = request.values.get("name")
        user = User.query.get(email)
        repo = Repository.query.get(repo_id)
        if user:
            oso_roles.reassign_user_role(db.session, user, repo, role_name, commit=True)
        return redirect(f"/orgs/{org_id}/repos/{repo_id}/roles")


## ADD TEMPLATE RENDERS BELOW HERE


@bp.route("/orgs/<int:org_id>/teams", methods=["GET"])
@login_required
def teams_index(org_id):
    org = Organization.query.get(org_id)
    current_app.oso.authorize(org, action="LIST_TEAMS")

    auth_filter = get_authorized_filter(Team)
    teams = (
        Team.query.filter(Team.organization.has(id=org_id)).filter(auth_filter).all()
    )
    return {f"teams for org_id {org_id}": [team.repr() for team in teams]}


@bp.route("/orgs/<int:org_id>/teams/<int:team_id>", methods=["GET"])
@login_required
def teams_show(org_id, team_id):
    team = Team.query.get(team_id)
    current_app.oso.authorize(team, action="READ")
    return team.repr()


@bp.route("/orgs/<int:org_id>/billing", methods=["GET"])
@login_required
def billing_show(org_id):
    org = Organization.query.get(org_id).first()
    current_app.oso.authorize(org, action="READ_BILLING")
    return {f"billing_address": org.billing_address}


@bp.route("/orgs/<int:org_id>/roles", methods=["GET"])
@login_required
def org_roles_index(org_id):
    # Get authorized roles for this organization
    org = db.session.query(Organization).filter_by(id=org_id).first()
    current_app.oso.authorize(org, action="LIST_ROLES")

    roles = oso_roles.get_resource_roles(db.session, org)
    return {
        f"roles": [{"user": role.user.repr(), "role": role.repr()} for role in roles]
    }
