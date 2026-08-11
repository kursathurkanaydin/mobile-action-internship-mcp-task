import pytest

from mcp_task.validation.common import InputValidationError
from mcp_task.validation.other import require_store


class TestRequireStore:
    @pytest.mark.parametrize("raw, expected", [("ios", "ios"), ("IOS", "ios"), (" play ", "play"), ("Play", "play")])
    def test_valid_stores_are_normalized(self, raw, expected):
        assert require_store(raw) == expected

    @pytest.mark.parametrize("bad_value", ["android", "appstore", "", None])
    def test_invalid_store_raises(self, bad_value):
        with pytest.raises(InputValidationError):
            require_store(bad_value)
