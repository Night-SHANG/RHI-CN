from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_state(state_path: Path, inventory_path: Path, *, validated_main: str | None = None,
                 observed_release: str | None = None, published_release: str | None = None,
                 inventory_main: str | None = None) -> None:
    state = _read(state_path, {"upstream": "RankFTW/RHI", "validated_main_commit": None,
        "observed_release_tag": None, "published_release_tag": None})
    if validated_main is not None:
        state["validated_main_commit"] = validated_main
    if observed_release is not None:
        state["observed_release_tag"] = observed_release
    if published_release is not None:
        state["published_release_tag"] = published_release
    _write(state_path, state)
    if inventory_main is not None:
        inventory = _read(inventory_path, {"upstream_commit": None, "unhandled_csharp": [], "manifest_visible_text": []})
        inventory["upstream_commit"] = inventory_main
        _write(inventory_path, inventory)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", type=Path, default=Path("upstream.json"))
    ap.add_argument("--inventory", type=Path, default=Path("Localization/inventory/main.json"))
    ap.add_argument("--validated-main")
    ap.add_argument("--observed-release")
    ap.add_argument("--published-release")
    ap.add_argument("--inventory-main")
    args = ap.parse_args()
    update_state(args.state, args.inventory, validated_main=args.validated_main,
                 observed_release=args.observed_release, published_release=args.published_release,
                 inventory_main=args.inventory_main)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
