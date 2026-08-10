from datetime import date, datetime


def best_rank_series(history: list[dict], device: str | None = None) -> list[tuple[date, int]]:
    """Collapse raw {rank, date, appKind} entries to one rank per calendar day, sorted by date.

    With device=None, entries from every device are merged, keeping the best
    (lowest) rank per day. With device="IPHONE"/"IPAD", only that device's
    entries are considered. Used by the dashboard for its per-device chart
    series and stat cards/table, so all three work off the exact same numbers.

    Keys on the calendar date only (entry["date"]'s time-of-day is dropped),
    not the full timestamp. MobileAction's exact crawl time for "the same
    day" varies — between devices, and especially between different
    apps/keywords when the dashboard merges several series onto one shared
    x-axis. Keying on the full datetime would put each series' points at a
    slightly different x position for what's logically the same day; with
    the chart's spanGaps=False, every point would then be isolated by nulls
    on both sides and no connecting line would ever be drawn (each series
    scattered across its own timestamps rather than sharing calendar-day
    slots with the others).
    """
    best_by_date: dict[date, int] = {}
    for entry in history:
        if device is not None and entry.get("appKind") != device:
            continue
        rank = entry.get("rank")
        if rank is None:
            continue
        entry_date = datetime.fromisoformat(entry["date"]).date()
        if entry_date not in best_by_date or rank < best_by_date[entry_date]:
            best_by_date[entry_date] = rank
    return sorted(best_by_date.items())
