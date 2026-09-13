# Contributing

Keep changes inside the localization/synchronization scope. Do not modify unrelated RHI feature behavior in the RHI-CN overlay.

For translation corrections, prefer editing `Localization/translation-memory.json` and set the entry to `"state": "reviewed"`. Keep terminology consistent with `Localization/glossary.json`.

Before submitting a change, run:

```bash
python -m pytest -q
python tools/materialize.py --source <RHI-source-path> --repo .
python tools/check_localization.py --source <RHI-source-path> --repo . --strict
```

Changes to scanners, materialization, installer patching, or release automation should include a regression test. Any transformation that cannot be proven safe should report the string and leave upstream code untouched rather than applying a heuristic rewrite.
