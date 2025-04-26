from romt import integrity

import pytest

# Sample hash file:
#  URL:  https://static.rust-lang.org/dist/
#          2024-02-08/channel-rust-stable.toml.sha256
#  hash: 7b89a56897a1581ca66312468276ee08e6d596a3254128a567c1658c6f733c76
#  name: channel-rust-stable.toml
#  Format:
#    - text file:   64-character hash string, two spaces, filename.
#    - binary file: 64-character hash string, space, asterisk, filename.


def test_parse_hash_text() -> None:
    expected_hash, expected_name = (
        "7b89a56897a1581ca66312468276ee08e6d596a3254128a567c1658c6f733c76",
        "channel-rust-stable.toml",
    )

    hash_text = f"{expected_hash}  {expected_name}"
    hash, name = integrity.parse_hash_text(hash_text)
    assert hash == expected_hash
    assert name == expected_name

    hash_text = f"{expected_hash} *{expected_name}"
    hash, name = integrity.parse_hash_text(hash_text)
    assert hash == expected_hash
    assert name == expected_name

    # Short hash:
    hash_text = f"{expected_hash[:-1]}  {expected_name}"
    with pytest.raises(ValueError):
        integrity.parse_hash_text(hash_text)

    # Invalid hex character:
    hash_text = f"{'z' + expected_hash[:-1]}  {expected_name}"
    with pytest.raises(ValueError):
        integrity.parse_hash_text(hash_text)

    # Too few spaces:
    hash_text = f"{expected_hash} {expected_name}"
    with pytest.raises(ValueError):
        integrity.parse_hash_text(hash_text)


def test_format_hash_text() -> None:
    hash = "7b89a56897a1581ca66312468276ee08e6d596a3254128a567c1658c6f733c76"
    name = "channel-rust-stable.toml"
    expected_hash_text = f"{hash} *{name}\n"
    hash_text = integrity.format_hash_text(hash, name)
    assert hash_text == expected_hash_text
