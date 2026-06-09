from __future__ import annotations

import re
from typing import Tuple

from app.config import get_settings

settings = get_settings()

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'()]+|www\.[^\s<>\"'()]+", re.IGNORECASE
)


def count_links(content: str) -> int:
    return len(URL_PATTERN.findall(content))


def check_keywords(content: str) -> Tuple[bool, list]:
    content_lower = content.lower()
    found = [kw for kw in settings.spam_keywords_set if kw in content_lower]
    return len(found) > 0, found


def calculate_spam_score(content: str, ip_address: str = "") -> Tuple[int, list]:
    score = 0
    reasons = []

    has_keywords, keywords = check_keywords(content)
    if has_keywords:
        score += len(keywords) * 10
        reasons.append(f"spam_keywords:{','.join(keywords)}")

    link_count = count_links(content)
    if link_count > settings.comment_max_links:
        score += (link_count - settings.comment_max_links) * 5
        reasons.append(f"too_many_links:{link_count}")

    if len(content) < 5:
        score += 5
        reasons.append("too_short")

    return score, reasons


def is_suspicious(content: str, ip_address: str = "") -> Tuple[bool, str]:
    score, reasons = calculate_spam_score(content, ip_address)
    if score >= 10:
        return True, ";".join(reasons)
    return False, ""
