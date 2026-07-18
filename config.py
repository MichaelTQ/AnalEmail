"""项目配置加载与校验。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(ValueError):
    """配置缺失或格式错误。"""


@dataclass(frozen=True)
class Config:
    email_address: str
    email_auth_code: str
    imap_host: str
    imap_port: int
    email_limit: int
    ollama_base_url: str
    ollama_model: str


def _read_positive_int(name: str) -> int:
    value = os.getenv(name, "").strip()
    try:
        number = int(value)
    except ValueError as exc:
        raise ConfigError(f"配置项 {name} 必须是整数。") from exc

    if number <= 0:
        raise ConfigError(f"配置项 {name} 必须大于 0。")
    return number


def load_config(env_path: Path | None = None) -> Config:
    """从项目目录中的 .env 加载并校验配置。"""
    path = env_path or Path(__file__).resolve().parent / ".env"
    if not path.is_file():
        raise ConfigError(
            f"未找到配置文件：{path}\n"
            "请先执行 `cp .env.example .env`，再填写 163 邮箱地址和客户端授权码。"
        )

    load_dotenv(dotenv_path=path, override=False)

    required_names = (
        "EMAIL_ADDRESS",
        "EMAIL_AUTH_CODE",
        "IMAP_HOST",
        "IMAP_PORT",
        "EMAIL_LIMIT",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
    )
    missing = [name for name in required_names if not os.getenv(name, "").strip()]
    if missing:
        raise ConfigError(
            "以下必需配置缺失或为空："
            + ", ".join(missing)
            + "。请检查 .env 文件。"
        )

    imap_port = _read_positive_int("IMAP_PORT")
    if imap_port > 65535:
        raise ConfigError("配置项 IMAP_PORT 必须在 1 到 65535 之间。")

    email_limit = _read_positive_int("EMAIL_LIMIT")

    return Config(
        email_address=os.environ["EMAIL_ADDRESS"].strip(),
        email_auth_code=os.environ["EMAIL_AUTH_CODE"].strip(),
        imap_host=os.environ["IMAP_HOST"].strip(),
        imap_port=imap_port,
        email_limit=email_limit,
        ollama_base_url=os.environ["OLLAMA_BASE_URL"].strip().rstrip("/"),
        ollama_model=os.environ["OLLAMA_MODEL"].strip(),
    )
