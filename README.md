# Effective Auth API

This project demonstrates **session-based authentication** and **role-based access control (RBAC)** using Django REST Framework.

## Roles and permissions model

We use the standard Django `User` model plus an explicit `UserProfile.role` field:

```python
class UserProfile(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, ...)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
```

- **Regular user** (`role = "user"`)
  - Can:
    - Register and log in via custom session endpoints
    - View and update their own profile
    - Soft-delete (deactivate) their own account
    - Access **public** resources
    - Access **own** resources (mocked) where they are the owner
  - Cannot:
    - Access **admin-only** resources
    - Access **manager** resources
    - See data owned by other users

- **Manager** (`role = "manager"`)
  - Can:
    - Everything a regular user can
    - Access **manager resources** (e.g. see all team projects)
    - Access **own** resources
  - Cannot:
    - Access **admin-only** resources

- **Admin** (`role = "admin"`)
  - Can:
    - Access **all** resources, including admin-only
    - View any user's "own" resources (for debugging/auditing)


## RBAC mock endpoints

To illustrate how rights separation works, the API exposes mock endpoints under `api/rights/`:

- `GET /api/rights/public/`
  - **Access**: any authenticated user
  - **Returns**: a static list of public resources

- `GET /api/rights/user-projects/`
  - **Access**: any authenticated user
  - **Logic**:
    - Returns a static list of "projects" filtered to the current user as owner.
  - **Forbidden**:
    - Not used here; every authenticated user has at least their own projects.

- `GET /api/rights/manager-projects/`
  - **Access**: only users with `profile.role="manager"` or `"admin"`
  - **Logic**:
    - If the user is manager/admin -> returns a mock list of "team projects".
    - Otherwise -> `403 Forbidden` with a message `"You are not allowed to view manager projects."`

- `GET /api/rights/admin-report/`
  - **Access**: only users with `profile.role="admin"`

## Admin role management endpoint

To demonstrate changing roles dynamically, admins can call:

- `PATCH /api/admin/users/{user_id}/role/`
  - **Access**: only users whose `profile.role="admin"`
  - **Request body**:
    - `role` — one of `"user"`, `"manager"`, `"admin"`
  - **Effect**:
    - Updates the target user's `UserProfile.role`.
  - **Forbidden**:
    - Non-admin callers receive `403 Forbidden`.
  - **Logic**:
    - If the user is an admin -> returns a mock "system report" object.
    - Otherwise -> `403 Forbidden` with `"You are not allowed to view admin report."`

These endpoints do **not** touch the database. Instead, they:

1. Inspect the authenticated user (`request.user`) resolved from the custom session.
2. Decide which "mock" objects are visible.
3. Either:
   - Return the objects, or
   - Return a `403 Forbidden` error when the user does not have enough rights.
   - Return a `401 Unauthenticated` error when user are not logged in.
