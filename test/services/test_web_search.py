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


class TestWikipediaFallback(unittest.TestCase):
    """DuckDuckGo Instant Answer frequently returns nothing for niche/specific
    topics -- Wikipedia's own search+summary REST API (also free, no key)
    has broader coverage and is tried next, only when DuckDuckGo found
    nothing. A None from Wikipedia too must still fall through to None,
    exactly like before this fallback existed.
    """

    _empty_duckduckgo = _fake_response({"Heading": "", "AbstractText": "", "AbstractURL": ""})

    def test_falls_back_to_wikipedia_when_duckduckgo_empty(self):
        wikipedia_search = _fake_response({"pages": [{"key": "Niche_Topic", "title": "Niche Topic"}]})
        wikipedia_summary = _fake_response(
            {
                "title": "Niche Topic",
                "extract": "A detailed summary from Wikipedia.",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Niche_Topic"}},
            }
        )
        with patch(
            "app.services.web_search.requests.get",
            side_effect=[self._empty_duckduckgo, wikipedia_search, wikipedia_summary],
        ) as mock_get:
            result = web_search.search_web("a niche topic duckduckgo has no abstract for")

        self.assertIsNotNone(result)
        self.assertEqual(result.heading, "Niche Topic")
        self.assertEqual(result.abstract, "A detailed summary from Wikipedia.")
        self.assertEqual(result.source_url, "https://en.wikipedia.org/wiki/Niche_Topic")
        self.assertEqual(mock_get.call_count, 3)

    def test_duckduckgo_success_short_circuits_wikipedia(self):
        duckduckgo_ok = _fake_response(
            {"Heading": "Roman Empire", "AbstractText": "abstract", "AbstractURL": "https://x"}
        )
        with patch("app.services.web_search.requests.get", return_value=duckduckgo_ok) as mock_get:
            web_search.search_web("Roman Empire")

        mock_get.assert_called_once()

    def test_wikipedia_fallback_returns_none_when_no_pages_found(self):
        wikipedia_search_empty = _fake_response({"pages": []})
        with patch(
            "app.services.web_search.requests.get",
            side_effect=[self._empty_duckduckgo, wikipedia_search_empty],
        ):
            result = web_search.search_web("a wildly invented topic with no wikipedia article")

        self.assertIsNone(result)

    def test_wikipedia_fallback_returns_none_when_summary_has_no_extract(self):
        wikipedia_search = _fake_response({"pages": [{"key": "Empty_Page"}]})
        wikipedia_summary_empty = _fake_response({"title": "Empty Page", "extract": ""})
        with patch(
            "app.services.web_search.requests.get",
            side_effect=[self._empty_duckduckgo, wikipedia_search, wikipedia_summary_empty],
        ):
            result = web_search.search_web("a topic with an empty wikipedia summary")

        self.assertIsNone(result)

    def test_wikipedia_fallback_uses_turkish_subdomain_for_tr_language(self):
        wikipedia_search_empty = _fake_response({"pages": []})
        with patch(
            "app.services.web_search.requests.get",
            side_effect=[self._empty_duckduckgo, wikipedia_search_empty],
        ) as mock_get:
            web_search.search_web("Çanakkale Savaşı", language="tr")

        wikipedia_call_url = mock_get.call_args_list[1].args[0]
        self.assertIn("tr.wikipedia.org", wikipedia_call_url)

    def test_wikipedia_fallback_defaults_to_english_for_unrecognized_language(self):
        wikipedia_search_empty = _fake_response({"pages": []})
        with patch(
            "app.services.web_search.requests.get",
            side_effect=[self._empty_duckduckgo, wikipedia_search_empty],
        ) as mock_get:
            web_search.search_web("some topic", language="fr")

        wikipedia_call_url = mock_get.call_args_list[1].args[0]
        self.assertIn("en.wikipedia.org", wikipedia_call_url)

    def test_wikipedia_network_error_returns_none(self):
        with patch(
            "app.services.web_search.requests.get",
            side_effect=[self._empty_duckduckgo, ConnectionError("network unreachable")],
        ):
            result = web_search.search_web("a topic whose wikipedia lookup fails")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
