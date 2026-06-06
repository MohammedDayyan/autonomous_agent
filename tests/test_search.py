from __future__ import annotations

from ai_decision_os.tools.search import _clean_api_key, _detect_provider, _tavily_api_key, _tavily_api_key_name


def test_clean_api_key_strips_quotes_and_spaces() -> None:
    assert _clean_api_key(' "tvly-test" ') == "tvly-test"
    assert _clean_api_key(" 'tvly-test' ") == "tvly-test"
    assert _clean_api_key(None) == ""


def test_clean_api_key_strips_newlines() -> None:
    assert _clean_api_key("\ntvly-test\r\n") == "tvly-test"


def test_detect_provider_from_results() -> None:
    assert _detect_provider([{"title": "Tavily answer", "url": "https://tavily.com", "snippet": ""}]) == "tavily"
    assert _detect_provider([{"title": "Open web search", "url": "https://duckduckgo.com/?q=x", "snippet": ""}]) == (
        "duckduckgo"
    )


def test_tavily_key_prefers_correct_env_var(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-correct")
    monkeypatch.setenv("TRAVILY_API_KEY", "tvly-misspelled")

    assert _tavily_api_key() == "tvly-correct"
    assert _tavily_api_key_name() == "TAVILY_API_KEY"


def test_tavily_key_accepts_common_misspelling(monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("TRAVILY_API_KEY", "tvly-misspelled")

    assert _tavily_api_key() == "tvly-misspelled"
    assert _tavily_api_key_name() == "TRAVILY_API_KEY"
