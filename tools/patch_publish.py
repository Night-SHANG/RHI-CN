from __future__ import annotations
import argparse
import re
from pathlib import Path


def patch_publish_text(text: str, output_dir: str) -> str:
    if "PublishSingleFile=true" not in text or "dotnet publish" not in text:
        raise RuntimeError("Upstream publish.bat contract changed")
    matches = re.findall(r'(?im)^set\s+OUT=.*$', text)
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one OUT assignment, found {len(matches)}")
    return re.sub(r'(?im)^set\s+OUT=.*$', lambda _m: f"set OUT={output_dir}", text, count=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("output")
    args = ap.parse_args()
    text = args.path.read_text(encoding="utf-8")
    args.path.write_text(patch_publish_text(text, args.output), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
