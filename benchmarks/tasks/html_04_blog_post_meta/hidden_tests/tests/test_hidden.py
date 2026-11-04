from solution import parse_post


def post(inner: str, head: str = "") -> str:
    return f"<html><head>{head}</head><body><article>{inner}</article></body></html>"


def test_fixture():
    html = open("post.html", encoding="utf-8").read()
    assert parse_post(html) == {
        "title": "Tide Pools at Dawn",
        "date": "2024-03-05",
        "author": "Mira Okafor",
        "tags": ["coast", "photography"],
    }


def test_returns_exactly_the_four_keys():
    assert set(parse_post(post("<h1>T</h1>"))) == {"title", "date", "author", "tags"}


def test_title_normalisation_and_first_h1_only():
    inner = "<h1>\n  Rock &amp; Roll:\n  <em>Notes</em>   from  the &#39;road&#39;\n</h1><h1>Second</h1>"
    assert parse_post(post(inner))["title"] == "Rock & Roll: Notes from the 'road'"


def test_h1_outside_post_ignored_and_missing_title_is_none():
    html = "<body><h1>Site name</h1><article><p>no heading</p></article><h1>Footer</h1></body>"
    assert parse_post(html)["title"] is None


def test_date_forms_and_first_time_with_datetime_wins():
    t = lambda attrs: post(f"<h1>x</h1><time {attrs}>x</time>")
    assert parse_post(t('datetime="2024-03-05T09:30:00+01:00"'))["date"] == "2024-03-05"
    assert parse_post(t('class=d datetime=" 2023-12-31 "'))["date"] == "2023-12-31"
    assert parse_post(t("datetime='2022-01-02'"))["date"] == "2022-01-02"
    two = post('<time>yesterday</time><time datetime="2021-05-06">a</time><time datetime="2021-07-08">b</time>')
    assert parse_post(two)["date"] == "2021-05-06"
    assert parse_post(post("<time>today</time>"))["date"] is None
    assert parse_post(post("<p>no time</p>"))["date"] is None


def test_tags_rel_words_dedupe_order_and_case():
    inner = (
        '<a rel="tag" href="/t/zeta">Zeta</a>'
        '<a href="/t/alpha" rel="nofollow  tag-ish tagged">no</a>'
        '<a href="/t/b" rel="tag nofollow">beta</a>'
        '<a rel="category" href="/c">cat</a>'
        '<a href="/p">plain</a>'
        '<a rel="tag" href="/t/zeta">Zeta</a>'
        '<a rel="tag" href="/t/z2">zeta</a>'
        '<a rel="tag" href="/t/e"> </a>'
        '<A HREF="/t/n" REL="tag"><span>Nested</span>\n <b>Tag</b></A>'
    )
    assert parse_post(post(inner))["tags"] == ["Zeta", "beta", "zeta", "Nested Tag"]


def test_author_meta_variants():
    assert parse_post(post("", '<meta content="Ann Lee" name="author">'))["author"] == "Ann Lee"
    assert parse_post(post("", "<META NAME='Author' CONTENT='  Bo &amp; Co  '>"))["author"] == "Bo & Co"
    first = '<meta name="author" content="First"><meta name="author" content="Second">'
    assert parse_post(post("", first))["author"] == "First"
    assert parse_post(post("", '<meta name="description" content="x">'))["author"] is None
    assert parse_post(post("", '<meta name="author" content="  ">'))["author"] is None
    assert parse_post(post("", '<meta name="author">'))["author"] is None
    assert parse_post(post(""))["author"] is None


def test_nested_article_ignored_even_before_post_content():
    inner = (
        "<h1>Real title</h1>"
        '<article class="related"><h1>Related</h1><time datetime="2020-01-01">old</time>'
        '<a rel="tag" href="/t/rel">related</a></article>'
        '<time datetime="2024-02-02">new</time><a rel="tag" href="/t/own">own</a>'
    )
    assert parse_post(post(inner)) == {
        "title": "Real title", "date": "2024-02-02", "author": None, "tags": ["own"],
    }


def test_nested_article_h1_does_not_become_title():
    inner = '<p>intro</p><article><h1>Comment heading</h1></article>'
    assert parse_post(post(inner))["title"] is None
    after = '<h1>Own</h1><article><h1>Comment</h1></article><h1>Late</h1>'
    assert parse_post(post(after))["title"] == "Own"


def test_only_first_top_level_article_counts():
    html = (
        "<article><p>empty first post</p></article>"
        '<article><h1>Second</h1><time datetime="2024-01-01">d</time>'
        '<a rel="tag" href="/t">tag</a></article>'
    )
    assert parse_post(html) == {"title": None, "date": None, "author": None, "tags": []}


def test_elements_outside_post_ignored():
    html = (
        '<header><h1>Blog</h1><a rel="tag" href="/p">popular</a><time datetime="2000-01-01">x</time></header>'
        '<article><h1>Post</h1></article>'
        '<footer><a rel="tag" href="/f">footer</a><time datetime="2030-01-01">y</time></footer>'
    )
    assert parse_post(html) == {"title": "Post", "date": None, "author": None, "tags": []}


def test_no_article_still_reads_author():
    html = '<head><meta name="author" content="Zed"></head><body><h1>Hi</h1><time datetime="2024-01-01">x</time></body>'
    assert parse_post(html) == {"title": None, "date": None, "author": "Zed", "tags": []}
    assert parse_post("") == {"title": None, "date": None, "author": None, "tags": []}
