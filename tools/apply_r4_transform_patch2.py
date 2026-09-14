from pathlib import Path

p = Path("tools/transform.py")
s = p.read_text(encoding="utf-8")

old = '''        if tag.startswith("/") or tag in {"Run", "Window"}:\n            return m.group(0)\n        found: list[tuple[str, str]] = []'''
new = '''        if tag.startswith("/") or tag in {"Run", "Window"}:\n            return m.group(0)\n        combo_template_added = False\n        if tag == "ComboBox" and not re.search(r'\\bItemTemplate\\s*=', attrs):\n            attrs += ' ItemTemplate="{StaticResource LocalizedComboBoxItemTemplate}"'\n            combo_template_added = True\n        found: list[tuple[str, str]] = []'''
if old not in s:
    raise SystemExit("xaml tag anchor not found")
s = s.replace(old, new, 1)

old = '''        if not found:\n            return m.group(0)'''
new = '''        if not found:\n            return f'<{tag}{attrs}{close}>' if combo_template_added else m.group(0)'''
if old not in s:
    raise SystemExit("xaml empty-found anchor not found")
s = s.replace(old, new, 1)

anchor = '''def _transform_interpolated_ui(text: str, relpath: str) -> tuple[str, dict[str, str]]:\n'''
insert = '''def _is_probably_text_expression(expr: str) -> bool:\n    expr = expr.strip()\n    if not re.fullmatch(r'(?:[A-Za-z_]\\w*\\.)*[A-Za-z_]\\w*', expr):\n        return False\n    tail = expr.rsplit('.', 1)[-1].lower()\n    exact = {"text", "label", "title", "name", "content", "message", "description", "tip", "tooltip", "status"}\n    return tail in exact or tail.endswith(("text", "label", "title", "name", "content", "message", "description", "tip", "tooltip", "status"))\n\n\n'''
if anchor not in s:
    raise SystemExit("interpolated helper anchor not found")
s = s.replace(anchor, insert + anchor, 1)

old = '''        fmt, args, has_english = _split_interpolated_body(body)\n        if not has_english or not args:\n            continue'''
new = '''        fmt, args, has_english = _split_interpolated_body(body)\n        if not args:\n            continue\n        if not has_english and not any(_is_probably_text_expression(expr) for expr in args):\n            continue'''
if old not in s:
    raise SystemExit("interpolated condition anchor not found")
s = s.replace(old, new, 1)

# Keep scan_csharp_unhandled aligned with the transform logic.
old = '''        fmt, args, has_english = _split_interpolated_body(body)\n        if has_english and args:\n            findings.append({"file": relpath, "text": body, "format": fmt, "kind": "interpolated"})'''
new = '''        fmt, args, has_english = _split_interpolated_body(body)\n        if args and (has_english or any(_is_probably_text_expression(expr) for expr in args)):\n            findings.append({"file": relpath, "text": body, "format": fmt, "kind": "interpolated"})'''
if old not in s:
    raise SystemExit("scan condition anchor not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("patched tools/transform.py (round 2)")
