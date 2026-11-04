import re
from html.parser import HTMLParser
from urllib.parse import urljoin

_SKIP = re.compile(r"(?i)(mailto|tel|javascript):")


class _Parser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[dict] = []
        self.href: str | None = None
        self.buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        self.href = None if href is None else href.strip()
        self.buffer = []

    def handle_endtag(self, tag):
        if tag != "a" or self.href is None:
            return
        href = self.href
        self.href = None
        if not href or href.startswith("#") or _SKIP.match(href):
            return
        text = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
        self.links.append({"text": text, "url": urljoin(self.base_url, href)})

    def handle_data(self, data):
        if self.href is not None:
            self.buffer.append(data)


def extract_links(html: str, base_url: str) -> list[dict]:
    parser = _Parser(base_url)
    parser.feed(html)
    parser.close()
    return parser.links
