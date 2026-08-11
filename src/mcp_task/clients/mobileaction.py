import logging

import httpx

from mcp_task import credit_tracking
from mcp_task.config import MOBILEACTION_API_KEY, MOBILEACTION_BASE_URL
from mcp_task.errors import ToolError

logger = logging.getLogger(__name__)

_STATUS_MESSAGES = {
    401: "Authentication failed: the MobileAction API key is invalid or missing.",
    403: "Access denied: this API key does not have permission for this endpoint.",
    404: "Not found: no data exists for the given parameters (check trackId/countryCode/keyword).",
    429: "Rate limit or credit limit exceeded: too many requests, or the API key is out of credits.",
}


class MobileActionAPIError(ToolError):
    """A clean, user-facing error for any failure talking to the MobileAction API.

    error_type is derived from status_code when not given explicitly: no
    status_code means the request never got a response (network failure),
    404 means the resource doesn't exist, anything else is an upstream API
    problem unrelated to the caller's input.
    """

    def __init__(self, message: str, status_code: int | None = None, error_type: str | None = None):
        if error_type is None:
            if status_code is None:
                error_type = "network"
            elif status_code == 404:
                error_type = "not_found"
            else:
                error_type = "upstream_api"
        super().__init__(message, status_code=status_code, error_type=error_type)


def _build_params(params: dict | None) -> dict:
    request_params = {k: v for k, v in (params or {}).items() if v is not None}
    request_params["token"] = MOBILEACTION_API_KEY
    return request_params


def _handle_response(response: httpx.Response, path: str, raw: bool = False) -> dict | list | str | None:
    """Shared by get()/post(): credit-cost logging, error handling, and body parsing.

    Returns None for a 2xx response with an empty body (e.g. the Google Play
    app-detail endpoint returns 204 for an unrecognized package id) rather
    than crashing on response.json() with nothing to parse. raw=True skips
    JSON parsing and returns response.text instead - the one MobileAction
    endpoint found so far that needs this (app-match) replies with a bare
    text/plain body, not JSON, so response.json() would raise.
    """
    credit_remaining = response.headers.get("X-Credit-Remaining")
    credit_cost = response.headers.get("X-Credit-Cost")
    if credit_remaining is not None:
        logger.info("MobileAction call cost=%s remaining=%s path=%s", credit_cost, credit_remaining, path)
        credit_tracking.record(credit_cost, credit_remaining)

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

    if not response.content:
        return None

    return response.text if raw else response.json()


def get(path: str, params: dict | None = None, raw: bool = False) -> dict | list | str | None:
    """Make an authenticated GET request to the MobileAction API.

    Appends the API token, logs the credit cost/remaining from response headers,
    and raises MobileActionAPIError with a clean message on any failure (network
    error or non-2xx response) instead of letting a raw exception propagate.
    Pass raw=True for the rare endpoint that replies with plain text instead
    of JSON (see _handle_response).
    """
    url = f"{MOBILEACTION_BASE_URL}{path}"

    try:
        response = httpx.get(url, params=_build_params(params), timeout=15)
    except httpx.RequestError as exc:
        raise MobileActionAPIError(f"Network error while calling MobileAction API: {exc}") from exc

    return _handle_response(response, path, raw=raw)


def post(path: str, params: dict | None = None, json: dict | list | None = None) -> dict | list | None:
    """Make an authenticated POST request to the MobileAction API.

    Same auth/error-handling/credit-logging behavior as get() (see
    _handle_response), but for the handful of MobileAction endpoints that
    take their real payload as a JSON body instead of query params - e.g.
    visibility-score-history, which expects a bare JSON array of trackIds
    as the body rather than an object, hence json accepting dict | list.
    Only use this for read-only/compute endpoints (a report or estimate
    that happens to need POST because its input is too large/structured for
    a query string) - endpoints that mutate dashboard state (e.g. adding or
    deleting tracked keywords) are a different, higher-stakes category not
    covered by this function yet.
    """
    url = f"{MOBILEACTION_BASE_URL}{path}"

    try:
        response = httpx.post(url, params=_build_params(params), json=json, timeout=15)
    except httpx.RequestError as exc:
        raise MobileActionAPIError(f"Network error while calling MobileAction API: {exc}") from exc

    return _handle_response(response, path)
