import romt.crate
from romt.crate import CrateFilter


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


def test_crate_filter() -> None:
    f = CrateFilter()
    assert f.name_matches("arbitrary")
    assert f.filter_crate_versions("name", {"1", "2"}) == {"1", "2"}
    f.add("name@1.0.0")
    assert not f.name_matches("arbitrary")
    assert f.filter_crate_versions("arbitrary", {"1", "2"}) == set()
    assert f.name_matches("name")
    assert f.filter_crate_versions("name", {"2", "1.0.0"}) == {"1.0.0"}

    # All versions of "name":
    f.add("name")
    assert f.filter_crate_versions("name", {"1", "2", "3"}) == {"1", "2", "3"}
    f.add("name2@2.0")
    f.add("name2@2.1")
    f.add("name2@3.7")
    assert f.filter_crate_versions("name2", {"1.0", "2.1", "3.5"}) == {"2.1"}
    f.add("nam*@3.0")
    assert f.name_matches("name8")
    assert f.filter_crate_versions("name3", {"1.0", "3.0"}) == {"3.0"}
    assert f.filter_crate_versions("name4", {"3.1", "3.0"}) == {"3.0"}

    f.add("[ab]*[yz]?@[!12]*")
    assert f.name_matches("ably1")
    assert not f.name_matches("ably")
    assert f.name_matches("buzz!")
    assert not f.name_matches("cuzz!")
    assert f.filter_crate_versions("ably1", {"11", "21", "31"}) == {"31"}
    assert f.filter_crate_versions("buzz!", {"1.0", "1.1"}) == set()

    # Version "8" of any crate:
    f.add("@8")
    assert f.filter_crate_versions("any-crate", {"8", "9"}) == {"8"}
