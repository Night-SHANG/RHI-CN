from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.console import print_json
from tools.resw import read_resw
from tools.translation_memory import merge_machine_translations, load_translation_memory


def collect_missing_sources(
    english: dict[str, str],
    exact_zh: dict[str, str],
    memory: dict,
) -> list[str]:
    missing: set[str] = set()
    for key, source in english.items():
        if not source.strip():
            continue
        exact = exact_zh.get(key, "").strip()
        if exact and exact != source:
            continue
        item = memory.get(source)
        if item and str(item.get("translation", "")).strip():
            continue
        missing.add(source)
    return sorted(missing, key=lambda s: (s.casefold(), s))


def parse_translation_response(raw: str, allowed_sources: set[str]) -> dict[str, str]:
    raw = raw.strip()
    fence = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Translation response must be a JSON array")
    result: dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        source = row.get("source")
        translation = row.get("translation")
        if source not in allowed_sources or not isinstance(translation, str) or not translation.strip():
            continue
        result[source] = translation.strip()
    return result


def _translate_batch(
    sources: list[str],
    glossary: dict,
    api_url: str,
    api_key: str,
    model: str,
) -> dict[str, str]:
    system = (
        "Translate RHI desktop application UI text from English to Simplified Chinese. "
        "RHI manages ReShade, RenoDX, OptiScaler, DLSS and graphics mods. Preserve product names, "
        "file names, DLL names, paths, placeholders, hotkeys and technical identifiers. "
        "Return ONLY a JSON array of objects with exact fields source and translation. "
        "The source field must be copied exactly from the input. Do not omit entries."
    )
    user = json.dumps({"glossary": glossary, "strings": sources}, ensure_ascii=False)
    payload = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "RHI-CN-localization/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Translation API HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Translation API request failed: {exc}") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Translation API response is not OpenAI-compatible") from exc
    translated = parse_translation_response(content, set(sources))
    missing = [s for s in sources if s not in translated]
    if missing:
        raise RuntimeError(f"Translation API omitted {len(missing)} source strings")
    return translated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True, help="Materialized RHI source root")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch-size", type=int, default=20)
    args = ap.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    en_path = args.source / "RenoDXCommander" / "Strings" / "en-US" / "Resources.resw"
    exact_path = args.repo / "Localization" / "zh-CN" / "Resources.resw"
    memory_path = args.repo / "Localization" / "translation-memory.json"
    glossary_path = args.repo / "Localization" / "glossary.json"

    english = read_resw(en_path)
    exact = read_resw(exact_path)
    base_memory = json.loads(memory_path.read_text(encoding="utf-8")) if memory_path.exists() else {}
    memory = load_translation_memory(args.repo / "Localization")
    glossary = json.loads(glossary_path.read_text(encoding="utf-8")) if glossary_path.exists() else {}
    missing = collect_missing_sources(english, exact, memory)
    print_json({"missing_count": len(missing), "missing": missing})
    if not missing or args.dry_run:
        return 0

    api_url = os.getenv("TRANSLATION_API_URL", "").strip()
    api_key = os.getenv("TRANSLATION_API_KEY", "").strip()
    model = os.getenv("TRANSLATION_MODEL", "").strip()
    if not (api_url and api_key and model):
        print("Translation API is not configured; keeping English fallback.")
        return 0

    additions: dict[str, str] = {}
    for offset in range(0, len(missing), args.batch_size):
        batch = missing[offset : offset + args.batch_size]
        additions.update(_translate_batch(batch, glossary, api_url, api_key, model))

    merged = merge_machine_translations(base_memory, additions)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Added {len(additions)} machine translations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
