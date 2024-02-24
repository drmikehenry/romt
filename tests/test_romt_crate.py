import romt.crate


def test_crate_prefix_from_name() -> None:
    lower = romt.crate.PrefixStyle.LOWER
    mixed = romt.crate.PrefixStyle.MIXED
    assert romt.crate.crate_prefix_from_name("a", lower) == "1"
    assert romt.crate.crate_prefix_from_name("a", mixed) == "1"
    assert romt.crate.crate_prefix_from_name("ab", lower) == "2"
    assert romt.crate.crate_prefix_from_name("ab", mixed) == "2"
    assert romt.crate.crate_prefix_from_name("AbC", lower) == "3/a"
    assert romt.crate.crate_prefix_from_name("AbC", mixed) == "3/A"
    assert romt.crate.crate_prefix_from_name("AbCd", lower) == "ab/cd"
    assert romt.crate.crate_prefix_from_name("AbCd", mixed) == "Ab/Cd"
