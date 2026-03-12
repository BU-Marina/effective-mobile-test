from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    # Registration
    path("auth/custom/register/", views.RegistrationView.as_view(), name="custom-register"),
    # Custom session auth (no Django login/logout/authenticate)
    path("auth/custom/login/", views.CustomLoginView.as_view(), name="custom-login"),
    path("auth/custom/logout/", views.CustomLogoutView.as_view(), name="custom-logout"),
    path("auth/custom/me/", views.CustomCurrentUserView.as_view(), name="custom-current-user"),
    # RBAC mock endpoints
    path("rights/public/", views.PublicResourcesView.as_view(), name="rights-public"),
    path("rights/user-projects/", views.UserProjectsView.as_view(), name="rights-user-projects"),
    path("rights/manager-projects/", views.ManagerProjectsView.as_view(), name="rights-manager-projects"),
    path("rights/admin-report/", views.AdminReportView.as_view(), name="rights-admin-report"),
    # Admin role management
    path(
        "admin/users/<int:user_id>/role/",
        views.AdminChangeUserRoleView.as_view(),
        name="admin-change-user-role",
    ),
    path(
        "admin/users/rights/",
        views.AdminListUserRightsView.as_view(),
        name="admin-list-user-rights",
    ),
]
