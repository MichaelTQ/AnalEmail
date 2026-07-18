"""163 邮箱 IMAP 只读客户端。"""

from __future__ import annotations

import imaplib
import socket
from datetime import datetime, timezone
from typing import Any

from imap_tools import MailBox
from imap_tools.errors import (
    ImapToolsError,
    MailboxFolderSelectError,
    MailboxLoginError,
)

from config import Config


class EmailClientError(RuntimeError):
    """可安全展示给用户的邮箱客户端错误。"""


def _send_client_id(mailbox: MailBox) -> None:
    """向 163 声明真实客户端信息，避免被判定为 Unsafe Login。"""
    client_info = (
        '("name" "email-ai-assistant" '
        '"version" "1.0" '
        '"vendor" "local-student-project")'
    )
    status, _ = mailbox.client.xatom("ID", client_info)
    if status != "OK":
        raise EmailClientError(
            "163 服务器未接受客户端身份信息，无法继续安全读取邮件。"
        )


def _sort_date(message: Any) -> datetime:
    """返回可比较的邮件日期；无有效日期的邮件排在最后。"""
    try:
        value = getattr(message, "date", None)
    except (TypeError, ValueError, OverflowError):
        return datetime.min.replace(tzinfo=timezone.utc)
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def fetch_recent_emails(config: Config) -> list[Any]:
    """获取最近邮件，全程不删除、不移动且不设置已读标记。"""
    mailbox: MailBox | None = None
    logged_in = False

    try:
        mailbox = MailBox(config.imap_host, port=config.imap_port)
        # 不在 login 时自动选择目录，随后显式以只读方式打开 INBOX。
        mailbox.login(
            config.email_address,
            config.email_auth_code,
            initial_folder=None,
        )
        logged_in = True
        _send_client_id(mailbox)
        mailbox.folder.set("INBOX", readonly=True)

        messages = list(
            mailbox.fetch(
                criteria="ALL",
                limit=config.email_limit,
                reverse=True,
                mark_seen=False,
                bulk=True,
            )
        )
        messages.sort(key=_sort_date, reverse=True)
        return messages
    except MailboxLoginError as exc:
        raise EmailClientError(
            "邮箱登录失败。请确认：163 邮箱已开启 IMAP/SMTP 服务；"
            "登录凭据使用的是客户端授权码而不是邮箱登录密码；邮箱地址和授权码均正确。"
        ) from exc
    except MailboxFolderSelectError as exc:
        if "Unsafe Login" in str(exc):
            raise EmailClientError(
                "163 拒绝打开收件箱，并将本次连接判定为 Unsafe Login。"
                "程序已发送客户端 ID；请重新生成授权码后重试，"
                "若仍失败请联系 163 邮箱客服确认账号风控状态。"
            ) from exc
        raise EmailClientError(
            "无法以只读方式打开 INBOX。请确认收件箱可用，并稍后重试。"
        ) from exc
    except (socket.gaierror, socket.timeout, TimeoutError, ConnectionError) as exc:
        raise EmailClientError(
            f"网络连接失败，无法连接 {config.imap_host}:{config.imap_port}。"
            "请检查网络、主机名、防火墙和代理设置。"
        ) from exc
    except OSError as exc:
        raise EmailClientError(
            f"连接 163 IMAP 服务失败（{config.imap_host}:{config.imap_port}）。"
            "请检查网络连接及 IMAP 服务是否可用。"
        ) from exc
    except imaplib.IMAP4.error as exc:
        raise EmailClientError(
            "底层 IMAP 通信失败。请确认服务器地址、端口和 163 IMAP 服务状态，"
            "然后重试。"
        ) from exc
    except ImapToolsError as exc:
        raise EmailClientError(
            "IMAP 操作失败。请确认 163 邮箱已开启 IMAP/SMTP 服务，"
            "并稍后重试。"
        ) from exc
    finally:
        if mailbox is not None and logged_in:
            try:
                mailbox.logout()
            except Exception:
                # 连接可能已经被服务器关闭；此处不能掩盖原始结果或错误。
                pass
