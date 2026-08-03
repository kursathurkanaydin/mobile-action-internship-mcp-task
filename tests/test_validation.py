import pytest

from mcp_task.validation import (
    InputValidationError,
    require_country_code,
    require_date,
    require_date_range,
    require_device,
    require_positive_int,
    require_text,
    require_track_id,
    require_track_id_list,
)


class TestRequireTrackId:
    def test_valid_positive_int_passes_through(self):
        assert require_track_id(529479190) == 529479190

    @pytest.mark.parametrize("bad_value", [0, -1, None])
    def test_rejects_non_positive_or_missing(self, bad_value):
        with pytest.raises(InputValidationError):
            require_track_id(bad_value)


class TestRequireCountryCode:
    @pytest.mark.parametrize("raw, expected", [("US", "US"), ("us", "US"), (" tr ", "TR")])
    def test_valid_codes_are_uppercased_by_default(self, raw, expected):
        assert require_country_code(raw) == expected

    def test_upper_false_preserves_case(self):
        assert require_country_code("us", upper=False) == "us"

    @pytest.mark.parametrize("bad_value", ["", "USA", "U", "1S", None])
    def test_rejects_anything_not_two_letters(self, bad_value):
        with pytest.raises(InputValidationError):
            require_country_code(bad_value)


class TestRequireText:
    def test_strips_and_returns_non_empty(self):
        assert require_text("  strategy  ", "keyword") == "strategy"

    @pytest.mark.parametrize("bad_value", ["", "   ", None])
    def test_rejects_empty(self, bad_value):
        with pytest.raises(InputValidationError, match="cannot be empty"):
            require_text(bad_value, "keyword")


class TestRequireDevice:
    @pytest.mark.parametrize("raw, expected", [("IPHONE", "IPHONE"), ("iphone", "IPHONE"), (" ipad ", "IPAD")])
    def test_valid_devices_are_normalized(self, raw, expected):
        assert require_device(raw) == expected

    def test_none_and_not_required_returns_none(self):
        assert require_device(None, required=False) is None

    def test_none_and_required_raises(self):
        with pytest.raises(InputValidationError):
            require_device(None, required=True)

    def test_invalid_device_name_raises(self):
        with pytest.raises(InputValidationError):
            require_device("ANDROID")


class TestRequireDate:
    def test_valid_date_passes_through(self):
        assert require_date("2026-07-01", "date") == "2026-07-01"

    @pytest.mark.parametrize("bad_value", ["07-01-2026", "2026/07/01", "not-a-date", ""])
    def test_rejects_bad_format(self, bad_value):
        with pytest.raises(InputValidationError, match="date"):
            require_date(bad_value, "date")


class TestRequireDateRange:
    def test_valid_range_does_not_raise(self):
        require_date_range("2026-07-01", "2026-07-10", max_days=30)

    def test_start_after_end_raises(self):
        with pytest.raises(InputValidationError, match="before"):
            require_date_range("2026-07-10", "2026-07-01")

    def test_range_longer_than_max_days_raises(self):
        with pytest.raises(InputValidationError, match="too large"):
            require_date_range("2026-01-01", "2026-07-01", max_days=30)

    def test_range_is_inclusive_of_both_endpoints(self):
        # exactly max_days long (inclusive) should be accepted
        require_date_range("2026-07-01", "2026-07-30", max_days=30)


class TestRequirePositiveInt:
    def test_none_passes_through(self):
        assert require_positive_int(None, "limit") is None

    def test_positive_value_passes_through(self):
        assert require_positive_int(150, "limit") == 150

    @pytest.mark.parametrize("bad_value", [0, -5])
    def test_rejects_non_positive(self, bad_value):
        with pytest.raises(InputValidationError):
            require_positive_int(bad_value, "limit")


class TestRequireTrackIdList:
    def test_valid_csv_returns_parsed_ids_in_order(self):
        assert require_track_id_list("111,222,333") == [111, 222, 333]

    def test_deduplicates_preserving_first_seen_order(self):
        assert require_track_id_list("111,222,111,333") == [111, 222, 333]

    def test_strips_whitespace_around_ids(self):
        assert require_track_id_list(" 111 , 222 ") == [111, 222]

    def test_empty_string_raises(self):
        with pytest.raises(InputValidationError, match="cannot be empty"):
            require_track_id_list("")

    def test_non_numeric_entry_raises(self):
        with pytest.raises(InputValidationError, match="abc"):
            require_track_id_list("111,abc")

    def test_below_min_count_raises(self):
        with pytest.raises(InputValidationError, match="at least 2"):
            require_track_id_list("111")

    def test_duplicates_collapsing_below_min_count_raises(self):
        with pytest.raises(InputValidationError, match="at least 2"):
            require_track_id_list("111,111")

    def test_above_max_count_raises(self):
        ids = ",".join(str(100 + i) for i in range(7))
        with pytest.raises(InputValidationError, match="Too many apps"):
            require_track_id_list(ids)

    def test_respects_custom_min_and_max(self):
        assert require_track_id_list("111,222,333", min_count=3, max_count=3) == [111, 222, 333]
        with pytest.raises(InputValidationError):
            require_track_id_list("111,222,333,444", min_count=3, max_count=3)

    def test_min_count_one_allows_a_single_id(self):
        assert require_track_id_list("111", min_count=1) == [111]

    def test_max_count_can_be_raised_for_batch_lookups(self):
        ids = ",".join(str(100 + i) for i in range(150))
        assert len(require_track_id_list(ids, min_count=1, max_count=150)) == 150
