from solution import clean_emails

EXPECTED = ['ann.lee@example.com',
 'bob@example.com',
 'flo@mail.example.org',
 'kit@sub.example.co.uk']


def write(tmp_path, body):
    p = tmp_path / "c.csv"
    p.write_text("name,email\n" + body)
    return str(p)


def test_fixture():
    assert clean_emails("contacts.csv") == EXPECTED


def test_dedupe_keeps_first_position_and_lowercases(tmp_path):
    path = write(tmp_path, "a,B@x.io\nb,a@x.io\nc, b@X.IO \nd,c@y.io\ne,A@x.io\n")
    assert clean_emails(path) == ["b@x.io", "a@x.io", "c@y.io"]


def test_invalid_shapes_are_dropped(tmp_path):
    bad = ["plain", "a@b", "a@b.", "a@.b.com", "@b.com", "a@@b.com", "a@b@c.com", "a b@c.com", ""]
    path = write(tmp_path, "".join(f"n,{e}\n" for e in bad) + "n,ok@b.co\n")
    assert clean_emails(path) == ["ok@b.co"]


def test_header_only(tmp_path):
    assert clean_emails(write(tmp_path, "")) == []


def test_extra_columns_ignored(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("id,name,email\n1,Q,Q@z.com\n2,R,q@z.com\n")
    assert clean_emails(str(p)) == ["q@z.com"]
