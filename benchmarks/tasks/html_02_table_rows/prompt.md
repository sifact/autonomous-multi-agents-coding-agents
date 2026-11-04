Write `solution.py` with a function `parse_table(html: str) -> list[list[str]]`.

It takes the text of an HTML page (not a file name) and returns the rows of the **first**
`<table>` element on the page. The sample page `report.html` is in the working directory (a
made-up report; no network is involved). **Use only the Python standard library**
(`html.parser`, `re`, ...): no BeautifulSoup, lxml, pandas or requests. The page may be
formatted differently from the sample (upper-case tags, attributes, line breaks inside tags,
nested tags in cells), so do not rely on the exact text of the sample.

Rules:

- Return one list per `<tr>` of that table, in document order, whether the row sits directly in
  the table or inside `<thead>`, `<tbody>` or `<tfoot>`. Each row lists its cells (`<td>` and
  `<th>` alike, in order) as strings. A `<tr>` with no cells is left out.
- A cell's text is everything inside it, with nested tags removed, HTML entities decoded
  (`&amp;`, `&eacute;`, `&#38;`, `&nbsp;`), every run of whitespace (including a non-breaking
  space) collapsed to one space, and surrounding whitespace removed. An empty cell is `""`.
- The `<caption>`, comments and text between cells are not part of any row. Rows of any later
  table on the page are ignored. Tables are not nested, and no cell uses `colspan` or `rowspan`.
  Every `<tr>`, `<td>` and `<th>` is closed explicitly.
- Rows may have different numbers of cells; keep them as they are.
- A page without a table gives `[]`.
