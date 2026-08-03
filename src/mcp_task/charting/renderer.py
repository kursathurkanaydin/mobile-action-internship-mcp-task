from datetime import datetime


def best_rank_series(history: list[dict], device: str | None = None) -> list[tuple[datetime, int]]:
    """Collapse raw {rank, date, appKind} entries to one rank per day, sorted by date.

    With device=None, entries from every device are merged, keeping the best
    (lowest) rank per day. With device="IPHONE"/"IPAD", only that device's
    entries are considered. Used by the dashboard for its per-device chart
    series and stat cards/table, so all three work off the exact same numbers.
    """
    best_by_date: dict[datetime, int] = {}
    for entry in history:
        if device is not None and entry.get("appKind") != device:
            continue
        rank = entry.get("rank")
        if rank is None:
            continue
        entry_date = datetime.fromisoformat(entry["date"])
        if entry_date not in best_by_date or rank < best_by_date[entry_date]:
            best_by_date[entry_date] = rank
    return sorted(best_by_date.items())
