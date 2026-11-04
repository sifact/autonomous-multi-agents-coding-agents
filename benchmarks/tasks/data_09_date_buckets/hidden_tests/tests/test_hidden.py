import pytest

from solution import bucket_events

EXPECTED_DAY = {'2024-01-01': 1,
 '2024-01-02': 3,
 '2024-01-03': 0,
 '2024-01-04': 2,
 '2024-01-05': 0,
 '2024-01-06': 1,
 '2024-01-07': 0,
 '2024-01-08': 0,
 '2024-01-09': 2,
 '2024-01-10': 3,
 '2024-01-11': 0,
 '2024-01-12': 0,
 '2024-01-13': 0,
 '2024-01-14': 0,
 '2024-01-15': 0,
 '2024-01-16': 0,
 '2024-01-17': 3,
 '2024-01-18': 3,
 '2024-01-19': 0,
 '2024-01-20': 0,
 '2024-01-21': 0,
 '2024-01-22': 0,
 '2024-01-23': 0,
 '2024-01-24': 0,
 '2024-01-25': 0,
 '2024-01-26': 0,
 '2024-01-27': 0,
 '2024-01-28': 0,
 '2024-01-29': 0,
 '2024-01-30': 0,
 '2024-01-31': 1,
 '2024-02-01': 0,
 '2024-02-02': 0,
 '2024-02-03': 1,
 '2024-02-04': 0,
 '2024-02-05': 0,
 '2024-02-06': 0,
 '2024-02-07': 0,
 '2024-02-08': 0,
 '2024-02-09': 0,
 '2024-02-10': 0,
 '2024-02-11': 0,
 '2024-02-12': 0,
 '2024-02-13': 0,
 '2024-02-14': 0,
 '2024-02-15': 0,
 '2024-02-16': 0,
 '2024-02-17': 0,
 '2024-02-18': 0,
 '2024-02-19': 0,
 '2024-02-20': 0,
 '2024-02-21': 0,
 '2024-02-22': 0,
 '2024-02-23': 0,
 '2024-02-24': 0,
 '2024-02-25': 0,
 '2024-02-26': 0,
 '2024-02-27': 0,
 '2024-02-28': 0,
 '2024-02-29': 1}


def write(tmp_path, stamps):
    p = tmp_path / "e.csv"
    p.write_text("timestamp,user\n" + "".join(f"{s},u\n" for s in stamps))
    return str(p)


def test_fixture_by_day_fills_gaps():
    result = bucket_events("events.csv", "day")
    assert list(result) == list(EXPECTED_DAY)
    assert result == EXPECTED_DAY


def test_hour_buckets_fill_gaps(tmp_path):
    path = write(tmp_path, ["2024-03-04T10:59:59", "2024-03-04T10:00:00", "2024-03-04T13:05:00"])
    assert bucket_events(path, "hour") == {
        "2024-03-04 10:00": 2, "2024-03-04 11:00": 0,
        "2024-03-04 12:00": 0, "2024-03-04 13:00": 1,
    }


def test_week_is_iso_monday_and_gap_filled(tmp_path):
    # 2024-03-03 is a Sunday (week of Monday 02-26); 03-04 is a Monday; 03-18 two weeks on.
    path = write(tmp_path, ["2024-03-03T23:59:00", "2024-03-04T00:00:00", "2024-03-18T12:00:00"])
    assert bucket_events(path, "week") == {
        "2024-02-26": 1, "2024-03-04": 1, "2024-03-11": 0, "2024-03-18": 1,
    }


def test_month_gaps_cross_year(tmp_path):
    path = write(tmp_path, ["2024-02-10T00:00:00", "2023-11-30T23:00:00", "2023-11-01T00:00:00"])
    assert bucket_events(path, "month") == {
        "2023-11": 2, "2023-12": 0, "2024-01": 0, "2024-02": 1,
    }


def test_offsets_are_converted_to_utc(tmp_path):
    path = write(tmp_path, [
        "2024-03-05T00:30:00+02:00",   # 2024-03-04 22:30 UTC
        "2024-03-05T01:00:00+02:00",   # 2024-03-04 23:00 UTC
        "2024-03-04T23:30:00-02:00",   # 2024-03-05 01:30 UTC
        "2024-03-05T08:00:00Z",
        "2024-03-05T09:00:00",
        "2024-03-05T22:00:00-05:00",
    ])
    assert bucket_events(path, "day") == {"2024-03-04": 2, "2024-03-05": 3, "2024-03-06": 1}


def test_bad_rows_skipped_and_empty(tmp_path):
    path = write(tmp_path, ["garbage", "", "2024-01-01T00:00:00"])
    assert bucket_events(path, "month") == {"2024-01": 1}
    assert bucket_events(write(tmp_path, ["nope"]), "day") == {}


def test_unknown_bucket_raises(tmp_path):
    with pytest.raises(ValueError):
        bucket_events(write(tmp_path, ["2024-01-01T00:00:00"]), "year")
