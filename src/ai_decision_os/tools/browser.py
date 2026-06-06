from __future__ import annotations

from html.parser import HTMLParser

import httpx
from playwright.async_api import async_playwright


async def extract_page(url: str, max_chars: int = 5000) -> dict[str, str]:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                # Set a slightly shorter navigation timeout to keep execution moving
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                title = await page.title()
                try:
                    text = await page.locator("body").inner_text(timeout=8000)
                except Exception:
                    text = "Could not extract body text from the target page."
                return {"url": url, "title": title, "text": text[:max_chars]}
            finally:
                await browser.close()
    except Exception as exc:
        return await _extract_page_with_http(url, max_chars, exc)


async def _extract_page_with_http(url: str, max_chars: int, playwright_error: Exception) -> dict[str, str]:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; AI-Decision-OS/0.1; "
                        "+https://github.com/)"
                    )
                },
            )
            response.raise_for_status()
    except Exception as http_error:
        return {
            "url": url,
            "title": "Failed to load page",
            "text": (
                "Error extracting page content. "
                f"Playwright failed: {playwright_error}. HTTP fallback failed: {http_error}"
            ),
        }

    parser = _ReadableHTMLParser()
    parser.feed(response.text)
    title = parser.title or str(response.url)
    text = parser.text()
    if not text:
        text = "HTTP fallback loaded the page but did not find readable body text."
    return {
        "url": str(response.url),
        "title": title,
        "text": f"{text[:max_chars]}\n\nExtraction note: used HTTP fallback because Playwright failed.",
    }


class _ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._chunks: list[str] = []
        self._tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag_stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[index] == tag:
                del self._tag_stack[index:]
                break

    def handle_data(self, data: str) -> None:
        blocked_tags = {"script", "style", "noscript", "svg"}
        if any(tag in blocked_tags for tag in self._tag_stack):
            return
        normalized = " ".join(data.split())
        if not normalized:
            return
        if self._tag_stack and self._tag_stack[-1] == "title" and not self.title:
            self.title = normalized
            return
        self._chunks.append(normalized)

    def text(self) -> str:
        return "\n".join(self._chunks)
