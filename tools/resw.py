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


def materialize_zh(
    english: dict[str, str],
    exact_zh: dict[str, str],
    memory: dict[str, dict],
) -> tuple[dict[str, str], list[str]]:
    zh: dict[str, str] = {}
    fallback: list[str] = []
    for key, source in english.items():
        if key in exact_zh and exact_zh[key].strip():
            zh[key] = exact_zh[key]
            continue
        item = memory.get(source) or {}
        translation = str(item.get("translation", "")).strip()
        if translation:
            zh[key] = translation
        else:
            zh[key] = source
            fallback.append(key)
    return zh, fallback
