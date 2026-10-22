"""Headless Chromium through Playwright, for PDF exports and for pictures of visuals in
Word exports. The browser is RADICLE_CHROMIUM_PATH (the Docker image's Chromium) or
Playwright's own."""

import asyncio
import os
from typing import Any

from playwright.async_api import async_playwright

from radicle.platform.config import get_settings

READY = "[data-print-ready]"
TIMEOUT_MS = 60_000
VISUAL_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
    "img-src data:; font-src data:"
)


def _launch_args() -> dict[str, Any]:
    path = get_settings().chromium_path
    if path and not os.path.exists(path):
        raise RuntimeError(
            f"PDF exports need Chromium at {path}; this install was built without it."
        )
    # The image runs Chromium as a non-root user without user namespaces.
    return {"executable_path": path, "args": ["--no-sandbox"]} if path else {}


async def pdf(url: str) -> bytes:
    """Open the print view, let lazy images and visuals load, and print it in A4."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(**_launch_args())
        try:
            page = await browser.new_page(viewport={"width": 1100, "height": 1400})
            await page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
            await page.wait_for_selector(READY, state="attached", timeout=TIMEOUT_MS)
            # Lazy images load as they come into view.
            await page.evaluate(
                """async () => {
                  for (let y = 0; y < document.body.scrollHeight; y += 800) {
                    window.scrollTo(0, y);
                    await new Promise((r) => setTimeout(r, 50));
                  }
                  window.scrollTo(0, 0);
                }"""
            )
            await page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
            return await page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "16mm", "bottom": "16mm", "left": "14mm", "right": "14mm"},
            )
        finally:
            await browser.close()


async def shots(codes: list[str]) -> list[bytes | None]:
    """A picture of each visual (its SVG or HTML), drawn alone in a page with the visual
    sandbox's CSP; None where one fails."""
    out: list[bytes | None] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(**_launch_args())
        try:
            page = await browser.new_page(
                viewport={"width": 900, "height": 600}, java_script_enabled=True
            )
            for code in codes:
                try:
                    head = f'<meta http-equiv="Content-Security-Policy" content="{VISUAL_CSP}">'
                    await page.set_content(head + code, timeout=TIMEOUT_MS)
                    await asyncio.sleep(0.5)  # let animations reach a frame
                    out.append(await page.screenshot(full_page=True))
                except Exception:  # a broken visual keeps its description in Word
                    out.append(None)
        finally:
            await browser.close()
    return out
