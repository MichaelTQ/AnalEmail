"""使用 Python 标准库 email 解析邮件内容。"""

from __future__ import annotations

import re
from datetime import datetime
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup


def decode_mime_header(value: str | None) -> str:
    """解码 RFC 2047 标题，容忍未知或错误字符集。"""
    if not value:
        return ""

    decoded_parts: list[str] = []
    try:
        parts = decode_header(value)
    except (ValueError, TypeError):
        return str(value).strip()

    for part, charset in parts:
        if isinstance(part, str):
            decoded_parts.append(part)
            continue

        decoded_parts.append(_decode_bytes(part, charset))

    return "".join(decoded_parts).strip()


def _decode_bytes(data: bytes, declared_charset: str | None = None) -> str:
    """按声明字符集及常见中英文字符集依次解码。"""
    charsets = [declared_charset, "utf-8", "gb18030", "gbk", "big5", "latin-1"]
    tried: set[str] = set()

    for charset in charsets:
        if not charset:
            continue
        normalized = charset.lower().strip()
        if normalized in tried:
            continue
        tried.add(normalized)
        try:
            return data.decode(normalized)
        except (LookupError, UnicodeDecodeError):
            continue

    return data.decode("utf-8", errors="replace")


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw_payload = part.get_payload()
        return raw_payload if isinstance(raw_payload, str) else ""
    return _decode_bytes(payload, part.get_content_charset())


def _is_attachment(part: Message) -> bool:
    disposition = (part.get_content_disposition() or "").lower()
    return disposition == "attachment" or bool(part.get_filename())


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text).strip()


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    return _clean_text(soup.get_text(separator="\n"))


def extract_body(message: Message) -> str:
    """优先提取 text/plain，不存在时将 text/html 转成纯文本。"""
    plain_parts: list[str] = []
    html_parts: list[str] = []

    parts = message.walk() if message.is_multipart() else (message,)
    for part in parts:
        if part.is_multipart() or _is_attachment(part):
            continue

        content_type = part.get_content_type().lower()
        if content_type == "text/plain":
            text = _clean_text(_decode_part(part))
            if text:
                plain_parts.append(text)
        elif content_type == "text/html":
            text = _html_to_text(_decode_part(part))
            if text:
                html_parts.append(text)

    selected = plain_parts if plain_parts else html_parts
    return _clean_text("\n\n".join(selected)) if selected else ""


def _parse_sender(value: str | None) -> str:
    decoded = decode_mime_header(value)
    if not decoded:
        return "(无发件人)"
    name, address = parseaddr(decoded)
    if name and address:
        # formataddr 会把中文姓名重新编码成 RFC 2047，终端展示应保留可读文本。
        return f"{name} <{address}>"
    return address or name or decoded


def _parse_date(value: str | None) -> str:
    if not value:
        return "(未知时间)"
    try:
        parsed = parsedate_to_datetime(value)
        if not isinstance(parsed, datetime):
            return "(未知时间)"
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone()
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OverflowError):
        return "(未知时间)"


def parse_email(mail: Any) -> dict[str, Any]:
    """将 imap-tools MailMessage 转换为统一字典。"""
    message = getattr(mail, "obj", mail)
    if not isinstance(message, Message):
        raise TypeError("收到无法识别的邮件对象。")

    uid = str(getattr(mail, "uid", "") or message.get("X-UID", "") or "(未知 UID)")
    subject = decode_mime_header(message.get("Subject")) or "(无标题)"

    return {
        "uid": uid,
        "sender": _parse_sender(message.get("From")),
        "subject": subject,
        "date": _parse_date(message.get("Date")),
        "body": extract_body(message),
        "has_attachment": any(_is_attachment(part) for part in message.walk()),
    }
