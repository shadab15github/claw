# claw-site

`claw-site` is a small Python MCP server with one tool: `extract_urls`.

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

## Tool

### `extract_urls`

Parameters:

- `url`: page or site URL.
- `same_domain`: only return URLs on the input hostname. Default: `true`.
- `limit`: maximum unique URLs to return. Default: `500`.

The response is only newline-separated absolute URLs, or a short message when no URLs are found.
