from pathlib import Path

import pytest

from printbot.config import InvalidConfigError, load_config


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_missing_file_raises_helpful_error(tmp_path: Path):
    with pytest.raises(InvalidConfigError, match="not found"):
        load_config(tmp_path / "does-not-exist.yaml")


def test_valid_config_parses(tmp_path: Path):
    path = write(
        tmp_path,
        """
        telegram:
          token: "111:abc"
          allowed_user_ids: [111, 222]
        qlapi:
          base_url: "http://qlapi:80/"
          timeout_seconds: 5
        print:
          copies: 2
          rotate: true
        """,
    )

    config = load_config(path)

    assert config.telegram.token == "111:abc"
    assert config.telegram.allowed_user_ids == [111, 222]
    assert config.qlapi.base_url == "http://qlapi:80"  # trailing slash stripped
    assert config.qlapi.timeout_seconds == 5
    assert config.print.copies == 2
    assert config.print.rotate is True


def test_defaults_applied_when_sections_omitted(tmp_path: Path):
    path = write(tmp_path, 'telegram:\n  token: "111:abc"\n  allowed_user_ids: [111]\n')

    config = load_config(path)

    assert config.qlapi.base_url == "http://qlapi:80"
    assert config.print.copies == 1
    assert config.print.rotate is False


def test_missing_token_raises(tmp_path: Path):
    path = write(tmp_path, "telegram:\n  allowed_user_ids: [111]\n")

    with pytest.raises(InvalidConfigError, match="token"):
        load_config(path)


def test_placeholder_token_rejected(tmp_path: Path):
    path = write(
        tmp_path,
        'telegram:\n  token: "123456789:AAExampleExampleExampleExampleExample"\n'
        "  allowed_user_ids: [111]\n",
    )

    with pytest.raises(InvalidConfigError, match="placeholder"):
        load_config(path)


def test_empty_allowlist_rejected(tmp_path: Path):
    path = write(tmp_path, 'telegram:\n  token: "111:abc"\n  allowed_user_ids: []\n')

    with pytest.raises(InvalidConfigError, match="allowed_user_ids"):
        load_config(path)


def test_missing_allowlist_rejected(tmp_path: Path):
    path = write(tmp_path, 'telegram:\n  token: "111:abc"\n')

    with pytest.raises(InvalidConfigError, match="allowed_user_ids"):
        load_config(path)


def test_non_numeric_timeout_raises_config_error(tmp_path: Path):
    """Must surface as InvalidConfigError (clean startup message), not a raw
    ValueError traceback out of float().
    """
    path = write(
        tmp_path,
        'telegram:\n  token: "111:abc"\n  allowed_user_ids: [111]\n'
        'qlapi:\n  timeout_seconds: "abc"\n',
    )

    with pytest.raises(InvalidConfigError, match="timeout_seconds"):
        load_config(path)


def test_non_mapping_section_rejected(tmp_path: Path):
    path = write(
        tmp_path,
        'telegram:\n  token: "111:abc"\n  allowed_user_ids: [111]\nqlapi: "not-a-mapping"\n',
    )

    with pytest.raises(InvalidConfigError, match="valid dictionary"):
        load_config(path)


def test_non_numeric_allowlist_entry_rejected(tmp_path: Path):
    path = write(
        tmp_path, 'telegram:\n  token: "111:abc"\n  allowed_user_ids: ["not-a-number"]\n'
    )

    with pytest.raises(InvalidConfigError, match="valid integer"):
        load_config(path)


def test_bool_allowlist_entry_rejected(tmp_path: Path):
    """`- true` is a config typo, not user id 1. pydantic's default lax mode
    coerces bool -> int, so this only holds because the ids are StrictInt.
    """
    path = write(tmp_path, 'telegram:\n  token: "111:abc"\n  allowed_user_ids: [true]\n')

    with pytest.raises(InvalidConfigError, match="valid integer"):
        load_config(path)


def test_bool_numeric_fields_rejected(tmp_path: Path):
    """Same lax-coercion trap for the other numeric fields."""
    path = write(
        tmp_path,
        'telegram:\n  token: "111:abc"\n  allowed_user_ids: [111]\n'
        "qlapi:\n  timeout_seconds: true\n",
    )

    with pytest.raises(InvalidConfigError, match="timeout_seconds"):
        load_config(path)


def test_unknown_key_rejected(tmp_path: Path):
    """A typo'd section must fail loudly rather than silently falling back to
    defaults.
    """
    path = write(
        tmp_path,
        'telegram:\n  token: "111:abc"\n  allowed_user_ids: [111]\nqlappi:\n  base_url: "http://x"\n',
    )

    with pytest.raises(InvalidConfigError, match="Extra inputs are not permitted"):
        load_config(path)


def test_zero_copies_rejected(tmp_path: Path):
    path = write(
        tmp_path,
        'telegram:\n  token: "111:abc"\n  allowed_user_ids: [111]\nprint:\n  copies: 0\n',
    )

    with pytest.raises(InvalidConfigError, match="greater than or equal to 1"):
        load_config(path)
