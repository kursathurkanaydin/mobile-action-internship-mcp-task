from datetime import datetime

from mcp_task.charting.renderer import best_rank_series, render_comparison_chart, render_ranking_history_chart

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _entry(date: str, rank, device: str = "IPHONE"):
    return {"trackId": 1, "keyword": "strategy", "rank": rank, "countryCode": "US", "date": date, "appKind": device}


class TestBestRankSeries:
    def test_picks_lower_rank_across_devices_per_day(self):
        history = [
            _entry("2026-07-01T00:00:00", 20, "IPHONE"),
            _entry("2026-07-01T00:00:00", 15, "IPAD"),
        ]
        assert best_rank_series(history) == [(datetime.fromisoformat("2026-07-01T00:00:00"), 15)]

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


class TestRenderRankingHistoryChart:
    def test_returns_valid_png_bytes(self):
        history = [
            _entry("2026-07-01T00:00:00", 20, "IPHONE"),
            _entry("2026-07-02T00:00:00", 18, "IPHONE"),
            _entry("2026-07-01T00:00:00", 15, "IPAD"),
        ]
        png_bytes = render_ranking_history_chart(history, "strategy", "US", 529479190)
        assert png_bytes.startswith(_PNG_MAGIC)
        assert len(png_bytes) > 0

    def test_handles_empty_history_without_crashing(self):
        png_bytes = render_ranking_history_chart([], "strategy", "US", 529479190)
        assert png_bytes.startswith(_PNG_MAGIC)


class TestRenderComparisonChart:
    def test_returns_valid_png_bytes(self):
        histories_by_app = {
            "Clash of Clans": [_entry("2026-07-01T00:00:00", 12)],
            "Clash Royale": [_entry("2026-07-01T00:00:00", 20)],
        }
        png_bytes = render_comparison_chart(histories_by_app, "strategy", "US")
        assert png_bytes.startswith(_PNG_MAGIC)

    def test_app_with_no_ranked_days_is_skipped_without_crashing(self):
        histories_by_app = {
            "Has Data": [_entry("2026-07-01T00:00:00", 12)],
            "No Data": [_entry("2026-07-01T00:00:00", None)],
        }
        png_bytes = render_comparison_chart(histories_by_app, "strategy", "US")
        assert png_bytes.startswith(_PNG_MAGIC)
