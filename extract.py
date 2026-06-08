"""HTML URL extraction helpers."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup


def normalize_discovered_url(raw_url: str, base_url: str | None = None) -> str | None:
    raw = (raw_url or "").strip()
    if not raw or re.match(r"^(javascript:|mailto:|tel:|#)", raw, re.I):
        return None
    try:
        absolute_url = urljoin(base_url, raw) if base_url else raw
    except ValueError:
        return None
    parsed = urlparse(absolute_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return urlunparse(parsed._replace(fragment=""))


def extract_links(html: str, base_url: str, *, same_domain: bool = True) -> list[str]:
    soup = BeautifulSoup(html or "", "lxml")
    base_host = urlparse(base_url).hostname or ""
    urls: list[str] = []
    seen: set[str] = set()

    for tag in soup.select("a[href], link[href], area[href]"):
        url = normalize_discovered_url(tag.get("href") or "", base_url)
        if not url:
            continue
        if same_domain and (urlparse(url).hostname or "") != base_host:
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)

    return urls


def has_extractable_content(html: str, base_url: str, *, same_domain: bool = True) -> bool:
    return bool(extract_links(html, base_url, same_domain=same_domain))
