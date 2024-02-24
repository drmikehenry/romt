import pytest
import romt.toolchain
from romt import error


def test_parse_select() -> None:
    parse = romt.toolchain.parse_spec
    # Channel-only; date is "":
    assert parse("nightly") == ("", "nightly")
    assert parse("stable") == ("", "stable")
    assert parse("beta") == ("", "beta")
    assert parse("1.23.0") == ("", "1.23.0")
    # Channel and date:
    assert parse("nightly-2020-04-01") == ("2020-04-01", "nightly")
    assert parse("stable-latest") == ("latest", "stable")
    assert parse("beta-*") == ("*", "beta")
    # Date-only; channel is "*":
    assert parse("2020-04-01") == ("2020-04-01", "*")
    assert parse("latest") == ("latest", "*")
    assert parse("*") == ("*", "*")

    with pytest.raises(error.UsageError):
        parse("nightly-")
    with pytest.raises(error.UsageError):
        parse("-latest")
    with pytest.raises(error.UsageError):
        parse("lateststuff")
    with pytest.raises(error.UsageError):
        parse("**")
