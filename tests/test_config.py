from __future__ import annotations

import textwrap
from datetime import datetime
from pathlib import Path

import pytest
import zoneinfo

from src.config import Category, Config, DeliveryConfig, Feed, get_active_categories, load_config

VALID_YAML = textwrap.dedent("""\
    delivery:
      time: "06:00"
      timezone: "Europe/Warsaw"

    categories:
      world_politics:
        display_name: "World Politics"
        frequency: daily
        context_hint: "politics"
        feeds:
          - url: https://feeds.bbci.co.uk/news/world/rss.xml
            name: BBC World

      rock_metal:
        display_name: "Rock & Metal"
        frequency: weekly
        day: friday
        feeds:
          - url: https://www.loudwire.com/feed/
            name: Loudwire
""")


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(VALID_YAML, encoding="utf-8")
    return p


def test_load_valid_config(config_file: Path) -> None:
    cfg = load_config(config_file)
    assert isinstance(cfg, Config)
    assert cfg.delivery.timezone == "Europe/Warsaw"
    assert cfg.delivery.time == "06:00"
    assert len(cfg.categories) == 2


def test_load_config_category_fields(config_file: Path) -> None:
    cfg = load_config(config_file)
    politics = next(c for c in cfg.categories if c.key == "world_politics")
    assert politics.display_name == "World Politics"
    assert politics.frequency == "daily"
    assert politics.context_hint == "politics"
    assert len(politics.feeds) == 1
    assert politics.feeds[0].url == "https://feeds.bbci.co.uk/news/world/rss.xml"
    assert politics.feeds[0].name == "BBC World"


def test_load_config_weekly_category(config_file: Path) -> None:
    cfg = load_config(config_file)
    rock = next(c for c in cfg.categories if c.key == "rock_metal")
    assert rock.frequency == "weekly"
    assert rock.day == "friday"


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(tmp_path / "nonexistent.yaml")


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "config.yaml"
    bad.write_text("key: [unclosed bracket\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(bad)


def _make_config(extra_categories: list[Category] | None = None) -> Config:
    cats = [
        Category(key="politics", display_name="Politics", frequency="daily", feeds=[]),
        Category(
            key="rock",
            display_name="Rock",
            frequency="weekly",
            feeds=[],
            day="friday",
        ),
    ]
    if extra_categories:
        cats.extend(extra_categories)
    return Config(
        delivery=DeliveryConfig(time="06:00", timezone="Europe/Warsaw"),
        categories=cats,
    )


def test_active_categories_daily_always_included() -> None:
    cfg = _make_config()
    tz = zoneinfo.ZoneInfo("Europe/Warsaw")
    monday = datetime(2026, 5, 18, 6, 0, tzinfo=tz)  # Monday
    active = get_active_categories(cfg, now=monday)
    keys = [c.key for c in active]
    assert "politics" in keys
    assert "rock" not in keys


def test_active_categories_weekly_on_matching_day() -> None:
    cfg = _make_config()
    tz = zoneinfo.ZoneInfo("Europe/Warsaw")
    friday = datetime(2026, 5, 15, 6, 0, tzinfo=tz)  # Friday
    active = get_active_categories(cfg, now=friday)
    keys = [c.key for c in active]
    assert "politics" in keys
    assert "rock" in keys


def test_active_categories_weekly_default_day() -> None:
    cfg = Config(
        delivery=DeliveryConfig(time="06:00", timezone="Europe/Warsaw"),
        categories=[
            Category(
                key="books",
                display_name="Books",
                frequency="weekly",
                feeds=[],
                # no day specified — should default to friday
            )
        ],
    )
    tz = zoneinfo.ZoneInfo("Europe/Warsaw")
    friday = datetime(2026, 5, 15, 6, 0, tzinfo=tz)
    active = get_active_categories(cfg, now=friday)
    assert any(c.key == "books" for c in active)


def test_active_categories_timezone_matters() -> None:
    """A run at 02:00 UTC on Saturday is still Friday in New York (EDT = UTC-4 in May)."""
    cfg = Config(
        delivery=DeliveryConfig(time="06:00", timezone="America/New_York"),
        categories=[
            Category(key="rock", display_name="Rock", frequency="weekly", feeds=[], day="friday"),
        ],
    )
    tz = zoneinfo.ZoneInfo("UTC")
    saturday_utc = datetime(2026, 5, 16, 2, 0, tzinfo=tz)  # Sat 02:00 UTC = Fri 22:00 EDT
    active = get_active_categories(cfg, now=saturday_utc)
    keys = [c.key for c in active]
    assert "rock" in keys
