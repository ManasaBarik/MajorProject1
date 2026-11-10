import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)

_STATUS_CODE_MAP = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHENTICATED",
    403: "UNAUTHORIZED",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "BUSINESS_ERROR",
    429: "RATE_LIMITED",
    500: "SERVER_ERROR",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {
                "success": False,
                "error": {
                    "code": "SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {},
                },
            },
            status=500,
        )
    detail = response.data
    if isinstance(detail, dict):
        message = detail.get("detail", "Request could not be completed.")
        details = {k: v for k, v in detail.items() if k != "detail"} if detail != {"detail": message} else detail
    elif isinstance(detail, list):
        message = "; ".join(str(x) for x in detail) if detail else "Request could not be completed."
        details = {"non_field_errors": detail}
    else:
        message = str(detail)
        details = {}
    code = _STATUS_CODE_MAP.get(response.status_code, "VALIDATION_ERROR" if response.status_code < 500 else "SERVER_ERROR")
    response.data = {
        "success": False,
        "error": {
            "code": code,
            "message": str(message),
            "details": details,
        },
    }
    return response
