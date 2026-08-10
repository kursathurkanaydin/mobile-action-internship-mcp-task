from datetime import date

from mcp_task.charting.renderer import best_rank_series


def _entry(date: str, rank, device: str = "IPHONE"):
    return {"trackId": 1, "keyword": "strategy", "rank": rank, "countryCode": "US", "date": date, "appKind": device}


class TestBestRankSeries:
    def test_picks_lower_rank_across_devices_per_day(self):
        history = [
            _entry("2026-07-01T00:00:00", 20, "IPHONE"),
            _entry("2026-07-01T00:00:00", 15, "IPAD"),
        ]
        assert best_rank_series(history) == [(date(2026, 7, 1), 15)]

    def test_ignores_entries_with_missing_rank(self):
        history = [_entry("2026-07-01T00:00:00", None), _entry("2026-07-02T00:00:00", 10)]
        result = best_rank_series(history)
        assert len(result) == 1
        assert result[0][1] == 10

    def test_sorts_by_date_ascending(self):
        history = [
            _entry("2026-07-03T00:00:00", 5),
            _entry("2026-07-01T00:00:00", 8),
            _entry("2026-07-02T00:00:00", 3),
        ]
        dates = [point[0] for point in best_rank_series(history)]
        assert dates == sorted(dates)

    def test_empty_history_returns_empty_list(self):
        assert best_rank_series([]) == []

    def test_device_filter_only_considers_that_devices_entries(self):
        history = [
            _entry("2026-07-01T00:00:00", 20, "IPHONE"),
            _entry("2026-07-01T00:00:00", 15, "IPAD"),
        ]
        assert best_rank_series(history, device="IPHONE") == [(date(2026, 7, 1), 20)]
        assert best_rank_series(history, device="IPAD") == [(date(2026, 7, 1), 15)]

    def test_device_filter_excludes_days_only_present_on_other_device(self):
        history = [
            _entry("2026-07-01T00:00:00", 20, "IPHONE"),
            _entry("2026-07-02T00:00:00", 10, "IPAD"),
        ]
        assert best_rank_series(history, device="IPHONE") == [(date(2026, 7, 1), 20)]
        assert best_rank_series(history, device="IPAD") == [(date(2026, 7, 2), 10)]

    def test_device_filter_with_no_matching_entries_returns_empty_list(self):
        history = [_entry("2026-07-01T00:00:00", 20, "IPHONE")]
        assert best_rank_series(history, device="IPAD") == []

    def test_different_crawl_times_on_the_same_calendar_day_are_merged_not_split(self):
        # regression guard: MobileAction's exact crawl timestamp for "the
        # same day" varies (e.g. between different keywords' series in a
        # multi-keyword chart) — merging by full datetime instead of just
        # the date would scatter one logical day across several x-axis
        # slots and break the chart's connecting lines (see renderer.py's
        # docstring). Two entries for the same calendar day, different
        # times, must collapse to ONE point, keeping the better rank.
        history = [
            _entry("2026-07-01T01:16:20", 20),
            _entry("2026-07-01T07:12:08", 15),
        ]
        assert best_rank_series(history) == [(date(2026, 7, 1), 15)]
