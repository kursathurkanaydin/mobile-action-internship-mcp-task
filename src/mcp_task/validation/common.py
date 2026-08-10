import re
from datetime import datetime

from mcp_task.errors import ToolError

_COUNTRY_CODE_RE = re.compile(r"^[A-Za-z]{2}$")


class InputValidationError(ToolError):
    """A clean, user-facing error for a bad tool input (empty/malformed/out of range)."""


def require_country_code(country_code: str, upper: bool = True) -> str:
    stripped = (country_code or "").strip()
    if not _COUNTRY_CODE_RE.match(stripped):
        raise InputValidationError(
            f"'{country_code}' is not a valid country code — it must be a two-letter "
            "App Store storefront code, e.g. 'US' or 'TR'."
        )
    return stripped.upper() if upper else stripped


def require_text(value: str, field_name: str) -> str:
    stripped = (value or "").strip()
    if not stripped:
        raise InputValidationError(f"'{field_name}' cannot be empty.")
    return stripped


def require_date(value: str, field_name: str) -> str:
    stripped = (value or "").strip()
    try:
        datetime.strptime(stripped, "%Y-%m-%d")
    except ValueError:
        raise InputValidationError(
            f"'{value}' is not a valid date for '{field_name}' — expected YYYY-MM-DD format, e.g. '2026-07-01'."
        ) from None
    return stripped


def require_date_range(start_date: str, end_date: str, max_days: int = 30) -> None:
    start = datetime.strptime(require_date(start_date, "start_date"), "%Y-%m-%d").date()
    end = datetime.strptime(require_date(end_date, "end_date"), "%Y-%m-%d").date()

    if start > end:
        raise InputValidationError(f"start_date ({start_date}) must be on or before end_date ({end_date}).")

    span_days = (end - start).days + 1
    if span_days > max_days:
        raise InputValidationError(
            f"Date range too large: {start_date} to {end_date} is {span_days} days, but this "
            f"endpoint supports at most {max_days} days per request."
        )


def require_positive_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if value <= 0:
        raise InputValidationError(f"'{field_name}' must be a positive number, got {value}.")
    return value
