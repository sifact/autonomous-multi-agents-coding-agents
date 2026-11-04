import re
from html.parser import HTMLParser


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self.date: str | None = None
        self.author: str | None = None
        self.author_seen = False
        self.tags: list[str] = []
        self.state = 0  # 0 before the post, 1 inside it, 2 after it
        self.depth = 0
        self.capture: str | None = None
        self.buffer: list[str] = []

    def _in_post(self) -> bool:
        return self.state == 1 and self.depth == 1

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        is_author = (attr.get("name") or "").strip().lower() == "author"
        if tag == "meta" and not self.author_seen and is_author:
            self.author_seen = True
            self.author = (attr.get("content") or "").strip() or None
        if tag == "article":
            if self.state == 0:
                self.state, self.depth = 1, 1
            elif self.state == 1:
                self.depth += 1
            return
        if not self._in_post() or self.capture:
            return
        if tag == "h1" and self.title is None:
            self.capture, self.buffer = "title", []
        elif tag == "time" and self.date is None and (attr.get("datetime") or "").strip():
            self.date = attr["datetime"].strip()[:10]
        elif tag == "a" and "tag" in (attr.get("rel") or "").split():
            self.capture, self.buffer = "tag", []

    def handle_endtag(self, tag):
        if tag == "article" and self.state == 1:
            self.depth -= 1
            if self.depth == 0:
                self.state = 2
            return
        if self.capture == "title" and tag == "h1":
            self.title, self.capture = _clean("".join(self.buffer)), None
        elif self.capture == "tag" and tag == "a":
            text, self.capture = _clean("".join(self.buffer)), None
            if text and text not in self.tags:
                self.tags.append(text)

    def handle_data(self, data):
        if self.capture and self._in_post():
            self.buffer.append(data)


def parse_post(html: str) -> dict:
    parser = _Parser()
    parser.feed(html)
    parser.close()
    return {
        "title": parser.title,
        "date": parser.date,
        "author": parser.author,
        "tags": parser.tags,
    }
