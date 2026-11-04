from solution import parse_table


def test_fixture():
    html = open("report.html", encoding="utf-8").read()
    assert parse_table(html) == [
        ["Region", "Q1", "Q2"],
        ["North & East", "1,200", "1,350"],
        ["Café Belt", "", "980"],
        ["South", "2,010", "2,044"],
        ["Total", "3,210", "4,374"],
    ]


def test_uppercase_tags_attributes_and_newlines_in_tags():
    html = (
        "<TABLE border=1><TR\n class='x'><TH\n scope=col>Name</TH><TH>Age</TH></TR>"
        "<TR><TD\n>Ann</TD\n><TD data-v=\"1\">31</TD></TR></TABLE>"
    )
    assert parse_table(html) == [["Name", "Age"], ["Ann", "31"]]


def test_nested_tags_and_split_text_in_cells():
    html = (
        "<table><tr><td><b>1</b>,<i>200</i></td><td>a <b>b</b> c</td>"
        "<td><span><a href='#'>deep <u>link</u></a></span></td></tr></table>"
    )
    assert parse_table(html) == [["1,200", "a b c", "deep link"]]


def test_entities_decoded_once_and_whitespace_collapsed():
    html = (
        "<table><tr><td>Tom &amp; Jerry</td><td>&lt;b&gt;</td><td>&#38;&amp;amp;</td>"
        "<td>  x \n\t  y &nbsp; z  </td><td>&nbsp;</td><td>5&nbsp;kg</td></tr></table>"
    )
    assert parse_table(html) == [["Tom & Jerry", "<b>", "&&amp;", "x y z", "", "5 kg"]]


def test_empty_cells_and_ragged_rows_kept():
    html = "<table><tr><td></td><td> </td></tr><tr><td>only</td></tr><tr><td>1</td><td>2</td><td>3</td></tr></table>"
    assert parse_table(html) == [["", ""], ["only"], ["1", "2", "3"]]


def test_caption_comments_and_stray_text_ignored():
    html = (
        "<table><caption>Title <b>here</b></caption>stray"
        "<!-- <tr><td>hidden</td></tr> -->"
        "<tr>between<td>kept</td>between</tr></table>"
    )
    assert parse_table(html) == [["kept"]]


def test_empty_rows_dropped_and_sections_in_document_order():
    html = (
        "<table><tfoot><tr><td>foot</td></tr></tfoot><thead><tr><th>head</th></tr></thead>"
        "<tbody><tr></tr><tr><td>body</td></tr></tbody></table>"
    )
    assert parse_table(html) == [["foot"], ["head"], ["body"]]


def test_only_first_table_is_used():
    html = (
        "<p>intro</p><table><tr><td>one</td></tr></table>"
        "<table><tr><td>two</td></tr><tr><td>three</td></tr></table>"
    )
    assert parse_table(html) == [["one"]]


def test_content_before_table_does_not_leak_in():
    html = "<div><td>stray</td><p>x</p></div><table><tr><td>real</td></tr></table>"
    assert parse_table(html) == [["real"]]


def test_no_table_and_empty_table():
    assert parse_table("<p>nothing</p>") == []
    assert parse_table("") == []
    assert parse_table("<table></table>") == []
