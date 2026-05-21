from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.synthesis import Synthesis

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
FAILED_DIGESTS_DIR = Path(__file__).parent.parent / "failed_digests"


@dataclass
class DigestStory:
    title: str
    url: str
    source_name: str
    synthesis_paragraphs: list[str]


@dataclass
class DigestSection:
    category_display_name: str
    frequency: str
    stories: list[DigestStory]


def build_subject(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    return f"News Digest — {now.day} {now.strftime('%B')} {now.year}"


def render_digest(sections: list[DigestSection], subject: str) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("digest.html.j2")
    generation_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return template.render(
        sections=sections,
        subject=subject,
        generation_time=generation_time,
    )


def _write_fallback(html: str, subject: str) -> None:
    FAILED_DIGESTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_subject = "".join(c if c.isalnum() or c in "-_ " else "_" for c in subject)[:60]
    path = FAILED_DIGESTS_DIR / f"{ts}_{safe_subject}.html"
    path.write_text(html, encoding="utf-8")
    logger.info("Digest saved to fallback file: %s", path)


def send_digest(sections: list[DigestSection]) -> None:
    if not sections:
        logger.info("No stories to send — skipping email")
        return

    subject = build_subject()
    html = render_digest(sections, subject)

    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient, msg.as_string())
        logger.info("Digest email sent to %s (subject: %s)", recipient, subject)
    except Exception as exc:
        logger.error("SMTP send failed: %s — writing fallback file", exc)
        _write_fallback(html, subject)


def syntheses_to_sections(
    category_results: list[tuple[str, str, list[Synthesis]]],
) -> list[DigestSection]:
    """Convert (category_key, display_name, frequency, syntheses) tuples to DigestSection list."""
    sections: list[DigestSection] = []
    for display_name, frequency, syntheses in category_results:
        if not syntheses:
            continue
        stories = [
            DigestStory(
                title=s.article.title,
                url=s.article.url,
                source_name=s.article.source_name,
                synthesis_paragraphs=[p.strip() for p in s.text.split("\n\n") if p.strip()],
            )
            for s in syntheses
        ]
        sections.append(
            DigestSection(
                category_display_name=display_name,
                frequency=frequency,
                stories=stories,
            )
        )
    return sections
