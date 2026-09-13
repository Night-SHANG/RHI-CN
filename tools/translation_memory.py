from __future__ import annotations
import hashlib


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
