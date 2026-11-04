from solution import parse_products


def page(body: str) -> str:
    return f"<html><body><ul>{body}</ul></body></html>"


def test_fixture():
    html = open("store.html", encoding="utf-8").read()
    assert parse_products(html) == [
        {"name": "Desk Lamp", "price": 24.5},
        {"name": "Oak Bookshelf", "price": 1249.0},
        {"name": "Tom & Jerry's Mug", "price": 9.99},
        {"name": "Floor Rug", "price": None},
        {"name": "Wall Clock", "price": None},
    ]


def test_attribute_order_multiple_classes_and_quote_style():
    html = page(
        "<li data-id='7' class='item product featured'>"
        "<h3 data-x=1 class=\"name\">Desk Lamp</h3>"
        "<span data-cur=\"usd\" class='price big'>$24.50</span></li>"
    )
    assert parse_products(html) == [{"name": "Desk Lamp", "price": 24.5}]


def test_newlines_inside_tags_and_uppercase_tags():
    html = page(
        "<LI\n   CLASS=\"product\"\n>\n<SPAN\n class='name'\n>\n  Big\n   Pot\n</SPAN>\n"
        "<SPAN CLASS=\"price\"\n>  $ 15.00\n</SPAN></LI>"
    )
    assert parse_products(html) == [{"name": "Big Pot", "price": 15.0}]


def test_nested_tags_and_entities_in_name_and_price():
    html = page(
        '<li class="product"><span class="name"><a href="/p/1"><b>Oak</b> Shelf</a> &amp; Co</span>'
        '<div class="price"><strong>&#36;</strong>1,015<small>.50</small></div></li>'
    )
    assert parse_products(html) == [{"name": "Oak Shelf & Co", "price": 1015.5}]


def test_void_elements_inside_product_and_inside_name():
    html = page(
        '<li class="product"><img src="a.png"><br><span class="name"><img alt="x"> Chair</span>'
        '<hr><span class="price">$40</span></li>'
        '<li class="product"><span class="name">Stool</span><img src="b.png"/><span class="price">$8</span></li>'
    )
    assert parse_products(html) == [
        {"name": "Chair", "price": 40.0},
        {"name": "Stool", "price": 8.0},
    ]


def test_missing_and_unparsable_prices_and_missing_name():
    html = page(
        '<li class="product"><b class="name">A</b></li>'
        '<li class="product"><b class="name">B</b><b class="price">Sold out</b></li>'
        '<li class="product"><b class="price">$3.00</b></li>'
        '<li class="product"><b class="name">C</b><b class="price"></b></li>'
        '<li class="product"><b class="name">D</b><b class="price">USD 5</b></li>'
        '<li class="product"><b class="name">E</b><b class="price">19</b></li>'
    )
    assert parse_products(html) == [
        {"name": "A", "price": None},
        {"name": "B", "price": None},
        {"name": "C", "price": None},
        {"name": "D", "price": None},
        {"name": "E", "price": 19.0},
    ]


def test_class_word_matching_is_exact():
    html = page(
        '<li class="product-card"><b class="name">no</b><b class="price">$1</b></li>'
        '<li class="products"><b class="name">no</b></li>'
        '<li class="product"><b class="name-tag">x</b><b class="name">Real</b>'
        '<b class="price-note">free</b><b class="price">$2</b></li>'
        '<div class="product"><b class="name">div</b></div>'
    )
    assert parse_products(html) == [{"name": "Real", "price": 2.0}]


def test_first_matching_element_wins_and_document_order_kept():
    html = page(
        '<li class="product"><i class="name">Z-first</i><i class="name">ignored</i>'
        '<i class="price">$30</i><i class="price">$99</i></li>'
        '<li class="product"><i class="name">A-second</i><i class="price">$10</i></li>'
        '<li class="product"><i class="name">M-third</i><i class="price">$20</i></li>'
    )
    assert parse_products(html) == [
        {"name": "Z-first", "price": 30.0},
        {"name": "A-second", "price": 10.0},
        {"name": "M-third", "price": 20.0},
    ]


def test_outside_elements_ignored_and_empty_pages():
    html = '<span class="name">Loose</span><span class="price">$1</span>' + page("")
    assert parse_products(html) == []
    assert parse_products("") == []


def test_price_is_float_type():
    (item,) = parse_products(page('<li class="product"><b class="name">X</b><b class="price">$7</b></li>'))
    assert type(item["price"]) is float
