from romt import common


def test_is_date() -> None:
    is_date = common.is_date
    assert is_date("2020-01-23")
    assert not is_date("2020-01-2")
    assert not is_date("2020-01-234")
    assert not is_date("20-01-23")


def test_is_version() -> None:
    is_version = common.is_version
    assert is_version("1.2.0")
    assert is_version("1.2.3")
    assert not is_version("1.2")
    assert not is_version("a.b.c")


def test_split_word() -> None:
    assert common.split_word("") == [""]
    assert common.split_word("a") == ["a"]
    assert common.split_word("a,b") == ["a", "b"]
    assert common.split_word("a,") == ["a", ""]
    assert common.split_word(",") == ["", ""]
    assert common.split_word("a    b") == ["a", "b"]


def test_split_flatten_words() -> None:
    split_flatten_words = common.split_flatten_words
    assert split_flatten_words([""]) == [""]
    assert split_flatten_words(["a"]) == ["a"]
    assert split_flatten_words(["a", "b"]) == ["a", "b"]
    assert split_flatten_words(["b,a", "b"]) == ["b", "a"]
    assert split_flatten_words([",a", "b    c"]) == ["", "a", "b", "c"]


def test_split_flatten_normalize_words() -> None:
    f = common.split_flatten_normalize_words
    assert f([""]) == []
    assert f(["  c  b,,,a "]) == ["a", "b", "c"]
    assert f(["d,b", "c , a"]) == ["a", "b", "c", "d"]


def test_normalize_patterns() -> None:
    normalize_patterns = common.normalize_patterns
    assert normalize_patterns([""]) == []
    assert normalize_patterns(["  c  b,,,a "]) == ["a", "b", "c"]
    assert normalize_patterns(["d,b", "c , a"]) == ["a", "b", "c", "d"]
    assert normalize_patterns(["a,*,b"]) == ["*"]
