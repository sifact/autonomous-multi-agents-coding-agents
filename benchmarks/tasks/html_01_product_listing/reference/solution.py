import re
from html.parser import HTMLParser

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
    "track", "wbr",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _price(text: str) -> float | None:
    try:
        return float(text.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


class _Parser(HTMLParser):
    """Collects products; ``depth`` counts open non-void elements inside the current <li>."""

    def __init__(self) -> None:
        super().__init__()
        self.products: list[dict] = []
        self.current: dict | None = None
        self.seen: set[str] = set()  # fields (name/price) already taken for this product
        self.depth = 0
        self.capture: tuple[str, int] | None = None
        self.buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        classes = set((dict(attrs).get("class") or "").split())
        if self.current is None:
            if tag == "li" and "product" in classes:
                self.current = {"name": None, "price": None}
                self.seen = set()
                self.depth = 1
            return
        if tag in VOID:
            return
        self.depth += 1
        if self.capture is None:
            for field in ("name", "price"):
                if field in classes and field not in self.seen:
                    self.seen.add(field)
                    self.capture = (field, self.depth)
                    self.buffer = []
                    break

    def handle_endtag(self, tag):
        if self.current is None or tag in VOID:
            return
        if self.capture and self.capture[1] == self.depth:
            field = self.capture[0]
            text = _clean("".join(self.buffer))
            self.current[field] = text if field == "name" else _price(text)
            self.capture = None
        self.depth -= 1
        if self.depth == 0:
            if self.current["name"] is not None:
                self.products.append(self.current)
            self.current = None

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)


def parse_products(html: str) -> list[dict]:
    parser = _Parser()
    parser.feed(html)
    parser.close()
    return parser.products
