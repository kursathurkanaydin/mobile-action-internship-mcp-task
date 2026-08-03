import urllib.request

from mcp_task.charting.server import publish_html


class TestPublishHtml:
    def test_published_content_is_served_correctly(self):
        content = b"<html><body>dashboard</body></html>"
        url = publish_html(content)

        assert url.startswith("http://127.0.0.1:")
        assert url.endswith(".html")

        with urllib.request.urlopen(url) as response:
            assert response.status == 200
            assert response.headers.get("Content-Type", "").startswith("text/html")
            assert response.read() == content

    def test_two_publishes_get_different_urls(self):
        first_url = publish_html(b"<html>one</html>")
        second_url = publish_html(b"<html>two</html>")
        assert first_url != second_url
