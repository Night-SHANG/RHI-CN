from __future__ import annotations

VISIBLE_NOTE_FIELDS = ("notes", "notesUrlLabel")


def extract_user_visible_manifest_text(manifest: dict) -> list[str]:
    out: list[str] = []
    warnings = manifest.get("installWarnings")
    if isinstance(warnings, dict):
        for per_game in warnings.values():
            if isinstance(per_game, dict):
                for text in per_game.values():
                    if isinstance(text, str) and text.strip():
                        out.append(text)
    for container_name in ("gameNotes", "lumaGameNotes", "dxvkGameNotes", "reshadeGameInfo", "lumaGameInfo", "optiScalerGameInfo"):
        container = manifest.get(container_name)
        if not isinstance(container, dict):
            continue
        for entry in container.values():
            if isinstance(entry, dict):
                for field in VISIBLE_NOTE_FIELDS:
                    text = entry.get(field)
                    if isinstance(text, str) and text.strip():
                        out.append(text)
    return out
