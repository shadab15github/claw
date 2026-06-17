# claw-site

`claw-site` is a small Python MCP server with tools for extracting site URLs and extracting text from images.

The tool follows this flow:

```text
robots.txt
  -> find sitemap URLs
  -> parse sitemap XML
  -> collect URLs
  -> fetch page
  -> httpx
  -> content found?
     -> yes: extract URLs
     -> no: crawl4ai fallback
```

## Setup

Requires Python 3.10+.

The `extract_image_text` tool also requires the native Tesseract OCR executable:

- Windows: install Tesseract OCR. The tool auto-detects the standard `C:\Program Files\Tesseract-OCR\tesseract.exe` install path; set `TESSERACT_CMD` if it is installed elsewhere.
- macOS/Linux: install `tesseract` with your system package manager.

```bash
cd claw-site
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
crawl4ai-setup
```

## Run

```bash
python server.py
python server.py --http
```

HTTP mode listens on `127.0.0.1:3002` by default.

## Claude Desktop config

```json
{
  "mcpServers": {
    "claw-site": {
      "command": "D:\\MCP\\claw-site\\.venv\\Scripts\\python.exe",
      "args": ["D:\\MCP\\claw-site\\server.py"]
    }
  }
}
```

## Tools

### `extract_urls`

Parameters:

- `url`: page or site URL.
- `same_domain`: only return URLs on the input hostname. Default: `true`.
- `same_path`: only return URLs under the input URL path prefix, for example `https://example.com/blogs` returns `/blogs` and `/blogs/...` URLs. Default: `true`.
- `limit`: maximum unique URLs to return. Default: `500`.

The response includes URL stats by source, then a Markdown bullet list of absolute URLs with the source that found each URL, such as `robots.txt`, `sitemap.xml`, `httpx`, or `Crawl4AI`. If no URLs are found, the tool returns the stats and a short message.

### `extract_content`

Parameters:

- `url`: page URL to extract. Scheme-less input like `example.com` is allowed.
- `include_title`: prepend the page title as a top-level Markdown heading. Default: `true`.

Fetches the page with httpx and converts the readable HTML to Markdown (scripts, styles, and other non-content tags are stripped; relative links and images are resolved to absolute URLs). When the static HTML yields little content — for example a JavaScript-rendered page — it falls back to `crawl4ai` browser rendering and uses its native Markdown output. The response is the Markdown content.

### `extract_image_text`

Parameters:

- `image`: image file path, image URL, data URL, or base64-encoded image content.
- `lang`: Tesseract language code. Default: `eng`.

The response is only the text recognized from the image.
