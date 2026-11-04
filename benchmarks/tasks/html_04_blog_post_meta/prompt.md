Write `solution.py` with a function `parse_post(html: str) -> dict`.

It takes the text of a blog page (not a file name) and returns the metadata of the blog post on
it. The sample page `post.html` is in the working directory (a made-up blog; no network is
involved). **Use only the Python standard library** (`html.parser`, `re`, ...): no
BeautifulSoup, lxml or requests. The page may be formatted differently from the sample
(attribute order, quote style, upper-case tags, line breaks inside tags, nested tags), so do
not rely on the exact text of the sample.

Return a dict with exactly the keys `"title"`, `"date"`, `"author"` and `"tags"`:

- The *post* is the first `<article>` element in the page (from its start tag to its matching
  end tag). Anything inside an `<article>` nested within the post (for example a comment) is
  ignored for `title`, `date` and `tags`. Later top-level `<article>` elements are ignored too.
  Elements outside the post (header, sidebar, footer) are ignored for these three keys.
- `"title"`: the text of the first `<h1>` inside the post, or `None` if there is none.
  Text means everything inside the element with nested tags removed, HTML entities decoded
  (`&amp;`, `&#39;`), whitespace runs collapsed to one space, surrounding whitespace removed.
- `"date"`: take the first `<time>` element inside the post that has a non-empty `datetime` attribute (empty or whitespace-only counts as absent);
  the value is the first 10 characters of that attribute (after stripping whitespace), for
  example `"2024-03-05"` from `"2024-03-05T06:15:00+01:00"`. `None` if there is no such element.
- `"tags"`: a list with the text of every `<a>` inside the post whose `rel` attribute contains
  the word `tag` (words are separated by whitespace, so `rel="tag nofollow"` counts and
  `rel="category"` does not). Texts are normalised like the title; empty texts are dropped;
  a tag repeated with identical text (case-sensitive) is kept once, at its first position; the document order is kept and the
  case is not changed. `[]` if there are none.
- `"author"`: the `content` attribute (entities decoded, stripped) of the first `<meta>` element anywhere in
  the page whose `name` attribute is `author` (compare the name in any letter case); `None`
  if there is no such element or its content is empty.
- A page with no `<article>` gives `title` `None`, `date` `None`, `tags` `[]`; `author` is
  still read from the `<meta>` element.
