import re
from datetime import datetime

from mcp_task.errors import ToolError

_COUNTRY_CODE_RE = re.compile(r"^[A-Za-z]{2}$")
_VALID_DEVICES = {"IPHONE", "IPAD"}


class InputValidationError(ToolError):
    """A clean, user-facing error for a bad tool input (empty/malformed/out of range)."""


def require_track_id(track_id: int) -> int:
    if track_id is None or track_id <= 0:
        raise InputValidationError(
            f"'{track_id}' is not a valid App Store track id — it must be a positive number "
            "(e.g. 529479190). Use get_app_store_id to look one up by app name."
        )
    return track_id


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


def require_device(device: str | None, required: bool = True) -> str | None:
    if device is None or not device.strip():
        if required:
            raise InputValidationError("'device' is required and must be 'IPHONE' or 'IPAD'.")
        return None
    normalized = device.strip().upper()
    if normalized not in _VALID_DEVICES:
        raise InputValidationError(f"'{device}' is not a valid device — it must be 'IPHONE' or 'IPAD'.")
    return normalized


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


def require_track_id_list(track_ids: str, min_count: int = 2, max_count: int = 5) -> list[int]:
    """Parse+validate a comma-separated list of track ids, e.g. for app comparisons or batch lookups."""
    raw_ids = [part.strip() for part in (track_ids or "").split(",") if part.strip()]
    if not raw_ids:
        raise InputValidationError(
            "'track_ids' cannot be empty — provide one or more comma-separated App Store ids."
        )

    parsed_ids = []
    for raw_id in raw_ids:
        try:
            parsed_ids.append(int(raw_id))
        except ValueError:
            raise InputValidationError(f"'{raw_id}' is not a valid App Store track id — expected a number.") from None

    unique_ids = list(dict.fromkeys(parsed_ids))  # de-dupe, keep first-seen order
    for track_id in unique_ids:
        require_track_id(track_id)

    if len(unique_ids) < min_count:
        raise InputValidationError(f"Need at least {min_count} distinct app ids, got {len(unique_ids)}.")
    if len(unique_ids) > max_count:
        raise InputValidationError(
            f"Too many apps given at once: {len(unique_ids)}, but at most {max_count} are supported."
        )
    return unique_ids
