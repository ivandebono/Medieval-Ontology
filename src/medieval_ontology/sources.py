"""Source loading for local files and remote text pages."""

from __future__ import annotations

from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_SOURCE_URL = "https://www.thelatinlibrary.com/ebulo.html"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = []
    for raw_line in text.replace("\xa0", " ").splitlines():
        line = " ".join(raw_line.split())
        if line:
            lines.append(line)
    return "\n".join(lines)


def load_source(source: str = DEFAULT_SOURCE_URL, timeout: float = 30.0) -> str:
    """Load text from a URL or local path, stripping HTML when necessary."""

    if source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=timeout, headers={"User-Agent": "ontology/0.1"})
        response.raise_for_status()
        content = response.text
    else:
        content = Path(source).read_text(encoding="utf-8")

    if "<html" in content.lower() or "<br" in content.lower() or "<p" in content.lower():
        return html_to_text(content)
    return content
