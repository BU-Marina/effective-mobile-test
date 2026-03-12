"""
Custom session authentication without Django's login()/logout().
Store only user_id in the session and load the user.
"""
from django.contrib.auth import get_user_model

from rest_framework import authentication

User = get_user_model()

# Session key using to store the logged-in user's id (no Django auth backend)
SESSION_USER_ID_KEY = "custom_user_id"


class CustomSessionAuthentication(authentication.BaseAuthentication):
    """
    Authenticate by reading user id from request.session.
    Does not use Django's auth session (_auth_user_id / login() / logout()).
    """

    def authenticate(self, request):
        user_id = request.session.get(SESSION_USER_ID_KEY)

        if user_id is None:
            return None

        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            request.session.pop(SESSION_USER_ID_KEY, None)
            return None

        if not user.is_active:
            request.session.pop(SESSION_USER_ID_KEY, None)
            return None

        return (user, None)
