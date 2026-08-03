class ToolError(Exception):
    """Base for clean, user-facing tool errors.

    .message is always safe to show to the user/model. .status_code is set
    for upstream API failures (MobileActionAPIError) and stays None for
    everything else (bad input, lookup-not-found, etc.), so every subclass
    can be caught and converted the same way via to_error_response.
    """

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def to_error_response(exc: ToolError) -> dict:
    """Shape any ToolError into the {"error", "status_code"} dict tools return on failure."""
    return {"error": exc.message, "status_code": exc.status_code}
