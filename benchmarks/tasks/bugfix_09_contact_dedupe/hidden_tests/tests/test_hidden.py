from contacts import dedupe, find_contact
from normalize import initials, normalize_email, normalize_name


def test_dedupe_ignores_case_and_inner_whitespace():
    contacts = [{"name": "Ada Lovelace"}, {"name": "ada   LOVELACE"}, {"name": "Alan Turing"}]
    assert dedupe(contacts) == [{"name": "Ada Lovelace"}, {"name": "Alan Turing"}]


def test_dedupe_uses_full_case_folding():
    contacts = [{"name": "Straße Müller", "id": 1}, {"name": "STRASSE MÜLLER", "id": 2}]
    assert dedupe(contacts) == [{"name": "Straße Müller", "id": 1}]


def test_dedupe_handles_tabs_and_edges():
    contacts = [{"name": "  Bo\tPeep "}, {"name": "bo peep"}, {"name": "Bo  Peeps"}]
    assert dedupe(contacts) == [{"name": "  Bo\tPeep "}, {"name": "Bo  Peeps"}]


def test_dedupe_keeps_the_first_and_the_order():
    contacts = [{"name": "b", "n": 1}, {"name": "A", "n": 2}, {"name": "B", "n": 3},
                {"name": "a", "n": 4}, {"name": "c", "n": 5}]
    assert [c["n"] for c in dedupe(contacts)] == [1, 2, 5]
    original = list(contacts)
    dedupe(contacts)
    assert contacts == original


def test_dedupe_exact_duplicates_and_trivial_lists():
    one = {"name": "Eve"}
    assert dedupe([one, {"name": "Eve"}, one]) == [one]
    assert dedupe([]) == []
    assert dedupe([{"name": "x"}, {"name": "y"}]) == [{"name": "x"}, {"name": "y"}]


def test_find_contact_with_case_folding():
    contacts = [{"name": "Ada"}, {"name": "Straße"}, {"name": "Straße"}]
    assert find_contact(contacts, "STRASSE") is contacts[1]
    assert find_contact(contacts, "  straße ") is contacts[1]
    assert find_contact(contacts, "ADA") is contacts[0]


def test_find_contact_misses_and_whitespace():
    contacts = [{"name": "Ada  King"}]
    assert find_contact(contacts, "ada king") is contacts[0]
    assert find_contact(contacts, "Ada") is None
    assert find_contact([], "x") is None


def test_normalize_name():
    assert normalize_name("  Ada \t LOVELACE\n") == "ada lovelace"
    assert normalize_name("Straße") == "strasse"
    assert normalize_name("") == ""


def test_email_and_initials_are_unchanged():
    assert normalize_email("  Ada@Example.COM ") == "ada@example.com"
    assert initials("ada king  lovelace") == "AKL"
    assert initials("  grace HOPPER ") == "GH"
    assert initials("") == ""


def test_case_folding_beyond_ascii_and_sharp_s():
    assert normalize_name("ΑΣΑ") == normalize_name("αςα") == "ασα"
    contacts = [{"name": "ΑΣΑ Κ"}, {"name": "αςα κ"}]
    assert dedupe(contacts) == [{"name": "ΑΣΑ Κ"}]
    assert find_contact([{"name": "αςα"}], "ΑΣΑ") == {"name": "αςα"}
