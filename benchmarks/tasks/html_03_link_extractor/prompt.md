Write `solution.py` with a function `extract_links(html: str, base_url: str) -> list[dict]`.

It takes the text of an HTML page (not a file name) and the URL the page was served from, and
returns every link on the page with its address made absolute. The sample page
`blog_index.html` is in the working directory (a made-up blog; no network is involved). Its
base URL is `https://blog.example.test/2024/index.html`. **Use only the Python standard
library** (`html.parser`, `urllib.parse`, `re`, ...): no BeautifulSoup, lxml or requests. The page may
be formatted differently from the sample (upper-case tags and attributes, quote style, line
breaks inside tags, nested tags), so do not rely on the exact text of the sample.

Rules:

- Consider every `<a>` element that has an `href` attribute, in document order. Duplicate
  links are all kept.
- An `<a>` that is never closed ends at the next `<a>` start tag or at the end of the page and
  is still a link (its text is what it contains up to that point).
- Only `<a>` elements count: `href` on `<link>`, `<area>` or anything else is not a link.
  Other schemes (`ftp:`, `data:`, `https:`) are kept; only the three prefixes below are skipped,
  and only at the very start of the stripped `href` (`/r?u=mailto:x` is kept).
- Skip the link when its `href`, stripped of surrounding whitespace, is empty, starts with `#`,
  or starts with `mailto:`, `tel:` or `javascript:` (any letter case).
- `"url"` is the stripped `href` (HTML entities such as `&amp;` decoded) resolved against
  `base_url` exactly as `urllib.parse.urljoin(base_url, href)` does. Any `<base>` tag in the
  page is ignored; only the `base_url` argument counts.
- `"text"` is the text inside the `<a>` element, with nested tags removed, entities decoded,
  whitespace runs collapsed to one space and surrounding whitespace removed. A link that
  contains only an image has the text `""` (alt text is not used).
- Return a list of `{"text": str, "url": str}` dicts. A page without links gives `[]`.
