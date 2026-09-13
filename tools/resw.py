from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET


def read_resw(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    root = ET.parse(path).getroot()
    out: dict[str, str] = {}
    for data in root.findall("data"):
        name = data.attrib.get("name")
        value = data.find("value")
        if name and value is not None:
            out[name] = value.text or ""
    return out


def write_resw(path: Path, entries: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("root")
    for key in sorted(entries):
        data = ET.SubElement(root, "data", {"name": key, "{http://www.w3.org/XML/1998/namespace}space": "preserve"})
        value = ET.SubElement(data, "value")
        value.text = entries[key]
    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _normalized_memory(memory: dict[str, dict]) -> dict[str, dict]:
    normalized: dict[str, dict] = {}
    ambiguous: set[str] = set()
    for source, item in memory.items():
        key = _normalize_line_endings(source)
        if key in ambiguous:
            continue
        existing = normalized.get(key)
        if existing is None:
            normalized[key] = item
            continue
        existing_translation = str(existing.get("translation", "")).strip()
        incoming_translation = str(item.get("translation", "")).strip()
        if existing_translation != incoming_translation:
            normalized.pop(key, None)
            ambiguous.add(key)
    return normalized


def materialize_zh(
    english: dict[str, str],
    exact_zh: dict[str, str],
    memory: dict[str, dict],
) -> tuple[dict[str, str], list[str]]:
    zh: dict[str, str] = {}
    fallback: list[str] = []
    normalized_memory = _normalized_memory(memory)
    for key, source in english.items():
        if key in exact_zh and exact_zh[key].strip():
            zh[key] = exact_zh[key]
            continue
        item = memory.get(source) or normalized_memory.get(_normalize_line_endings(source)) or {}
        translation = str(item.get("translation", "")).strip()
        if translation:
            zh[key] = translation
        else:
            zh[key] = source
            fallback.append(key)
    return zh, fallback
