from solution import count_levels

EXPECTED = {'DEBUG': 9, 'INFO': 14, 'WARNING': 6, 'ERROR': 2, 'CRITICAL': 0}
ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def test_fixture_counts_and_key_order():
    result = count_levels("app.log")
    assert list(result) == ORDER
    assert result == EXPECTED


def test_empty_file_has_all_levels_zero(tmp_path):
    p = tmp_path / "e.log"
    p.write_text("")
    assert count_levels(str(p)) == dict.fromkeys(ORDER, 0)


def test_only_leading_level_counts(tmp_path):
    p = tmp_path / "x.log"
    p.write_text(
        "2024-01-01 00:00:00 [INFO] saw [ERROR] in text\n"
        "2024-01-01 00:00:01 [CRITICAL] disk full\n"
        "2024-01-01 00:00:02 [critical] not a level\n"
        "2024-01-01 00:00:03 [TRACE] unknown\n"
        "  2024-01-01 00:00:04 [ERROR] indented is not an entry\n"
        "[ERROR] no timestamp\n"
        "Traceback (most recent call last):\n"
        "\n"
        "2024-01-01 00:00:05 [WARNING] w1\n"
        "2024-01-01 00:00:06 [WARNING] w2\n"
    )
    assert count_levels(str(p)) == {
        "DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 0, "CRITICAL": 1,
    }


def test_no_trailing_newline(tmp_path):
    p = tmp_path / "y.log"
    p.write_text("2024-02-02 10:00:00 [DEBUG] a\n2024-02-02 10:00:01 [DEBUG] b")
    assert count_levels(str(p))["DEBUG"] == 2
