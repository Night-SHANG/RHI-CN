from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.resw import read_resw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--report", default=Path("reports/localization-report.json"), type=Path)
    args = ap.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    english = read_resw(args.project / "Strings" / "en-US" / "Resources.resw")
    rows = []
    for key in report.get("fallback_keys", []):
        rows.append({"key": key, "source": english.get(key, "<missing>")})
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
