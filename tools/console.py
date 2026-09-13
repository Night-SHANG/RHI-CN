from __future__ import annotations
import json


def dumps_for_console(data) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2)


def print_json(data) -> None:
    print(dumps_for_console(data))
