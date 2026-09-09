"""All bot settings live in a single YAML file (see config.example.yaml).

Loading validates eagerly and raises InvalidConfigError, so a typo or a
missing token fails at startup with a clear message instead of at the first
incoming message.
"""
from pathlib import Path
from typing import List

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    field_validator,
)

DEFAULT_CONFIG_PATH = Path("config.yaml")

PLACEHOLDER_TOKEN = "123456789:AAExampleExampleExampleExampleExample"


class InvalidConfigError(Exception):
    pass


class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    # StrictInt per *element*, not Field(strict=True) on the list: the latter
    # only constrains the list itself, and pydantic's lax mode coerces
    # bool -> int, so `- true` would silently become user id 1.
    allowed_user_ids: List[StrictInt]

    @field_validator("token")
    @classmethod
    def _reject_placeholder(cls, value: str) -> str:
        if not value:
            raise ValueError("is required (get one from @BotFather)")
        if value == PLACEHOLDER_TOKEN:
            raise ValueError("is still the placeholder from config.example.yaml")
        return value

    @field_validator("allowed_user_ids")
    @classmethod
    def _reject_empty(cls, value: List[int]) -> List[int]:
        # Deliberately strict: this is the trust boundary in front of a
        # physical printer, so an empty allowlist is an error rather than
        # silently meaning "everyone".
        if not value:
            raise ValueError(
                "must be a non-empty list of numeric Telegram user ids allowed to print"
            )
        return value


class QlapiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str = "http://qlapi:80"
    timeout_seconds: float = Field(default=30.0, strict=True, gt=0)

    @field_validator("base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


class PrintConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    copies: int = Field(default=1, strict=True, ge=1)
    rotate: bool = False


class Config(BaseModel):
    # extra="forbid" so a typo'd key (`qlappi:`) is an error instead of being
    # silently ignored while the defaults quietly apply.
    model_config = ConfigDict(extra="forbid")

    telegram: TelegramConfig
    qlapi: QlapiConfig = QlapiConfig()
    print: PrintConfig = PrintConfig()


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Reads and validates the YAML config at `path`."""
    try:
        text = Path(path).read_text()
    except FileNotFoundError:
        raise InvalidConfigError(
            f"Config file not found at {path}. Copy config.example.yaml to config.yaml."
        )

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InvalidConfigError(f"{path} is not valid YAML: {exc}")

    if raw is not None and not isinstance(raw, dict):
        raise InvalidConfigError(f"{path} must contain a YAML mapping at the top level")

    try:
        return Config.model_validate(raw or {})
    except ValidationError as exc:
        raise InvalidConfigError(f"{path} is invalid:\n{exc}") from exc
