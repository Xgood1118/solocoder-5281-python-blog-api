from __future__ import annotations

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from app.config import get_settings
from app.email.templates import render_template

settings = get_settings()


async def send_email(
    to: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    if not settings.smtp_username or not settings.smtp_password:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.mail_from_name} <{settings.mail_from}>"
        msg["To"] = to
        msg["Subject"] = subject

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )
        return True
    except Exception:
        return False


async def send_confirmation_email(
    email: str,
    confirm_url: str,
    site_name: str = "",
) -> bool:
    site_name = site_name or settings.site_name
    html = render_template(
        "email/confirm_subscription.html",
        confirm_url=confirm_url,
        site_name=site_name,
    )
    text = f"请点击以下链接确认订阅：{confirm_url}"

    return await send_email(
        to=email,
        subject=f"确认订阅 {site_name}",
        html_content=html,
        text_content=text,
    )


async def send_new_article_notification(
    email: str,
    article_title: str,
    article_url: str,
    site_name: str = "",
) -> bool:
    site_name = site_name or settings.site_name
    html = render_template(
        "email/new_article.html",
        article_title=article_title,
        article_url=article_url,
        site_name=site_name,
    )
    text = f"新文章发布：{article_title}\n阅读链接：{article_url}"

    return await send_email(
        to=email,
        subject=f"[{site_name}] 新文章：{article_title}",
        html_content=html,
        text_content=text,
    )
