from __future__ import annotations

from typing import Any

from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]):
    """Return API errors using one predictable response envelope."""
    response = exception_handler(exc, context)

    if response is None:
        return response

    details = response.data

    if isinstance(details, dict) and "detail" in details:
        message = str(details["detail"])
    else:
        message = "Invalid request."

    response.data = {
        "error": {
            "code": response.status_code,
            "message": message,
            "details": details,
        }
    }

    return response