from nvai.datetime_utils import parse_expiredate


def test_parse_date_only_uses_local_midnight():
    dt = parse_expiredate("2026-07-09")
    assert dt.year == 2026
    assert dt.month == 7
    assert dt.day == 9
    assert dt.hour == 0
    assert dt.tzinfo is not None


def test_parse_iso_timezone():
    dt = parse_expiredate("2026-07-09T00:00:00+09:00")
    assert dt.isoformat() == "2026-07-09T00:00:00+09:00"


def test_parse_slash_date_mm_dd_yyyy():
    dt = parse_expiredate("01/08/2027")
    assert (dt.year, dt.month, dt.day, dt.hour) == (2027, 1, 8, 0)


def test_parse_slash_date_yyyy_mm_dd():
    dt = parse_expiredate("2027/08/01")
    assert (dt.year, dt.month, dt.day, dt.hour) == (2027, 8, 1, 0)
