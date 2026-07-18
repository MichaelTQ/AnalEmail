"""163 邮箱 AI 助手命令行入口。"""

from __future__ import annotations

import json
import sys
from typing import Any

from ai_analyzer import AIAnalyzerError, analyze_email
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


def _print_analysis(analysis: dict[str, Any]) -> None:
    print("最新邮件 AI 分析：")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
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
    first_parsed: dict[str, Any] | None = None

    if not messages:
        print("INBOX 中没有可读取的邮件。")

    for index, message in enumerate(messages, start=1):
        try:
            parsed = parse_email(message)
            _print_email(index, parsed)
            #分析第三封邮件
            if index == 3:
                first_parsed = parsed

            '''
            if first_parsed is None:#分析第一封邮件
                first_parsed = parsed'''
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

    print(f"邮件解析完成：成功 {success_count} 封，失败 {failure_count} 封。")

    if first_parsed is not None:
        try:
            analysis = analyze_email(first_parsed, config)
            _print_analysis(analysis)
        except AIAnalyzerError as exc:
            print(f"AI 分析失败：{exc}", file=sys.stderr)
            return 3

    return 0 if failure_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
