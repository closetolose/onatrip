"""Schedule step helpers for day content overrides."""

from __future__ import annotations

STEP_FIELDS = ("time", "place", "action", "next", "transit", "note")
META_FIELDS = ("totals",)


def normalize_step(step: dict) -> dict | None:
    if not isinstance(step, dict):
        return None
    cleaned: dict[str, str] = {}
    for field in STEP_FIELDS:
        value = (step.get(field) or "").strip()
        if value == "—":
            value = ""
        cleaned[field] = value
    if not cleaned["time"] and not cleaned["place"] and not cleaned["action"]:
        return None
    return cleaned


def clean_steps(steps: list) -> list[dict]:
    result: list[dict] = []
    for step in steps or []:
        cleaned = normalize_step(step)
        if cleaned:
            result.append(cleaned)
    return result


def clean_meta(meta: dict) -> dict:
    if not isinstance(meta, dict):
        return {}
    return {
        key: (meta.get(key) or "").strip()
        for key in META_FIELDS
    }


def steps_for_api(steps: list[dict]) -> list[dict]:
    return clean_steps(steps)


def resolve_steps(raw_steps: list[dict], media_entry: dict) -> list[dict]:
    if "steps" in media_entry:
        return media_entry["steps"]
    return raw_steps


def resolve_meta(raw_day: dict, media_entry: dict) -> dict[str, str]:
    override = media_entry.get("meta") or {}
    return {
        key: override[key] if key in override else (raw_day.get(key) or "")
        for key in META_FIELDS
    }
