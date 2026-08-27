import logging

from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("referralflow.exceptions")


class ApplicationError(drf_exceptions.APIException):
    """Base class for domain errors raised by the service layer."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be processed."
    default_code = "application_error"


def _error_code_from_exception(exc):
    code = getattr(exc, "default_code", None)
    return code or exc.__class__.__name__.lower()


def _flatten_details(detail):
    if isinstance(detail, (list, dict)):
        return detail
    return {"non_field_errors": [str(detail)]} if not isinstance(detail, str) else str(detail)


def custom_exception_handler(exc, context):
    """
    Normalizes every API error - validation failures, permission denials,
    domain errors, and unexpected exceptions - into a single response shape:

        {"error": {"code": str, "message": str, "details": dict|list|str|null}}

    so API consumers never have to branch on which layer raised the error.
    """
    if isinstance(exc, Http404):
        exc = drf_exceptions.NotFound()

    response = drf_exception_handler(exc, context)

    if response is None:
        request = context.get("request")
        logger.exception(
            "Unhandled exception while processing request",
            extra={"path": getattr(request, "path", "unknown")},
        )
        return Response(
            {
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    message = exc.default_detail if hasattr(exc, "default_detail") else str(exc)
    response.data = {
        "error": {
            "code": _error_code_from_exception(exc),
            "message": str(message),
            "details": _flatten_details(response.data),
        }
    }
    return response
