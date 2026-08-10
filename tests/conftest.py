import httpx
import pytest


class FakeResponse:
    """Minimal stand-in for httpx.Response covering only what the clients touch."""

    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = {}

    def json(self):
        if self._json_data is None:
            raise ValueError("no json body")
        return self._json_data

    @property
    def content(self):
        # Non-empty whenever a json body was set (even {} or []) or there's
        # raw text; empty only when neither was given, mimicking a real 204.
        if self._json_data is not None:
            return b"{}"
        return self.text.encode()

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test")
            raise httpx.HTTPStatusError("error", request=request, response=self)


@pytest.fixture
def fake_response():
    return FakeResponse
