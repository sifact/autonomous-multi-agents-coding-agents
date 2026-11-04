from solution import extract_links

BASE = "https://blog.example.test/2024/index.html"


def links(body: str, base: str = BASE):
    return extract_links(f"<html><body>{body}</body></html>", base)


def test_fixture():
    html = open("blog_index.html", encoding="utf-8").read()
    assert extract_links(html, BASE) == [
        {"text": "Home", "url": "https://blog.example.test/"},
        {"text": "About us", "url": "https://blog.example.test/about.html"},
        {"text": "Archive", "url": "https://blog.example.test/2024/archive/"},
        {"text": "Rain, & more rain",
         "url": "https://blog.example.test/2024/posts/rain.html?ref=home&lang=en"},
        {"text": "An outside view", "url": "https://other.example.test/x"},
        {"text": "CDN", "url": "https://cdn.example.test/lib.js"},
        {"text": "Next page", "url": "https://blog.example.test/2024/index.html?page=2"},
        {"text": "", "url": "https://blog.example.test/2024/posts/rain.html#comments"},
    ]


def test_relative_resolution_against_other_bases():
    assert links('<a href="a/b">x</a>', "http://h.example.test") == [
        {"text": "x", "url": "http://h.example.test/a/b"}]
    assert links('<a href="./x/../y">x</a>', "http://h.example.test/dir/") == [
        {"text": "x", "url": "http://h.example.test/dir/y"}]
    assert links('<a href="r.html">x</a>', "http://h.example.test/p/q.html?z=1") == [
        {"text": "x", "url": "http://h.example.test/p/r.html"}]
    assert links('<a href="../../up.html">x</a>', "http://h.example.test/a/b/c.html") == [
        {"text": "x", "url": "http://h.example.test/up.html"}]
    assert links('<a href="/root">x</a>', "http://h.example.test/a/b/c.html") == [
        {"text": "x", "url": "http://h.example.test/root"}]


def test_skipped_hrefs_any_case_and_padding():
    body = (
        '<a href="#top">1</a><a href="  #pad ">2</a><a href="mailto:a@b.test">3</a>'
        '<a href="MAILTO:a@b.test">4</a><a href="tel:+123">5</a><a href="JavaScript:void(0)">6</a>'
        '<a href="">7</a><a href="   ">8</a><a name="x">9</a><a>10</a>'
        '<a href="  /kept  ">kept</a>'
    )
    assert links(body) == [{"text": "kept", "url": "https://blog.example.test/kept"}]


def test_attribute_styles_case_and_newlines():
    body = (
        "<A\n  HREF='x.html'\n  class=nav\n>First</A>"
        "<a class=y href=y.html>Second</a>"
        '<a title="t" href\n=\n"z.html">Third</a>'
    )
    assert [l["url"] for l in links(body)] == [
        "https://blog.example.test/2024/x.html",
        "https://blog.example.test/2024/y.html",
        "https://blog.example.test/2024/z.html",
    ]


def test_text_nested_tags_entities_whitespace():
    body = (
        '<a href="/t"> Read\n   <b>more</b> about\t<i>Tom &amp; <u>Jerry</u></i>&nbsp;now </a>'
        '<a href="/u"><span>&#36;5</span></a>'
    )
    assert links(body) == [
        {"text": "Read more about Tom & Jerry now", "url": "https://blog.example.test/t"},
        {"text": "$5", "url": "https://blog.example.test/u"},
    ]


def test_entities_in_href_decoded():
    body = '<a href="/s?q=a&amp;b=2&#38;c=3">s</a>'
    assert links(body) == [{"text": "s", "url": "https://blog.example.test/s?q=a&b=2&c=3"}]


def test_duplicates_kept_and_document_order():
    body = '<a href="/z">Z</a><a href="/a">A</a><a href="/z">Z</a>'
    assert [l["text"] for l in links(body)] == ["Z", "A", "Z"]


def test_base_tag_ignored_and_image_only_text_empty():
    html = (
        '<html><head><base href="http://wrong.example.test/"></head><body>'
        '<a href="p.html" title="Tip"><img src="i.png" alt="Picture" title="Tip"></a></body></html>'
    )
    assert extract_links(html, "http://right.example.test/d/") == [
        {"text": "", "url": "http://right.example.test/d/p.html"}]


def test_absolute_and_protocol_relative_urls():
    body = '<a href="http://a.example.test/x">1</a><a href="//c.example.test/y">2</a>'
    assert [l["url"] for l in links(body, "https://b.example.test/")] == [
        "http://a.example.test/x", "https://c.example.test/y"]


def test_no_links():
    assert links("<p>nothing here</p>") == []
    assert extract_links("", BASE) == []


def test_only_a_elements_count():
    html = ('<head><link rel=stylesheet href="s.css"></head><map><area href="/z"></map>'
            '<a href="ok">ok</a>')
    assert extract_links(html, "https://b.example.test/d/") == [
        {"text": "ok", "url": "https://b.example.test/d/ok"}]


def test_other_schemes_kept_and_any_whitespace_stripped():
    html = (
        '<a href="ftp://f.example.test/x">f</a><a href="data:text/plain,hi">d</a>'
        '<a href="\n\t#frag">n</a><a href="\t/t\n">t</a><a href="/r?u=mailto:a@b">r</a>'
    )
    assert extract_links(html, "https://b.example.test/d/") == [
        {"text": "f", "url": "ftp://f.example.test/x"},
        {"text": "d", "url": "data:text/plain,hi"},
        {"text": "t", "url": "https://b.example.test/t"},
        {"text": "r", "url": "https://b.example.test/r?u=mailto:a@b"},
    ]


def test_unclosed_anchor_ends_at_next_anchor_or_end_of_page():
    base = "https://b.example.test/"
    html = '<a href="/one">First <b>link</b><a href="/two">Second'
    assert extract_links(html, base) == [
        {"text": "First link", "url": "https://b.example.test/one"},
        {"text": "Second", "url": "https://b.example.test/two"},
    ]
    assert extract_links('<p><a href="/last">tail', base) == [
        {"text": "tail", "url": "https://b.example.test/last"}]
