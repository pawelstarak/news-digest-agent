from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
import zoneinfo


@dataclass
class Feed:
    url: str
    name: str


@dataclass
class Category:
    key: str
    display_name: str
    frequency: Literal["daily", "weekly"]
    feeds: list[Feed]
    context_hint: str = ""
    day: str = "friday"  # only relevant when frequency == "weekly"


@dataclass
class DeliveryConfig:
    time: str
    timezone: str


@dataclass
class Config:
    delivery: DeliveryConfig
    categories: list[Category]


def load_config(path: str | Path | None = None) -> Config:
    if path is None:
        path = Path(__file__).parent.parent / "config.yaml"
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping at the top level")

    delivery_raw = raw.get("delivery", {})
    delivery = DeliveryConfig(
        time=delivery_raw.get("time", "06:00"),
        timezone=delivery_raw.get("timezone", "UTC"),
    )

    categories: list[Category] = []
    for key, cat_raw in (raw.get("categories") or {}).items():
        feeds = [
            Feed(url=f["url"], name=f["name"])
            for f in (cat_raw.get("feeds") or [])
        ]
        categories.append(
            Category(
                key=key,
                display_name=cat_raw.get("display_name", key),
                frequency=cat_raw.get("frequency", "daily"),
                feeds=feeds,
                context_hint=cat_raw.get("context_hint", ""),
                day=cat_raw.get("day", "friday"),
            )
        )

    return Config(delivery=delivery, categories=categories)


def get_active_categories(config: Config, now: datetime | None = None) -> list[Category]:
    """Return categories that should be processed for the current run.

    Daily categories always run. Weekly categories only run when the current
    local day-of-week (in the configured timezone) matches their configured day.
    """
    tz = zoneinfo.ZoneInfo(config.delivery.timezone)
    if now is None:
        now = datetime.now(tz)
    else:
        now = now.astimezone(tz)

    current_day = now.strftime("%A").lower()  # e.g. "friday"

    active: list[Category] = []
    for cat in config.categories:
        if cat.frequency == "daily":
            active.append(cat)
        elif cat.frequency == "weekly":
            if current_day == cat.day.lower():
                active.append(cat)
    return active
