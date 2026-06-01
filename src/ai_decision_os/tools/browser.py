from __future__ import annotations

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
        return {
            "url": url,
            "title": "Failed to load page",
            "text": f"Error extracting page content: {exc}"
        }
