# ⚠️ Project Archived: Please check out [osohq/gitclub](https://github.com/osohq/gitclub) for an up-to-date example

# Modeling GitHub permissions with oso

This application is a sample application based on GitHub, meant to model the basics of GitHub's permissions system.
The app uses the `sqlalchemy-oso` [authorization library](https://docs.osohq.com/using/frameworks/sqlalchemy.html) to model and enforce this system. For more information on oso, check out our docs.

The data model is based on the B2B features of GitHub (it does not cover the B2C features).

## Application Data Model

The app has the following models:

### Actors and Resources

- `Organization`
  - Organizations are the top-level grouping of users and resources in the app. As with the real GitHub, users can be in multiple Organizations, and may have different permission levels in each.
- `User`
  - GitHub users, identified by email address. Users can have roles within Organizations, Teams, and Repositories.
- `Team`
  - Groups of users within an organizaiton. They can be nested. Teams can have roles within Repositories.
- `Repository`
  - GitHub repositories, each is associated with a single organization.
- `Issue`
  - GitHub issues; each is associated with a single repository.

### Roles

The following role models were all created by extending mixins generated by
the
[`resource_role_class()`](https://docs.osohq.com/using/frameworks/sqlalchemy.html#sqlalchemy_oso.roles.resource_role_class)
method in `sqlalchemy-oso.roles`. All roles created using
`resource_role_class` are associated with both a user model and a resource
model through many-to-one relationships. In this way, the roles essentiall
act as a through-table for a many-to-many relationship between the user and
resource models.

- `OrganizationRole`
  - Roles scoped to organizations; each is associated with a single `Organization`.
  - Assigned to instances of `User`.
  - The role levels are: Owner, Member, and Billing Manager.
- `TeamRole`
  - Roles scoped to teams; each is associated with a single `Team`.
  - Assigned to instances of `User`.
  - The role levels are: Maintainer, Member.
- `RepositoryRole`
  - Roles scoped to repositories; each is associated with a single `Repository`.
  - The role levels are: Admin, Maintain, Write, Triage, Read.
  - Assigned to instances of `User`.
  - Has an additional many-to-one relationship to `Team`, configured by
    customizing the class. This allows repository roles to be assigned to both
    individual users and teams.

### Model hierarchy

Roles scoped to one resource model generally apply access control not only to
the resource they are scoped to, but also to resources nested within that
resource. This is a common pattern for applications with a hierarchical data
model.

For example, the `OrganizationRole` model controls access to organizations,
teams, and repositories.

```

       Organizations ------------> OrganizationRoles: - Owner
             |                                        - Member
    +---+----+--------+                               - Billing Manager
    |   |             |
    | Teams ---------------------> TeamRoles: - Maintainer
    |   |             |                       - Member
    |   |             |
    +---+---+    Repositories ---> RepositoryRoles: - Admin
    |       |         |                             - Maintain
  Users   Teams     Issues                          - Write
                                                    - Triage
                                                    - Read

```

## Running the App

To run the application, complete the following steps:

1. Set up a virtual environment and install required packages

   ```
   $ python -m venv venv/

   $ pip install -r requirements.txt
   ```

2. [OPTIONAL] Set the `FLASK_APP` environment variable so that the app will
   load fixture data upon creation. You can view the fixture data in
   `app/fixtures.py`. You should only need to load the fixture data once, which
   will create the `roles.db` file.

   ```
   $ export FLASK_APP="app:create_app(None, True)"
   ```

3. Run the server

   ```
   $ flask run
   * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
   ```

   Once the server is running, you can make requests to the REST API using
   cURL. Make sure to include the `--header "user: user@email.com"` header,
   which the app uses for pseudo-authentication:

   ```
   $ curl --header "user: mike@monsters.com" localhost:5000/orgs
   {"orgs":[{"id":2,"name":"Monsters Inc."}]}
   ```

## REST API

The app exposes the following HTTP endpoints:

### GET "/"

Returns the current user, or asks you to log in

```
$ curl --header "user: mike@monsters.com" localhost:5000/
{"email":"mike@monsters.com","id":4}
```

### GET "/orgs"

Returns a list of the current user's authorized organizations.

```
$ curl --header "user: mike@monsters.com" localhost:5000/orgs
{"orgs":[{"id":2,"name":"Monsters Inc."}]}
```

### GET "/orgs/<int:org_id>/repos"

Returns a list of the current user's repositories within organization `org_id`.
Users must be a member of the organization to reach this endpoint.
Users can see every repository that the have the `"READ"` role for.

```
$ curl --header "user: mike@monsters.com" localhost:5000/orgs/2/repos
{"repos":[{"id":2,"name":"Paperwork"}]}
```

```
$ curl --header "user: mike@monsters.com" localhost:5000/orgs/1/repos
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<title>403 Forbidden</title>
<h1>Forbidden</h1>
<p>Unauthorized</p>
```

### GET "/orgs/<int:org_id>/repos/<int:repo_id>"

### GET "/orgs/<int:org_id>/repos/<int:repo_id>/issues"

### GET "/orgs/<int:org_id>/repos/<int:repo_id>/roles"

### POST "/orgs/<int:org_id>/repos/<int:repo_id>/roles"

### GET "/orgs/<int:org_id>/teams"

### GET "/orgs/<int:org_id>/teams/<int:team_id>"

### GET "/orgs/<int:org_id>/billing"

### GET "/orgs/<int:org_id>/roles"
