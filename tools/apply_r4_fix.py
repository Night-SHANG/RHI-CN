from pathlib import Path


def patch_transform() -> None:
    p = Path("tools/transform.py")
    s = p.read_text(encoding="utf-8")

    old = '''UI_FILE_PATTERNS = (
    "MainWindow", "DetailPanelBuilder", "CompactViewBuilder", "AddonManagerDialog",
    "AddonPopupHelper", "SettingsHandler", "InstallEventHandler", "SetupWindow",
    "Dialog", "UIFactory", "UpdateInclusionHelper",
)'''
    new = '''UI_FILE_PATTERNS = (
    "MainWindow", "DetailPanelBuilder", "CompactViewBuilder", "AddonManagerDialog",
    "PopupHelper", "SettingsHandler", "InstallEventHandler", "SetupWindow",
    "Dialog", "UIFactory", "UpdateInclusionHelper",
)'''
    assert old in s
    s = s.replace(old, new, 1)

    old = 'def transform_xaml(text: str, relpath: str) -> tuple[str, dict[str, str]]:\n    text = _ensure_localizer_namespace(text)\n    entries: dict[str, str] = {}'
    new = 'def transform_xaml(text: str, relpath: str, skip_combobox_item_templates: set[str] | None = None) -> tuple[str, dict[str, str]]:\n    text = _ensure_localizer_namespace(text)\n    entries: dict[str, str] = {}\n    skip_combobox_item_templates = skip_combobox_item_templates or set()'
    assert old in s
    s = s.replace(old, new, 1)

    old = '''        combo_template_added = False
        if tag == "ComboBox" and not re.search(r'\\bItemTemplate\\s*=', attrs):
            attrs += ' ItemTemplate="{StaticResource LocalizedComboBoxItemTemplate}"'
            combo_template_added = True'''
    new = '''        combo_template_added = False
        combo_name_match = re.search(r'x:Name\\s*=\\s*"([^\"]+)"', attrs)
        combo_name = combo_name_match.group(1) if combo_name_match else None
        has_display_member_path = bool(re.search(r'\\bDisplayMemberPath\\s*=', attrs))
        if (
            tag == "ComboBox"
            and not re.search(r'\\bItemTemplate\\s*=', attrs)
            and not has_display_member_path
            and combo_name not in skip_combobox_item_templates
        ):
            attrs += ' ItemTemplate="{StaticResource LocalizedComboBoxItemTemplate}"'
            combo_template_added = True'''
    assert old in s
    s = s.replace(old, new, 1)

    anchor = '''def _cs_key(relpath: str, text: str, kind: str) -> str:
    digest = hashlib.sha1(f"{relpath}|{kind}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"CS_{digest}"
'''
    addition = anchor + '''

def _data_key(text: str) -> str:
    return "Data_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _collect_runtime_display_sources(text: str) -> dict[str, str]:
    """Collect runtime-displayed strings without changing their program values."""
    sources: set[str] = set()
    literal_re = re.compile(r'"((?:[^"\\\\]|\\\\.)*)"')

    tooltip_assignment = re.compile(
        r'\\b[A-Za-z_]\\w*(?:ToolTip|Tooltip)\\w*\\s*=\\s*(?P<expr>[^;]+);', re.S
    )
    for match in tooltip_assignment.finditer(text):
        for raw in literal_re.findall(match.group("expr")):
            value = _decode_csharp_string(raw)
            if value.strip() and any(ch.isalpha() for ch in value):
                sources.add(value)

    option_block = re.compile(
        r'\\b[A-Za-z_]\\w*(?:Options|Presets)\\s*=\\s*\\[(?P<body>[\\s\\S]*?)\\];'
    )
    tuple_first = re.compile(r'\\(\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*,')
    for match in option_block.finditer(text):
        for raw in tuple_first.findall(match.group("body")):
            value = _decode_csharp_string(raw)
            if value.strip() and any(ch.isalpha() for ch in value):
                sources.add(value)

    for match in re.finditer(r'ItemsSource\\s*=\\s*new\\s*\\[\\]\\s*\\{(?P<body>[\\s\\S]*?)\\}', text):
        for raw in literal_re.findall(match.group("body")):
            value = _decode_csharp_string(raw)
            if value.strip() and any(ch.isalpha() for ch in value):
                sources.add(value)
    for raw in re.findall(r'\\.Items\\.Add\\(\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*\\)', text):
        value = _decode_csharp_string(raw)
        if value.strip() and any(ch.isalpha() for ch in value):
            sources.add(value)

    return {_data_key(source): source for source in sorted(sources)}
'''
    assert anchor in s
    s = s.replace(anchor, addition, 1)

    start = s.index("def _transform_tooltip_literals(")
    end = s.index("\ndef _localize_literal_expr", start)
    replacement = r'''def _find_tooltip_calls(text: str) -> list[tuple[int, int, str, str]]:
    """Return ToolTipService.SetToolTip call spans plus target and second argument."""
    calls: list[tuple[int, int, str, str]] = []
    needle = "ToolTipService.SetToolTip("
    pos = 0
    while True:
        start = text.find(needle, pos)
        if start < 0:
            break
        i = start + len(needle)
        depth = 1
        quote: str | None = None
        comma = -1
        while i < len(text):
            ch = text[i]
            if quote is not None:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote:
                    quote = None
                i += 1
                continue
            if ch in {'"', "'"}:
                quote = ch
                i += 1
                continue
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    break
            elif ch == ',' and depth == 1 and comma < 0:
                comma = i
            i += 1
        if depth != 0 or comma < 0:
            pos = start + len(needle)
            continue
        target = text[start + len(needle):comma].strip()
        expr = text[comma + 1:i].strip()
        calls.append((start, i + 1, target, expr))
        pos = i + 1
    return calls


def _transform_tooltips(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    entries: dict[str, str] = {}
    replacements: list[tuple[int, int, str]] = []
    literal_full = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
    literal_any = re.compile(r'"((?:[^"\\]|\\.)*)"')
    literal_token = r'"(?:[^"\\]|\\.)*"'
    literal_concat = re.compile(rf'^{literal_token}(?:\s*\+\s*{literal_token})+$', re.S)

    for start, end, target, expr in _find_tooltip_calls(text):
        if "LocalizationService." in expr or expr in {"null", "string.Empty"}:
            continue

        if literal_concat.fullmatch(expr):
            parts = literal_any.findall(expr)
            value = "".join(_decode_csharp_string(raw) for raw in parts)
            if value.strip() and any(ch.isalpha() for ch in value):
                key = _cs_key(relpath, value, "ToolTipService.SetToolTip")
                entries[key] = value
                fallback = _encode_csharp_string(value)
                localized = f'RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'
                replacements.append((start, end, f'ToolTipService.SetToolTip({target}, {localized})'))
            continue

        plain = literal_full.fullmatch(expr)
        if plain:
            value = _decode_csharp_string(plain.group(1))
            if value.strip() and any(ch.isalpha() for ch in value):
                key = _cs_key(relpath, value, "ToolTipService.SetToolTip")
                entries[key] = value
                fallback = _encode_csharp_string(value)
                localized = f'RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'
                replacements.append((start, end, f'ToolTipService.SetToolTip({target}, {localized})'))
            continue

        if expr.startswith('$"'):
            continue

        if '?' in expr and literal_any.search(expr):
            def repl_literal(m: re.Match) -> str:
                value = _decode_csharp_string(m.group(1))
                if not value.strip() or not any(ch.isalpha() for ch in value):
                    return m.group(0)
                key = _cs_key(relpath, value, "ToolTipService.SetToolTip:branch")
                entries[key] = value
                fallback = _encode_csharp_string(value)
                return f'RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'
            localized_expr = literal_any.sub(repl_literal, expr)
            replacements.append((start, end, f'ToolTipService.SetToolTip({target}, {localized_expr})'))
            continue

        if re.fullmatch(r'(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*', expr) and _is_probably_text_expression(expr):
            localized = f'RenoDXCommander.Services.LocalizationService.GetDataString({expr})'
            replacements.append((start, end, f'ToolTipService.SetToolTip({target}, {localized})'))

    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    return text, entries

'''
    s = s[:start] + replacement + s[end + 1:]

    old = '''def transform_csharp(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    if not _is_ui_file(relpath):
        return text, {}
    entries: dict[str, str] = {}'''
    new = '''def transform_csharp(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    runtime_entries = _collect_runtime_display_sources(text)
    if not _is_ui_file(relpath):
        return text, runtime_entries
    entries: dict[str, str] = dict(runtime_entries)'''
    assert old in s
    s = s.replace(old, new, 1)
    s = s.replace(
        "text, tooltip_entries = _transform_tooltip_literals(text, relpath)",
        "text, tooltip_entries = _transform_tooltips(text, relpath)",
        1,
    )

    old = '''    for start, _end, body in _find_interpolated_strings(text):
        if not _interpolated_context(text, start):
            continue
        fmt, args, has_english = _split_interpolated_body(body)
        if args and (has_english or any(_is_probably_text_expression(expr) for expr in args)):
            findings.append({"file": relpath, "text": body, "format": fmt, "kind": "interpolated"})
    return findings'''
    new = '''    for start, _end, body in _find_interpolated_strings(text):
        if not _interpolated_context(text, start):
            continue
        fmt, args, has_english = _split_interpolated_body(body)
        if args and (has_english or any(_is_probably_text_expression(expr) for expr in args)):
            findings.append({"file": relpath, "text": body, "format": fmt, "kind": "interpolated"})
    for _start, _end, _target, expr in _find_tooltip_calls(text):
        if "LocalizationService." in expr or expr in {"null", "string.Empty"}:
            continue
        if expr.startswith('$"') or re.search(r'[A-Za-z]', expr):
            findings.append({"file": relpath, "text": expr, "format": expr, "kind": "tooltip"})
    return findings'''
    assert old in s
    s = s.replace(old, new, 1)

    p.write_text(s, encoding="utf-8")


def patch_materialize() -> None:
    p = Path("tools/materialize.py")
    s = p.read_text(encoding="utf-8")

    old = '''    english: dict[str, str] = {}
    unhandled: list[dict] = []
    for path in sorted(project.rglob("*.xaml")):'''
    new = '''    english: dict[str, str] = {}
    unhandled: list[dict] = []
    combobox_display_member_names: set[str] = set()
    for cs_path in sorted(project.rglob("*.cs")):
        if any(part in {"obj", "bin"} for part in cs_path.parts):
            continue
        cs_text = cs_path.read_text(encoding="utf-8")
        combobox_display_member_names.update(
            re.findall(r'\\b([A-Za-z_]\\w*)\\.DisplayMemberPath\\s*=', cs_text)
        )
    for path in sorted(project.rglob("*.xaml")):'''
    assert old in s
    s = s.replace(old, new, 1)

    old = 'text, entries = transform_xaml(path.read_text(encoding="utf-8"), rel)'
    new = 'text, entries = transform_xaml(path.read_text(encoding="utf-8"), rel, skip_combobox_item_templates=combobox_display_member_names)'
    assert old in s
    s = s.replace(old, new, 1)

    p.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    patch_transform()
    patch_materialize()
