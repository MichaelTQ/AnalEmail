"""163 邮箱 AI 助手第一阶段入口。"""

from __future__ import annotations

import sys
from typing import Any

from config import ConfigError, load_config
from email_client import EmailClientError, fetch_recent_emails
from email_parser import parse_email


SEPARATOR = "=" * 60


def _print_email(index: int, email_data: dict[str, Any]) -> None:
    print(SEPARATOR)
    print(f"邮件 {index}")
    print(f"UID: {email_data['uid']}")
    print(f"发件人: {email_data['sender']}")
    print(f"标题: {email_data['subject']}")
    print(f"时间: {email_data['date']}")
    print(f"是否有附件: {'是' if email_data['has_attachment'] else '否'}")
    print("正文预览:")

    body = email_data["body"]
    if body:
        print(body[:500])
    else:
        print("(正文为空)")
        print("[提示] 此邮件没有可读取的纯文本或 HTML 正文。")
    print(SEPARATOR)


def main() -> int:
    try:
        config = load_config()
        messages = fetch_recent_emails(config)
    except (ConfigError, EmailClientError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    success_count = 0
    failure_count = 0

    if not messages:
        print("INBOX 中没有可读取的邮件。")

    for index, message in enumerate(messages, start=1):
        try:
            parsed = parse_email(message)
            _print_email(index, parsed)
            success_count += 1
        except Exception as exc:
            failure_count += 1
            uid = str(getattr(message, "uid", "") or "未知 UID")
            print(SEPARATOR, file=sys.stderr)
            print(
                f"邮件 {index}（UID: {uid}）解析失败："
                f"{type(exc).__name__}。可能是邮件结构或编码异常，已继续处理下一封。",
                file=sys.stderr,
            )
            print(SEPARATOR, file=sys.stderr)

    print(f"处理完成：成功 {success_count} 封，失败 {failure_count} 封。")
    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
