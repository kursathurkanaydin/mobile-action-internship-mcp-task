import logging

import httpx

from mcp_task.config import MOBILEACTION_API_KEY, MOBILEACTION_BASE_URL
from mcp_task.errors import ToolInputError

logger = logging.getLogger("mcp_task.ma_client")

_STATUS_MESSAGES = {
    401: "Authentication failed: the MobileAction API key is invalid or missing.",
    403: "Access denied: this API key does not have permission for this endpoint.",
    404: "Not found: no data exists for the given parameters (check trackId/countryCode/keyword).",
    429: "Rate limit or credit limit exceeded: too many requests, or the API key is out of credits.",
}


class MobileActionAPIError(ToolInputError):
    """A clean, user-facing error for any failure talking to the MobileAction API."""


def get(path: str, params: dict | None = None) -> dict | list:
    """Make an authenticated GET request to the MobileAction API.

    Appends the API token, logs the credit cost/remaining from response headers,
    and raises MobileActionAPIError with a clean message on any failure (network
    error or non-2xx response) instead of letting a raw exception propagate.
    """
    url = f"{MOBILEACTION_BASE_URL}{path}"
    request_params = {k: v for k, v in (params or {}).items() if v is not None}
    request_params["token"] = MOBILEACTION_API_KEY

    try:
        response = httpx.get(url, params=request_params, timeout=15)
    except httpx.RequestError as exc:
        raise MobileActionAPIError(f"Network error while calling MobileAction API: {exc}") from exc

    credit_remaining = response.headers.get("X-Credit-Remaining")
    credit_cost = response.headers.get("X-Credit-Cost")
    if credit_remaining is not None:
        logger.info("MobileAction call cost=%s remaining=%s path=%s", credit_cost, credit_remaining, path)

    if response.status_code >= 400:
        message = _STATUS_MESSAGES.get(
            response.status_code,
            f"MobileAction API returned an unexpected error (HTTP {response.status_code}).",
        )
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise MobileActionAPIError(f"{message} Details: {detail}", status_code=response.status_code)

    return response.json()
