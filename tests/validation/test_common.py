import pytest

from mcp_task.validation.common import (
    InputValidationError,
    require_country_code,
    require_date,
    require_date_range,
    require_keyword_list,
    require_positive_int,
    require_text,
)


class TestInputValidationError:
    def test_error_type_is_validation(self):
        assert InputValidationError("bad input").error_type == "validation"


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


class TestRequireKeywordList:
    def test_single_keyword_is_allowed(self):
        assert require_keyword_list("strategy") == ["strategy"]

    def test_parses_dedupes_and_strips_whitespace(self):
        result = require_keyword_list(" game , strategy , game ")
        assert result == ["game", "strategy"]

    def test_empty_raises(self):
        with pytest.raises(InputValidationError, match="cannot be empty"):
            require_keyword_list("")

    def test_too_many_keywords_raises(self):
        keywords = ",".join(f"kw{i}" for i in range(5))
        with pytest.raises(InputValidationError, match="at most 3"):
            require_keyword_list(keywords, max_count=3)

    def test_too_few_keywords_raises(self):
        with pytest.raises(InputValidationError, match="at least 2"):
            require_keyword_list("game", min_count=2)
