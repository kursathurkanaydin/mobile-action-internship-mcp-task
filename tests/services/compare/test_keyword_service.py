from mcp_task.services.appstore import keyword_service as appstore_ks
from mcp_task.services.compare import keyword_service as compare_ks
from mcp_task.services.playstore import keyword_service as playstore_ks


class TestFetchKeywordMetadata:
    def test_combines_both_stores_under_their_own_keys(self, monkeypatch):
        monkeypatch.setattr(appstore_ks, "fetch_keyword_metadata", lambda country_code, keyword: {"searchVolume": 1})
        monkeypatch.setattr(
            playstore_ks, "fetch_keyword_metadata", lambda country_code, keyword: {"searchVolume": 2}
        )

        result = compare_ks.fetch_keyword_metadata("US", "strategy")
        assert result == {"app_store": {"searchVolume": 1}, "play_store": {"searchVolume": 2}}

    def test_passes_through_country_code_and_keyword_to_both_stores(self, monkeypatch):
        captured = {}

        def fake_appstore(country_code, keyword):
            captured["appstore"] = (country_code, keyword)
            return {}

        def fake_playstore(country_code, keyword):
            captured["playstore"] = (country_code, keyword)
            return {}

        monkeypatch.setattr(appstore_ks, "fetch_keyword_metadata", fake_appstore)
        monkeypatch.setattr(playstore_ks, "fetch_keyword_metadata", fake_playstore)

        compare_ks.fetch_keyword_metadata("TR", "clan")
        assert captured["appstore"] == ("TR", "clan")
        assert captured["playstore"] == ("TR", "clan")


class TestFetchKeywordRanking:
    def test_calls_each_store_with_its_own_track_id(self, monkeypatch):
        captured = {}

        def fake_appstore(track_id, country_code, keywords, date):
            captured["appstore"] = (track_id, country_code, keywords, date)
            return [{"rank": 1}]

        def fake_playstore(track_id, country_code, keywords, date):
            captured["playstore"] = (track_id, country_code, keywords, date)
            return [{"rank": 2}]

        monkeypatch.setattr(appstore_ks, "fetch_keyword_ranking", fake_appstore)
        monkeypatch.setattr(playstore_ks, "fetch_keyword_ranking", fake_playstore)

        result = compare_ks.fetch_keyword_ranking(529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-01")

        assert captured["appstore"] == (529479190, "US", "clan", "2026-07-01")
        assert captured["playstore"] == ("com.supercell.clashofclans", "US", "clan", "2026-07-01")
        assert result == {"app_store": [{"rank": 1}], "play_store": [{"rank": 2}]}

    def test_date_defaults_to_none(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            appstore_ks, "fetch_keyword_ranking", lambda *a: captured.setdefault("appstore_date", a[-1]) or []
        )
        monkeypatch.setattr(
            playstore_ks, "fetch_keyword_ranking", lambda *a: captured.setdefault("playstore_date", a[-1]) or []
        )

        compare_ks.fetch_keyword_ranking(529479190, "com.supercell.clashofclans", "US", "clan")
        assert captured["appstore_date"] is None
        assert captured["playstore_date"] is None


class TestFetchKeywordRankingHistory:
    def test_calls_each_store_with_its_own_track_id(self, monkeypatch):
        captured = {}

        def fake_appstore(track_id, country_code, keyword, start_date, end_date):
            captured["appstore"] = (track_id, country_code, keyword, start_date, end_date)
            return [{"rank": 1}]

        def fake_playstore(track_id, country_code, keyword, start_date, end_date):
            captured["playstore"] = (track_id, country_code, keyword, start_date, end_date)
            return [{"rank": 2}]

        monkeypatch.setattr(appstore_ks, "fetch_keyword_ranking_history", fake_appstore)
        monkeypatch.setattr(playstore_ks, "fetch_keyword_ranking_history", fake_playstore)

        result = compare_ks.fetch_keyword_ranking_history(
            529479190, "com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-10"
        )

        assert captured["appstore"] == (529479190, "US", "clan", "2026-07-01", "2026-07-10")
        assert captured["playstore"] == ("com.supercell.clashofclans", "US", "clan", "2026-07-01", "2026-07-10")
        assert result == {"app_store": [{"rank": 1}], "play_store": [{"rank": 2}]}


class TestFetchTopKeywords:
    def test_device_only_passed_to_app_store_side(self, monkeypatch):
        captured = {}

        def fake_appstore(track_id, country_code, date, device, limit):
            captured["appstore"] = (track_id, country_code, date, device, limit)
            return []

        def fake_playstore(track_id, country_code, date, limit):
            captured["playstore"] = (track_id, country_code, date, limit)
            return []

        monkeypatch.setattr(appstore_ks, "fetch_top_keywords", fake_appstore)
        monkeypatch.setattr(playstore_ks, "fetch_top_keywords", fake_playstore)

        compare_ks.fetch_top_keywords(
            529479190, "com.supercell.clashofclans", "US", "2026-07-01", device="IPHONE", limit=10
        )

        assert captured["appstore"] == (529479190, "US", "2026-07-01", "IPHONE", 10)
        assert captured["playstore"] == ("com.supercell.clashofclans", "US", "2026-07-01", 10)

    def test_combines_both_stores_under_their_own_keys(self, monkeypatch):
        monkeypatch.setattr(appstore_ks, "fetch_top_keywords", lambda *a: [{"keyword": "clan"}])
        monkeypatch.setattr(playstore_ks, "fetch_top_keywords", lambda *a: [{"keyword": "war"}])

        result = compare_ks.fetch_top_keywords(529479190, "com.supercell.clashofclans", "US", "2026-07-01")
        assert result == {"app_store": [{"keyword": "clan"}], "play_store": [{"keyword": "war"}]}
