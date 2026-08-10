import functools
import logging

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Base for clean, user-facing tool errors.

    .message is always safe to show to the user/model. .status_code is set
    for upstream API failures (MobileActionAPIError) and stays None for
    everything else (bad input, lookup-not-found, etc.), so every subclass
    can be caught and converted the same way via to_error_response.

    .error_type is a coarse, machine-readable category a caller can branch
    on without parsing .message — status_code alone can't distinguish "bad
    input" from "not found" from "network hiccup", since all three leave it
    None. One of:
      "validation"   - bad/missing input; retrying without changing the
                        request won't help.
      "not_found"    - the requested resource doesn't exist; same as above.
      "upstream_api" - the external API rejected the request (rate limit,
                        auth, server error) for a reason unrelated to input.
      "network"      - couldn't reach the external service at all; often
                        transient, safe to retry as-is.
      "internal"     - default, and what handle_tool_errors falls back to
                        for an exception that wasn't anticipated/categorized.
    Subclasses set a sensible class-level default; individual raise sites
    can still override it via the constructor when one subclass covers more
    than one of these situations (see MobileActionAPIError, AppLookupError).
    """

    error_type: str = "internal"

    def __init__(self, message: str, status_code: int | None = None, error_type: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        if error_type is not None:
            self.error_type = error_type


def to_error_response(exc: ToolError) -> dict:
    """Shape any ToolError into the {"error", "status_code", "error_type"} dict tools return on failure."""
    return {"error": exc.message, "status_code": exc.status_code, "error_type": exc.error_type}


def handle_tool_errors(fn):
    """Wrap a @mcp.tool function so any failure becomes a clean error dict, not a raw exception.

    Every tool in this codebase is expected to catch ToolError itself and
    return to_error_response(exc), but that's a convention, not something
    enforced anywhere — nothing stops a KeyError from an unexpectedly-shaped
    API response, or a third-party library raising something outside its
    normal error types, from bypassing that convention and leaking a raw
    Python exception straight to the model. This decorator is the actual
    enforcement: it catches ToolError the normal way, and anything else gets
    logged (with a traceback, for debugging) and converted the same way
    instead of propagating.

    Apply it *under* @mcp.tool (mcp.tool needs to sit outermost to register
    the tool), e.g.:

        @mcp.tool
        @handle_tool_errors
        def get_thing(...) -> dict:
            ...
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError as exc:
            return to_error_response(exc)
        except Exception as exc:
            logger.exception("Unexpected error in tool %s", fn.__name__)
            return to_error_response(ToolError(f"Unexpected internal error: {exc}"))

    return wrapper
