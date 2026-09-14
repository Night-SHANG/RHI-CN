from pathlib import Path

p = Path("tools/transform.py")
s = p.read_text(encoding="utf-8")

old = '''UI_FILE_PATTERNS = (\n    "MainWindow", "DetailPanelBuilder", "CompactViewBuilder", "AddonManagerDialog",\n    "AddonPopupHelper", "SettingsHandler", "InstallEventHandler", "SetupWindow",\n    "Dialog", "UIFactory",\n)'''
new = '''UI_FILE_PATTERNS = (\n    "MainWindow", "DetailPanelBuilder", "CompactViewBuilder", "AddonManagerDialog",\n    "AddonPopupHelper", "SettingsHandler", "InstallEventHandler", "SetupWindow",\n    "Dialog", "UIFactory", "UpdateInclusionHelper",\n)'''
if old not in s:
    raise SystemExit("UI_FILE_PATTERNS anchor not found")
s = s.replace(old, new, 1)

anchor = '''def _inject_combobox_item_template(text: str) -> str:\n'''
insert = r'''def _localize_literal_expr(relpath: str, prop: str, raw: str, kind: str, entries: dict[str, str]) -> str:
    value = _decode_csharp_string(raw)
    if not value.strip() or not any(ch.isalpha() for ch in value):
        return f'"{raw}"'
    key = _cs_key(relpath, value, kind)
    entries[key] = value
    fallback = _encode_csharp_string(value)
    return f'RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'


def _transform_concatenated_properties(
    text: str, relpath: str, prop_alt: str
) -> tuple[str, dict[str, str]]:
    """Collapse adjacent literal-only UI text concatenations into one resource."""
    entries: dict[str, str] = {}
    literal = r'"(?:[^"\\]|\\.)*"'
    pattern = re.compile(
        rf'\b(?P<prop>{prop_alt})\s*=\s*(?P<expr>{literal}(?:\s*\+\s*{literal})+)',
        re.S,
    )

    def sub(m: re.Match) -> str:
        prop = m.group("prop")
        literals = re.findall(literal, m.group("expr"), re.S)
        value = "".join(_decode_csharp_string(item[1:-1]) for item in literals)
        if not value.strip() or not any(ch.isalpha() for ch in value):
            return m.group(0)
        key = _cs_key(relpath, value, f"{prop}:concat")
        entries[key] = value
        fallback = _encode_csharp_string(value)
        return f'{prop} = RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'

    return pattern.sub(sub, text), entries


def _transform_ternary_properties(
    text: str, relpath: str, prop_alt: str
) -> tuple[str, dict[str, str]]:
    """Localize literal branches of simple ternary UI property expressions."""
    entries: dict[str, str] = {}
    literal = r'"(?P<{name}>(?:[^"\\]|\\.)*)"'
    yes_lit = literal.format(name="yes")
    no_lit = literal.format(name="no")
    pattern = re.compile(
        rf'\b(?P<prop>{prop_alt})\s*=\s*(?P<cond>[^?;\n]+?)\?\s*{yes_lit}\s*:\s*{no_lit}'
    )

    def sub(m: re.Match) -> str:
        prop = m.group("prop")
        yes = _localize_literal_expr(relpath, prop, m.group("yes"), f"{prop}:ternary:yes", entries)
        no = _localize_literal_expr(relpath, prop, m.group("no"), f"{prop}:ternary:no", entries)
        return f'{prop} = {m.group("cond").strip()} ? {yes} : {no}'

    return pattern.sub(sub, text), entries


def _transform_dynamic_text_properties(text: str) -> str:
    """Localize display-only string values while preserving the underlying data value."""
    pattern = re.compile(
        r'\bText\s*=\s*(?P<expr>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)'
    )

    def sub(m: re.Match) -> str:
        expr = m.group("expr")
        if expr.startswith("RenoDXCommander.Services.LocalizationService"):
            return m.group(0)
        return (
            "Text = RenoDXCommander.Services.LocalizationService.GetDataString("
            + expr + ")"
        )

    return pattern.sub(sub, text)


'''
if anchor not in s:
    raise SystemExit("combobox helper anchor not found")
s = s.replace(anchor, insert + anchor, 1)

old = '''        rendered_args = ', '.join(f'$"{{{expr}}}"' for expr in args)'''
new = '''        rendered_args = ', '.join(\n            f'RenoDXCommander.Services.LocalizationService.GetDataString($"{{{expr}}}")'\n            for expr in args\n        )'''
if old not in s:
    raise SystemExit("rendered_args anchor not found")
s = s.replace(old, new, 1)

old = '''    entries: dict[str, str] = {}\n    prop_alt = "|".join(map(re.escape, UI_ASSIGN_PROPS))\n    prop_re = re.compile(rf'\\b(?P<prop>{prop_alt})\\s*=\\s*"(?P<value>(?:[^"\\\\]|\\\\.)*)"')'''
new = '''    entries: dict[str, str] = {}\n    prop_alt = "|".join(map(re.escape, UI_ASSIGN_PROPS))\n    text, concat_entries = _transform_concatenated_properties(text, relpath, prop_alt)\n    entries.update(concat_entries)\n    text, ternary_entries = _transform_ternary_properties(text, relpath, prop_alt)\n    entries.update(ternary_entries)\n    prop_re = re.compile(rf'\\b(?P<prop>{prop_alt})\\s*=\\s*"(?P<value>(?:[^"\\\\]|\\\\.)*)"')'''
if old not in s:
    raise SystemExit("transform_csharp prop anchor not found")
s = s.replace(old, new, 1)

old = '''    entries.update(interpolated_entries)\n    text = _inject_combobox_item_template(text)\n    return text, entries'''
new = '''    entries.update(interpolated_entries)\n    text = _transform_dynamic_text_properties(text)\n    text = _inject_combobox_item_template(text)\n    return text, entries'''
if old not in s:
    raise SystemExit("transform_csharp tail anchor not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("patched tools/transform.py")
