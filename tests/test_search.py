from __future__ import annotations

from ai_decision_os.tools.search import _clean_api_key


def test_clean_api_key_strips_quotes_and_spaces() -> None:
    assert _clean_api_key(' "tvly-test" ') == "tvly-test"
    assert _clean_api_key(" 'tvly-test' ") == "tvly-test"
    assert _clean_api_key(None) == ""
