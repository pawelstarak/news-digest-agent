from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.email_sender import (
    DigestSection,
    DigestStory,
    build_subject,
    render_digest,
    send_digest,
)


def _make_section(
    display_name: str = "World Politics",
    frequency: str = "daily",
    stories: list[DigestStory] | None = None,
) -> DigestSection:
    if stories is None:
        stories = [
            DigestStory(
                title="A Major Political Event",
                url="https://example.com/story",
                source_name="BBC World",
                synthesis_paragraphs=["Summary paragraph.", "Context paragraph.", "Implications."],
            )
        ]
    return DigestSection(
        category_display_name=display_name,
        frequency=frequency,
        stories=stories,
    )


class TestBuildSubject:
    def test_format_includes_day_month_year(self) -> None:
        dt = datetime(2026, 5, 14, 6, 0, tzinfo=timezone.utc)
        subject = build_subject(dt)
        assert subject == "News Digest — 14 May 2026"

    def test_single_digit_day(self) -> None:
        dt = datetime(2026, 3, 5, 6, 0, tzinfo=timezone.utc)
        subject = build_subject(dt)
        assert "5 March 2026" in subject

    def test_uses_current_time_when_not_provided(self) -> None:
        subject = build_subject()
        assert "News Digest —" in subject


class TestRenderDigest:
    def test_renders_category_name(self) -> None:
        sections = [_make_section("World Politics")]
        html = render_digest(sections, "News Digest — 14 May 2026")
        assert "World Politics" in html

    def test_renders_story_title_as_link(self) -> None:
        sections = [_make_section()]
        html = render_digest(sections, "News Digest — 14 May 2026")
        assert "A Major Political Event" in html
        assert "https://example.com/story" in html
        assert "<a " in html

    def test_renders_synthesis_paragraphs(self) -> None:
        sections = [_make_section()]
        html = render_digest(sections, "News Digest — 14 May 2026")
        assert "Summary paragraph." in html
        assert "Context paragraph." in html
        assert "Implications." in html

    def test_renders_source_name(self) -> None:
        sections = [_make_section()]
        html = render_digest(sections, "News Digest — 14 May 2026")
        assert "BBC World" in html

    def test_multiple_categories_all_present(self) -> None:
        sections = [
            _make_section("World Politics", "daily"),
            _make_section("Science", "daily"),
        ]
        html = render_digest(sections, "Test Subject")
        assert "World Politics" in html
        assert "Science" in html

    def test_weekly_label_shown_for_weekly_category(self) -> None:
        sections = [_make_section("Rock & Metal", "weekly")]
        html = render_digest(sections, "Test Subject")
        assert "Weekly" in html

    def test_empty_sections_renders_without_error(self) -> None:
        html = render_digest([], "News Digest — 14 May 2026")
        assert "News Digest" in html


class TestSendDigest:
    def test_skips_send_when_no_sections(self) -> None:
        with patch("src.email_sender.smtplib.SMTP_SSL") as mock_smtp:
            send_digest([])
        mock_smtp.assert_not_called()

    def test_sends_email_on_success(self) -> None:
        sections = [_make_section()]
        mock_server = MagicMock()
        env = {
            "GMAIL_USER": "test@gmail.com",
            "GMAIL_APP_PASSWORD": "apppassword",
            "RECIPIENT_EMAIL": "recipient@example.com",
        }

        with patch.dict("os.environ", env):
            with patch("src.email_sender.smtplib.SMTP_SSL") as mock_smtp_cls:
                mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
                mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
                send_digest(sections)

        mock_server.login.assert_called_once_with("test@gmail.com", "apppassword")
        mock_server.sendmail.assert_called_once()

    def test_writes_fallback_on_smtp_failure(self, tmp_path: Path) -> None:
        sections = [_make_section()]
        env = {
            "GMAIL_USER": "test@gmail.com",
            "GMAIL_APP_PASSWORD": "bad_password",
            "RECIPIENT_EMAIL": "recipient@example.com",
        }

        with patch.dict("os.environ", env):
            with patch("src.email_sender.smtplib.SMTP_SSL", side_effect=Exception("Auth failed")):
                with patch("src.email_sender.FAILED_DIGESTS_DIR", tmp_path):
                    send_digest(sections)

        saved_files = list(tmp_path.glob("*.html"))
        assert len(saved_files) == 1
        content = saved_files[0].read_text(encoding="utf-8")
        assert "A Major Political Event" in content
