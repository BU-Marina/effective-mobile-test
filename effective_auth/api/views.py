from django.contrib.auth import get_user_model

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import CustomSessionAuthentication, SESSION_USER_ID_KEY
from .models import UserProfile
from .serializers import (
    LoginRequestSerializer,
    RegistrationRequestSerializer,
    UserRoleUpdateSerializer,
    UserSerializer,
    UserUpdateRequestSerializer,
)

User = get_user_model()


# --- Custom session auth (no Django login/logout/authenticate) ---


def _user_payload(user):
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", UserProfile.Role.USER) if profile else UserProfile.Role.USER
    return {
        "id": user.pk,
        "username": user.username,
        "email": getattr(user, "email", "") or "",
        "first_name": getattr(user, "first_name", "") or "",
        "last_name": getattr(user, "last_name", "") or "",
        "role": role,
    }


class RegistrationView(APIView):
    """
    Register a new user using email as username.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        request=RegistrationRequestSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request: Request) -> Response:
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        email = request.data.get("email")
        password = request.data.get("password")
        password_repeat = request.data.get("password_repeat")

        missing = [
            field
            for field, value in [
                ("first_name", first_name),
                ("last_name", last_name),
                ("email", email),
                ("password", password),
                ("password_repeat", password_repeat),
            ]
            if not value
        ]
        if missing:
            return Response(
                {"detail": f"Missing fields: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if password != password_repeat:
            return Response(
                {"detail": "Passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Basic uniqueness check by email (used as username)
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "User with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
        return Response(_user_payload(user), status=status.HTTP_201_CREATED)


class CustomLoginView(APIView):
    """
    Create a session by validating credentials manually.
    Does not use Django's authenticate() or login().
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # no auth for login

    @extend_schema(
        request=LoginRequestSerializer,
        responses={200: UserSerializer},
    )
    def post(self, request: Request) -> Response:
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "User account is disabled"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Store user id in session (no Django login())
        request.session[SESSION_USER_ID_KEY] = user.pk
        request.session.modified = True

        return Response(_user_payload(user), status=status.HTTP_200_OK)


class CustomLogoutView(APIView):
    """
    Destroy the current session by clearing session key.
    Does not use Django's logout().
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={204: None})
    def post(self, request: Request) -> Response:
        request.session.pop(SESSION_USER_ID_KEY, None)
        request.session.modified = True
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomCurrentUserView(APIView):
    """
    Return the current user identified by custom session.
    Uses CustomSessionAuthentication (no Django auth session).
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request) -> Response:
        return Response(
            _user_payload(request.user),
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=UserUpdateRequestSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request: Request) -> Response:
        user = request.user
        serializer = UserUpdateRequestSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_email = data.get("email")
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                return Response(
                    {"detail": "User with this email already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.email = new_email
            user.username = new_email

        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]

        user.save(update_fields=["email", "username", "first_name", "last_name"])
        return Response(_user_payload(user), status=status.HTTP_200_OK)

    @extend_schema(responses={204: None})
    def delete(self, request: Request) -> Response:
        """
        Soft-delete the current user account.
        Sets is_active=False and logs out via custom session.
        """
        user = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])

        # Clear custom session so user is logged out
        request.session.pop(SESSION_USER_ID_KEY, None)
        request.session.modified = True

        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicResourcesView(APIView):
    """
    Mock endpoint returning public resources for any authenticated user.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> Response:
        data = {
            "resources": [
                {"id": 1, "name": "Public Article 1"},
                {"id": 2, "name": "Public FAQ"},
            ]
        }
        return Response(data, status=status.HTTP_200_OK)


class UserProjectsView(APIView):
    """
    Mock endpoint returning projects owned by the current user.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> Response:
        user = request.user
        data = {
            "owner": user.email or user.username,
            "projects": [
                {"id": 101, "name": "Personal Project A"},
                {"id": 102, "name": "Personal Project B"},
            ],
        }
        return Response(data, status=status.HTTP_200_OK)


class ManagerProjectsView(APIView):
    """
    Mock endpoint returning manager-level resources.
    Only users with role=manager or role=admin are allowed.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={200: dict, 403: dict})
    def get(self, request: Request) -> Response:
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.role not in (UserProfile.Role.MANAGER, UserProfile.Role.ADMIN):
            return Response(
                {"detail": "You are not allowed to view manager projects."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = {
            "manager": user.email or user.username,
            "team_projects": [
                {"id": 201, "name": "Team Project X"},
                {"id": 202, "name": "Team Project Y"},
            ],
        }
        return Response(data, status=status.HTTP_200_OK)


class AdminReportView(APIView):
    """
    Mock endpoint returning an admin-only system report.
    Only users with role=admin are allowed.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={200: dict, 403: dict})
    def get(self, request: Request) -> Response:
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.role != UserProfile.Role.ADMIN:
            return Response(
                {"detail": "You are not allowed to view admin report."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = {
            "generated_by": user.email or user.username,
            "metrics": {
                "active_users": 123,
                "inactive_users": 7,
                "projects_total": 42,
            },
        }
        return Response(data, status=status.HTTP_200_OK)


class AdminChangeUserRoleView(APIView):
    """
    Admin-only endpoints to inspect and change another user's role.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={200: UserSerializer, 403: dict, 404: dict})
    def get(self, request: Request, user_id: int) -> Response:
        """
        View a single user's rights (role and basic info).
        Admins only.
        """
        acting_user = request.user
        acting_profile, _ = UserProfile.objects.get_or_create(user=acting_user)
        if acting_profile.role != UserProfile.Role.ADMIN:
            return Response(
                {"detail": "Only admin users can view user rights."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        UserProfile.objects.get_or_create(user=target_user)
        return Response(_user_payload(target_user), status=status.HTTP_200_OK)

    @extend_schema(
        request=UserRoleUpdateSerializer,
        responses={200: UserSerializer, 403: dict, 404: dict},
    )
    def patch(self, request: Request, user_id: int) -> Response:
        """
        Change a user's role (user/manager/admin).
        Admins only.
        """
        acting_user = request.user
        acting_profile, _ = UserProfile.objects.get_or_create(user=acting_user)
        if acting_profile.role != UserProfile.Role.ADMIN:
            return Response(
                {"detail": "Only admin users can change roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        profile.role = new_role
        profile.save(update_fields=["role"])

        return Response(_user_payload(target_user), status=status.HTTP_200_OK)


class AdminListUserRightsView(APIView):
    """
    Admin-only endpoint to list all users with their roles and status.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomSessionAuthentication]

    @extend_schema(responses={200: dict, 403: dict})
    def get(self, request: Request) -> Response:
        acting_user = request.user
        acting_profile, _ = UserProfile.objects.get_or_create(user=acting_user)
        if acting_profile.role != UserProfile.Role.ADMIN:
            return Response(
                {"detail": "Only admin users can view user rights."},
                status=status.HTTP_403_FORBIDDEN,
            )

        items = []
        for user in User.objects.all().order_by("id"):
            profile, _ = UserProfile.objects.get_or_create(user=user)
            items.append(
                {
                    "id": user.pk,
                    "email": user.email,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "role": profile.role,
                }
            )

        return Response({"users": items}, status=status.HTTP_200_OK)
