import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services import web_search


def _fake_response(json_data, status_ok=True):
    response = MagicMock()
    response.json.return_value = json_data
    if not status_ok:
        response.raise_for_status.side_effect = Exception("HTTP error")
    return response


class TestSearchWeb(unittest.TestCase):
    @patch("app.services.web_search.requests.get")
    def test_returns_result_when_abstract_present(self, mock_get):
        mock_get.return_value = _fake_response(
            {
                "Heading": "Roman Empire",
                "AbstractText": "The Roman Empire was the post-Republican period of ancient Rome.",
                "AbstractURL": "https://en.wikipedia.org/wiki/Roman_Empire",
            }
        )
        result = web_search.search_web("Roman Empire")
        self.assertIsNotNone(result)
        self.assertEqual(result.heading, "Roman Empire")
        self.assertEqual(
            result.abstract, "The Roman Empire was the post-Republican period of ancient Rome."
        )
        self.assertEqual(result.source_url, "https://en.wikipedia.org/wiki/Roman_Empire")

    @patch("app.services.web_search.requests.get")
    def test_returns_none_when_abstract_empty(self, mock_get):
        mock_get.return_value = _fake_response(
            {"Heading": "", "AbstractText": "", "AbstractURL": ""}
        )
        result = web_search.search_web("a very niche and specific local event")
        self.assertIsNone(result)

    @patch("app.services.web_search.requests.get")
    def test_returns_none_on_network_error(self, mock_get):
        mock_get.side_effect = ConnectionError("network unreachable")
        result = web_search.search_web("Roman Empire")
        self.assertIsNone(result)

    @patch("app.services.web_search.requests.get")
    def test_returns_none_on_http_error_status(self, mock_get):
        mock_get.return_value = _fake_response(
            {"AbstractText": "should not be reached"}, status_ok=False
        )
        result = web_search.search_web("Roman Empire")
        self.assertIsNone(result)

    def test_empty_query_returns_none_without_network_call(self):
        with patch("app.services.web_search.requests.get") as mock_get:
            result = web_search.search_web("   ")
            mock_get.assert_not_called()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
