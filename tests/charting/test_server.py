import urllib.request

from mcp_task.charting.server import publish_chart, publish_html


class TestPublishChart:
    def test_published_content_is_served_correctly(self):
        content = b"fake-png-bytes-for-testing"
        url = publish_chart(content)

        assert url.startswith("http://127.0.0.1:")
        assert url.endswith(".png")

        with urllib.request.urlopen(url) as response:
            assert response.status == 200
            assert response.headers.get("Content-Type") == "image/png"
            assert response.read() == content

    def test_two_publishes_get_different_urls(self):
        first_url = publish_chart(b"one")
        second_url = publish_chart(b"two")
        assert first_url != second_url


class TestPublishHtml:
    def test_published_content_is_served_correctly(self):
        content = b"<html><body>dashboard</body></html>"
        url = publish_html(content)

        assert url.endswith(".html")

        with urllib.request.urlopen(url) as response:
            assert response.status == 200
            assert response.headers.get("Content-Type", "").startswith("text/html")
            assert response.read() == content

    def test_chart_and_html_share_the_same_local_server(self):
        chart_url = publish_chart(b"chart")
        html_url = publish_html(b"<html></html>")

        chart_port = chart_url.split(":")[2].split("/")[0]
        html_port = html_url.split(":")[2].split("/")[0]
        assert chart_port == html_port
