"""claw-site MCP server.

Tools:
- extract URLs from a site using this flow:
robots.txt -> sitemap discovery -> sitemap parsing -> page fetch with httpx
-> link extraction, falling back to crawl4ai when static content has no links.
- extract text from images with Tesseract OCR.
"""

from __future__ import annotations

import contextlib
import os
from typing import Annotated

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP  # noqa: E402
from pydantic import Field  # noqa: E402

import extract  # noqa: E402
import fetcher  # noqa: E402
import ocr  # noqa: E402
import sitemap  # noqa: E402
from errors import describe_fetch_error, normalize_url, tool_error  # noqa: E402

DEFAULT_LIMIT = int(os.environ.get("CLAW_SITE_URL_LIMIT", "500"))


@contextlib.asynccontextmanager
async def _lifespan(_server: "FastMCP"):
    try:
        yield
    finally:
        await fetcher.close_crawler()


mcp = FastMCP(
    "claw-site",
    lifespan=_lifespan,
    host=os.environ.get("MCP_HTTP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_HTTP_PORT", "3002")),
)


@mcp.tool()
async def extract_urls(
    url: Annotated[str, Field(description="Page or site URL. Scheme-less input like `example.com` is allowed.")],
    same_domain: Annotated[bool, Field(description="Only return URLs on the input URL hostname.")] = True,
    limit: Annotated[int, Field(description="Maximum number of unique URLs to return.", ge=1, le=5000)] = DEFAULT_LIMIT,
) -> str:
    """Extract unique absolute URLs from robots/sitemaps and the given page.

    The tool first checks robots.txt for Sitemap entries, parses discovered
    sitemaps, fetches the requested page with httpx, extracts links if present,
    and falls back to crawl4ai browser rendering when static HTML has no links.
    """
    target = normalize_url(url)
    urls: list[str] = []
    seen: set[str] = set()
    render_methods: list[str] = []

    def mark_render_method(method: str) -> None:
        if method not in render_methods:
            render_methods.append(method)

    def add_many(values: list[str]) -> None:
        for value in values:
            if len(urls) >= limit:
                return
            if same_domain and not _same_hostname(value, target):
                continue
            if value in seen:
                continue
            seen.add(value)
            urls.append(value)

    try:
        mark_render_method("httpx")
        add_many(await sitemap.collect_sitemap_urls(target, limit=limit))
    except Exception:
        pass

    try:
        mark_render_method("httpx")
        page = await fetcher.fetch_static(target)
    except Exception as err:
        raise tool_error(describe_fetch_error(err, target))

    static_links = extract.extract_links(page.html, page.final_url, same_domain=same_domain)
    add_many(static_links)

    if len(urls) < limit and not static_links:
        try:
            mark_render_method("crawl4ai")
            rendered_page = await fetcher.fetch_browser(page.final_url)
            add_many(extract.extract_links(rendered_page.html, rendered_page.final_url, same_domain=same_domain))
        except Exception as err:
            raise tool_error(describe_fetch_error(err, page.final_url))

    render_label = " + ".join(render_methods) or "none"
    if not urls:
        return f"Render method used: {render_label}\nNo URLs found for {target}."
    return f"Render method used: {render_label}\n" + "\n".join(urls)


@mcp.tool()
async def extract_image_text(
    image: Annotated[
        str,
        Field(description="Image file path, image URL, data URL, or base64-encoded image content."),
    ],
    lang: Annotated[
        str,
        Field(description="Tesseract language code, for example 'eng' or 'eng+hin'."),
    ] = "eng",
) -> str:
    """Extract text from an image with Tesseract OCR.

    The response is only the recognized text, with no labels or metadata.
    """
    try:
        return await ocr.extract_image_text(image, lang=lang)
    except Exception as err:
        raise tool_error(str(err))


def _same_hostname(left_url: str, right_url: str) -> bool:
    from urllib.parse import urlparse

    return (urlparse(left_url).hostname or "") == (urlparse(right_url).hostname or "")


with contextlib.suppress(Exception):
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_req: "Request") -> "JSONResponse":
        return JSONResponse({"status": "ok", "server": "claw-site"})


def main() -> None:
    import sys

    argv = sys.argv[1:]
    if "--http" in argv:
        mode = "http"
    elif "--stdio" in argv:
        mode = "stdio"
    else:
        mode = os.environ.get("MCP_TRANSPORT", "stdio").lower()

    if mode == "http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
