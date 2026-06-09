from __future__ import annotations

import pytest

from app.services.antispam import (
    calculate_spam_score,
    check_keywords,
    count_links,
    is_suspicious,
)


def test_count_links_no_links():
    assert count_links("Just some text without links") == 0


def test_count_links_with_links():
    content = "Check out https://example.com and http://test.org/path"
    assert count_links(content) == 2


def test_count_links_with_www():
    content = "Visit www.example.com for more info"
    assert count_links(content) == 1


def test_check_keywords_clean():
    is_spam, found = check_keywords("This is a normal comment about Python")
    assert not is_spam
    assert len(found) == 0


def test_check_keywords_spam():
    is_spam, found = check_keywords("This contains spam and 广告 content")
    assert is_spam
    assert "spam" in found
    assert "广告" in found


def test_calculate_spam_score_clean():
    score, reasons = calculate_spam_score("A normal comment with no issues")
    assert score == 0
    assert len(reasons) == 0


def test_calculate_spam_score_with_keywords():
    score, reasons = calculate_spam_score("This is spam and 垃圾 content")
    assert score > 0
    assert any("spam_keywords" in r for r in reasons)


def test_calculate_spam_score_too_many_links():
    content = "Check https://a.com, https://b.com, https://c.com, https://d.com, https://e.com"
    score, reasons = calculate_spam_score(content)
    assert score > 0
    assert any("too_many_links" in r for r in reasons)


def test_is_suspicious_clean():
    suspicious, reason = is_suspicious("A perfectly normal comment")
    assert not suspicious
    assert reason == ""


def test_is_suspicious_spammy():
    suspicious, reason = is_suspicious(
        "spam spam spam 广告 推广 赌博 https://a.com https://b.com https://c.com https://d.com"
    )
    assert suspicious
    assert reason != ""


def test_spam_keywords_case_insensitive():
    is_spam, found = check_keywords("SPAM and SpAm everywhere")
    assert is_spam
    assert "spam" in found
