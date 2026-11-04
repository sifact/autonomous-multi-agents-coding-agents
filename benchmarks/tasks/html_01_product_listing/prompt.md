Write `solution.py` with a function `parse_products(html: str) -> list[dict]`.

It takes the text of an HTML page (not a file name) and returns the products listed on it. The
sample page `store.html` is in the working directory. It is a made-up shop; no network is
involved. **Use only the Python standard library** (`html.parser`, `re`, ...): no BeautifulSoup,
lxml or requests. The page may be formatted differently from the sample (attribute order,
quote style, line breaks inside tags, upper-case tags, nested tags), so do not rely on the
exact text of the sample.

Rules:

- A *product* is an `<li>` element whose `class` attribute contains the word `product`
  (classes are separated by whitespace; `product-list`, `products` and `sponsor` do not count).
  Elements outside such an `<li>` are ignored, even if they have a `name` or `price` class.
- The product's *name* is the text of the first element inside it whose class contains the
  word `name`. The *price* is the text of the first element inside it whose class contains
  the word `price` (`price-note` does not count). The text of an element includes the text of
  everything nested in it (tags removed), HTML entities decoded (`&amp;`, `&#39;`, `&#36;`),
  whitespace runs collapsed to a single space, and surrounding whitespace removed.
- A product without a name element is skipped.
- Price value: remove every `$` and `,` from the price text, strip whitespace, convert with
  `float()`. If the product has no price element, or the text still is not a number
  (for example `Sold out`), the price is `None`.
- Return one dict per product, `{"name": str, "price": float | None}`, in document order.
  A page with no products gives `[]`.
- Void elements such as `<img>` and `<br>` may appear anywhere inside a product.
