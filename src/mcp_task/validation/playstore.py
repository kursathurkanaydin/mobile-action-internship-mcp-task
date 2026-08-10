import re
from urllib.parse import parse_qs, urlparse

from mcp_task.validation.common import InputValidationError

_PACKAGE_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")


def require_package_name(track_id: str) -> str:
    """Validate a Google Play package id, accepted either bare or as a Play Store app URL.

    Users commonly have a Play Store link (e.g.
    "https://play.google.com/store/apps/details?id=com.facebook.katana&hl=tr")
    rather than the bare package id, so a play.google.com URL's "id" query
    param is extracted automatically instead of requiring the caller to do it.
    """
    stripped = (track_id or "").strip()
    if stripped.startswith(("http://", "https://")):
        parsed = urlparse(stripped)
        if "play.google.com" in parsed.netloc:
            query_id = parse_qs(parsed.query).get("id", [None])[0]
            if query_id:
                stripped = query_id

    if not _PACKAGE_NAME_RE.match(stripped):
        raise InputValidationError(
            f"'{track_id}' is not a valid Google Play track id — it must be a package name "
            "in reverse-domain form (e.g. 'com.facebook.katana'), or a Play Store app URL "
            "containing '?id=...' (e.g. 'https://play.google.com/store/apps/details?id=com.facebook.katana')."
        )
    return stripped


def require_package_name_list(track_ids: str, min_count: int = 1, max_count: int = 300) -> list[str]:
    """Parse+validate a comma-separated list of Google Play package ids, e.g. for batch lookups."""
    raw_ids = [part.strip() for part in (track_ids or "").split(",") if part.strip()]
    if not raw_ids:
        raise InputValidationError(
            "'track_ids' cannot be empty — provide one or more comma-separated Google Play package ids."
        )

    unique_ids = list(dict.fromkeys(raw_ids))  # de-dupe, keep first-seen order
    validated_ids = [require_package_name(raw_id) for raw_id in unique_ids]

    if len(validated_ids) < min_count:
        raise InputValidationError(f"Need at least {min_count} distinct app ids, got {len(validated_ids)}.")
    if len(validated_ids) > max_count:
        raise InputValidationError(
            f"Too many apps given at once: {len(validated_ids)}, but at most {max_count} are supported."
        )
    return validated_ids
