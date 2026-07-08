from io import StringIO

import pytest

from nvai.ui import Status


def test_status_non_tty_prints_start_and_ok():
    stream = StringIO()
    with Status("Doing work", stream=stream, interval=0.001):
        pass
    output = stream.getvalue()
    assert "[status] Doing work..." in output
    assert "[ok] Doing work" in output


def test_status_non_tty_prints_error_on_exception():
    stream = StringIO()
    with pytest.raises(RuntimeError):
        with Status("Doing work", stream=stream, interval=0.001):
            raise RuntimeError("boom")
    output = stream.getvalue()
    assert "[status] Doing work..." in output
    assert "[error] Doing work failed" in output
