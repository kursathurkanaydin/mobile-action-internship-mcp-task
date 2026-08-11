from mcp_task.validation.common import InputValidationError

_VALID_STORES = {"ios", "play"}


def require_store(store: str) -> str:
    normalized = (store or "").strip().lower()
    if normalized not in _VALID_STORES:
        raise InputValidationError(f"'{store}' is not a valid store — it must be 'ios' or 'play'.")
    return normalized
