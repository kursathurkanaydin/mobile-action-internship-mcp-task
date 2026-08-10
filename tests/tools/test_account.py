from mcp_task.clients.mobileaction import MobileActionAPIError
from mcp_task.tools import account


class TestGetRemainingApiCredits:
    def test_returns_client_data_unchanged_on_success(self, monkeypatch):
        fake_data = {"success": True, "data": {"creditTotal": 100000, "creditRemaining": 99000}}
        monkeypatch.setattr(account, "get", lambda path: fake_data)

        assert account.get_remaining_api_credits() == fake_data

    def test_returns_error_shape_on_api_failure(self, monkeypatch):
        def raise_error(path):
            raise MobileActionAPIError("rate limited", status_code=429)

        monkeypatch.setattr(account, "get", raise_error)

        result = account.get_remaining_api_credits()
        assert result == {"error": "rate limited", "status_code": 429, "error_type": "upstream_api"}
