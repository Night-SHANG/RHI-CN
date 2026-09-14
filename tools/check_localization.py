from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.console import print_json
from tools.resw import read_resw
from tools.translation_memory import stale_reviewed_entries, load_translation_memory


def _sig(item: dict) -> tuple:
    return (item.get("file"), item.get("text"), item.get("kind"))


def evaluate_report(
    en: dict[str, str],
    zh: dict[str, str],
    fallback_keys: list[str],
    unhandled: list[dict],
    baseline_unhandled: list[dict],
    stale_reviewed: list[str],
) -> dict:
    en_keys = set(en)
    zh_keys = set(zh)
    baseline = {_sig(x) for x in baseline_unhandled}
    translated = len(en_keys - set(fallback_keys))
    return {
        "english_keys": len(en_keys),
        "chinese_keys": len(zh_keys),
        "missing_zh_keys": sorted(en_keys - zh_keys),
        "unused_zh_keys": sorted(zh_keys - en_keys),
        "fallback_keys": sorted(fallback_keys),
        "coverage_percent": round(translated / len(en_keys) * 100.0, 2) if en_keys else 0.0,
        "new_unhandled_csharp": [x for x in unhandled if _sig(x) not in baseline],
        "stale_reviewed_sources": stale_reviewed,
    }


def should_fail(result: dict, strict: bool, no_fallback: bool = False) -> bool:
    fatal = bool(result["missing_zh_keys"] or result["stale_reviewed_sources"])
    if strict and result["new_unhandled_csharp"]:
        fatal = True
    if no_fallback and result.get("fallback_keys"):
        fatal = True
    return fatal


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--strict", action="store_true")
    ap.add_argument(
        "--no-fallback",
        action="store_true",
        help="Fail if any generated zh-CN resource still falls back to English.",
    )
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args()

    en = read_resw(args.source / "RenoDXCommander" / "Strings" / "en-US" / "Resources.resw")
    zh = read_resw(args.source / "RenoDXCommander" / "Strings" / "zh-CN" / "Resources.resw")
    report_path = args.repo / "reports" / "localization-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    inventory_path = args.repo / "Localization" / "inventory" / "main.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8")) if inventory_path.exists() else {}
    memory = load_translation_memory(args.repo / "Localization")

    unhandled = report.get("unhandled_csharp", [])
    manifest_visible = report.get("manifest_visible_text", [])
    if args.update_baseline:
        inventory = {
            "upstream_commit": inventory.get("upstream_commit"),
            "unhandled_csharp": unhandled,
            "manifest_visible_text": manifest_visible,
        }
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = evaluate_report(
        en,
        zh,
        report.get("fallback_keys", []),
        unhandled,
        inventory.get("unhandled_csharp", []),
        stale_reviewed_entries(memory),
    )
    result["fallback_sources"] = {
        key: en.get(key, "") for key in result["fallback_keys"]
    }
    baseline_manifest = set(inventory.get("manifest_visible_text", []))
    result["new_manifest_visible_text"] = [x for x in manifest_visible if x not in baseline_manifest]
    out_path = args.repo / "reports" / "check-report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_json(result)
    return 1 if should_fail(result, args.strict, args.no_fallback) else 0

if __name__ == "__main__":
    raise SystemExit(main())
