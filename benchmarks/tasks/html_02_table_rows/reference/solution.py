import re
from html.parser import HTMLParser


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.table_state = "before"  # before -> inside -> done
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table" and self.table_state == "before":
            self.table_state = "inside"
        elif self.table_state != "inside":
            return
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if self.table_state != "inside":
            return
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.table_state = "done"

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def parse_table(html: str) -> list[list[str]]:
    parser = _Parser()
    parser.feed(html)
    parser.close()
    return parser.rows
