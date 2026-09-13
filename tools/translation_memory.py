from __future__ import annotations
import hashlib
import json
from pathlib import Path


def load_translation_memory(localization_dir: Path) -> dict:
    localization_dir = Path(localization_dir)
    merged: dict = {}
    files = [localization_dir / "translation-memory.json"]
    reviewed_dir = localization_dir / "reviewed"
    if reviewed_dir.exists():
        files.extend(sorted(reviewed_dir.glob("*.json")))
    for path in files:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for source, item in data.items():
            incoming = dict(item)
            current = merged.get(source)
            if current and current.get("state") == "reviewed" and incoming.get("state") == "reviewed":
                if current.get("translation") != incoming.get("translation"):
                    raise RuntimeError(f"Conflicting reviewed translation for: {source}")
                continue
            if current and current.get("state") == "reviewed" and incoming.get("state") != "reviewed":
                continue
            merged[source] = incoming
    return merged


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def merge_machine_translations(memory: dict, additions: dict[str, str]) -> dict:
    merged = {k: dict(v) for k, v in memory.items()}
    for source, translation in additions.items():
        current = merged.get(source)
        if current and current.get("state") == "reviewed":
            continue
        merged[source] = {
            "translation": translation,
            "state": "machine",
            "source_hash": source_hash(source),
        }
    return merged


def stale_reviewed_entries(memory: dict) -> list[str]:
    stale: list[str] = []
    for source, item in memory.items():
        if item.get("state") != "reviewed":
            continue
        stored = item.get("source_hash")
        if stored and stored != source_hash(source):
            stale.append(source)
    return sorted(stale)
