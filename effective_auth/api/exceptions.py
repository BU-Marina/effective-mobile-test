from typing import Any, Optional

from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Optional[Response]:
    """
    Ensure unauthenticated errors use 401 status code with a clear message.
    """
    response = drf_exception_handler(exc, context)

    if isinstance(exc, NotAuthenticated):
        # Normalize all unauthenticated errors to 401 with a standard message.
        detail = "Authentication credentials were not provided."
        if response is None:
            return Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)

        response.status_code = status.HTTP_401_UNAUTHORIZED
        # Only override detail when it's missing or very generic.
        if not response.data or "detail" not in response.data:
            response.data = {"detail": detail}

    return response
