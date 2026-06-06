from __future__ import annotations

from ai_decision_os.tools.browser import _ReadableHTMLParser


def test_readable_html_parser_extracts_title_and_body_text() -> None:
    parser = _ReadableHTMLParser()
    parser.feed(
        """
        <html>
          <head><title>Example Page</title><style>.hidden { display: none; }</style></head>
          <body>
            <h1>Cristiano Ronaldo</h1>
            <script>window.noisy = true;</script>
            <p>Career goals and Champions League records.</p>
          </body>
        </html>
        """
    )

    assert parser.title == "Example Page"
    assert "Cristiano Ronaldo" in parser.text()
    assert "window.noisy" not in parser.text()
