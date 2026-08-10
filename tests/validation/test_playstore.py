import pytest

from mcp_task.validation.common import InputValidationError
from mcp_task.validation.playstore import require_package_name, require_package_name_list


class TestRequirePackageName:
    def test_valid_package_name_passes_through(self):
        assert require_package_name("com.facebook.katana") == "com.facebook.katana"

    def test_strips_surrounding_whitespace(self):
        assert require_package_name("  com.facebook.katana  ") == "com.facebook.katana"

    @pytest.mark.parametrize(
        "bad_value", [None, "", "com", "529479190", "com.face book", ".com.facebook", "com..facebook"]
    )
    def test_rejects_non_package_name_values(self, bad_value):
        with pytest.raises(InputValidationError):
            require_package_name(bad_value)

    def test_extracts_id_from_play_store_url(self):
        url = "https://play.google.com/store/apps/details?id=com.facebook.katana&hl=tr"
        assert require_package_name(url) == "com.facebook.katana"

    def test_extracts_id_from_play_store_url_when_id_is_not_first_param(self):
        url = "https://play.google.com/store/apps/details?hl=tr&id=com.facebook.katana"
        assert require_package_name(url) == "com.facebook.katana"

    def test_rejects_url_from_an_unrelated_domain(self):
        with pytest.raises(InputValidationError):
            require_package_name("https://example.com/store/apps/details?id=com.facebook.katana")

    def test_rejects_play_store_url_missing_id_param(self):
        with pytest.raises(InputValidationError):
            require_package_name("https://play.google.com/store/apps/details?hl=tr")


class TestRequirePackageNameList:
    def test_single_id_is_allowed(self):
        assert require_package_name_list("com.facebook.katana") == ["com.facebook.katana"]

    def test_parses_dedupes_and_strips_whitespace(self):
        result = require_package_name_list(" com.a , com.b , com.a ")
        assert result == ["com.a", "com.b"]

    def test_empty_raises(self):
        with pytest.raises(InputValidationError, match="cannot be empty"):
            require_package_name_list("")

    def test_invalid_package_name_in_list_raises(self):
        with pytest.raises(InputValidationError):
            require_package_name_list("com.a,not-a-package-name")

    def test_too_many_ids_raises(self):
        ids = ",".join(f"com.app{i}" for i in range(5))
        with pytest.raises(InputValidationError, match="at most 3"):
            require_package_name_list(ids, max_count=3)

    def test_too_few_ids_raises(self):
        with pytest.raises(InputValidationError, match="at least 2"):
            require_package_name_list("com.a", min_count=2)
