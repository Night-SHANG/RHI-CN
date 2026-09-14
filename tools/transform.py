from __future__ import annotations
import hashlib
import html
import re
from pathlib import Path

LOCALIZABLE_ATTRS = (
    "Text", "Content", "Header", "PlaceholderText", "Title",
    "PrimaryButtonText", "SecondaryButtonText", "CloseButtonText",
    "AutomationProperties.Name", "ToolTipService.ToolTip",
)
UI_FILE_PATTERNS = (
    "MainWindow", "DetailPanelBuilder", "CompactViewBuilder", "AddonManagerDialog",
    "PopupHelper", "SettingsHandler", "InstallEventHandler", "SetupWindow",
    "Dialog", "UIFactory", "UpdateInclusionHelper",
)
UI_ASSIGN_PROPS = (
    "Text", "Content", "Header", "PlaceholderText", "Title",
    "PrimaryButtonText", "SecondaryButtonText", "CloseButtonText",
    "OnContent", "OffContent",
)
UI_CALLS = (
    "SetStatus", "ShowErrorDialog", "ShowInfoDialog", "NotifyUser",
    "ShowMessage", "MessageBox.Show",
)


def _uid(relpath: str, tag: str, text: str) -> str:
    digest = hashlib.sha1(f"{relpath}|{tag}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"Auto_{digest}"


def _valid_literal(value: str) -> bool:
    value = html.unescape(value).strip()
    if not value:
        return False
    if value.startswith("{"):
        return False
    return any(ch.isalpha() for ch in value)


def _ensure_localizer_namespace(text: str) -> str:
    existing = re.search(r'xmlns:l="([^"]+)"', text)
    if existing:
        if existing.group(1) != "using:WinUI3Localizer":
            raise RuntimeError(f"XAML namespace prefix l is already bound to {existing.group(1)}")
        return text
    m = re.search(r'<(?:Window|Page|UserControl)\b', text)
    if not m:
        return text
    xns = re.search(r'(xmlns:x="[^"]+")', text[m.start():])
    if xns:
        pos = m.start() + xns.end()
        return text[:pos] + '\n    xmlns:l="using:WinUI3Localizer"' + text[pos:]
    pos = m.end()
    return text[:pos] + ' xmlns:l="using:WinUI3Localizer"' + text[pos:]


def transform_xaml(text: str, relpath: str, skip_combobox_item_templates: set[str] | None = None) -> tuple[str, dict[str, str]]:
    text = _ensure_localizer_namespace(text)
    entries: dict[str, str] = {}
    skip_combobox_item_templates = skip_combobox_item_templates or set()
    body_re = re.compile(r'<TextBlock(?P<attrs>[^>]*)>(?P<body>[^<]+)</TextBlock>', re.S)
    def body_sub(m: re.Match) -> str:
        attrs, body = m.group("attrs"), m.group("body")
        raw = html.unescape(body.strip())
        if not _valid_literal(raw) or re.search(r'\bText\s*=', attrs):
            return m.group(0)
        esc = html.escape(raw, quote=True)
        return f'<TextBlock{attrs} Text="{esc}"/>'
    text = body_re.sub(body_sub, text)
    tag_re = re.compile(r'<(?P<tag>[A-Za-z_][\w:.]*)(?P<attrs>\s+[^<>]*?)(?P<close>/?)>', re.S)
    def tag_sub(m: re.Match) -> str:
        tag, attrs, close = m.group("tag"), m.group("attrs"), m.group("close")
        # WinUI 3 Window is not a DependencyObject, so WinUI3Localizer's
        # attached DependencyProperty cannot be assigned to the root Window.
        if tag.startswith("/") or tag in {"Run", "Window"}:
            return m.group(0)
        combo_template_added = False
        combo_name_match = re.search(r'x:Name\s*=\s*"([^"]+)"', attrs)
        combo_name = combo_name_match.group(1) if combo_name_match else None
        has_display_member_path = bool(re.search(r'\bDisplayMemberPath\s*=', attrs))
        if (
            tag == "ComboBox"
            and not re.search(r'\bItemTemplate\s*=', attrs)
            and not has_display_member_path
            and combo_name not in skip_combobox_item_templates
        ):
            attrs += ' ItemTemplate="{StaticResource LocalizedComboBoxItemTemplate}"'
            combo_template_added = True
        found: list[tuple[str, str]] = []
        for attr in LOCALIZABLE_ATTRS:
            am = re.search(rf'(?<![\w:.]){re.escape(attr)}\s*=\s*"([^"]*)"', attrs)
            if am and _valid_literal(am.group(1)):
                found.append((attr, html.unescape(am.group(1))))
        if not found:
            return f'<{tag}{attrs}{close}>' if combo_template_added else m.group(0)
        um = re.search(r'l:Uids\.Uid\s*=\s*"([^"]+)"', attrs)
        if um:
            uid = um.group(1)
        else:
            nm = re.search(r'x:Name\s*=\s*"([^"]+)"', attrs)
            uid = nm.group(1) if nm else _uid(relpath, tag, "|".join(v for _, v in found))
            attrs += f' l:Uids.Uid="{uid}"'
        for attr, value in found:
            entries[f"{uid}.{attr}"] = value
        return f'<{tag}{attrs}{close}>'
    return tag_re.sub(tag_sub, text), entries


def _is_ui_file(relpath: str) -> bool:
    name = Path(relpath).name
    return any(pat in name for pat in UI_FILE_PATTERNS)


def _decode_csharp_string(value: str) -> str:
    """Decode regular C# string-literal escapes without re-decoding UTF-8 text."""
    simple = {
        "\\": "\\", '"': '"', "'": "'", "0": "\0", "a": "\a",
        "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v",
    }
    out: list[str] = []
    i = 0
    while i < len(value):
        if value[i] != "\\" or i + 1 >= len(value):
            out.append(value[i]); i += 1; continue
        code = value[i + 1]
        if code in simple:
            out.append(simple[code]); i += 2; continue
        if code == "u" and i + 6 <= len(value):
            chunk = value[i + 2:i + 6]
            if re.fullmatch(r"[0-9A-Fa-f]{4}", chunk):
                out.append(chr(int(chunk, 16))); i += 6; continue
        if code == "U" and i + 10 <= len(value):
            chunk = value[i + 2:i + 10]
            if re.fullmatch(r"[0-9A-Fa-f]{8}", chunk):
                out.append(chr(int(chunk, 16))); i += 10; continue
        if code == "x":
            m = re.match(r"[0-9A-Fa-f]{1,4}", value[i + 2:])
            if m:
                out.append(chr(int(m.group(0), 16))); i += 2 + len(m.group(0)); continue
        out.append("\\" + code); i += 2
    return "".join(out)


def _cs_key(relpath: str, text: str, kind: str) -> str:
    digest = hashlib.sha1(f"{relpath}|{kind}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"CS_{digest}"


def _data_key(text: str) -> str:
    return "Data_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _collect_runtime_display_sources(text: str) -> dict[str, str]:
    """Collect runtime-displayed strings without changing their program values."""
    sources: set[str] = set()
    literal_re = re.compile(r'"((?:[^"\\]|\\.)*)"')

    tooltip_assignment = re.compile(
        r'\b[A-Za-z_]\w*(?:ToolTip|Tooltip)\w*\s*=\s*(?P<expr>[^;]+);', re.S
    )
    for match in tooltip_assignment.finditer(text):
        for raw in literal_re.findall(match.group("expr")):
            value = _decode_csharp_string(raw)
            if value.strip() and any(ch.isalpha() for ch in value):
                sources.add(value)

    option_block = re.compile(
        r'\b[A-Za-z_]\w*(?:Options|Presets)\s*=\s*\[(?P<body>[\s\S]*?)\];'
    )
    tuple_first = re.compile(r'\(\s*"((?:[^"\\]|\\.)*)"\s*,')
    for match in option_block.finditer(text):
        for raw in tuple_first.findall(match.group("body")):
            value = _decode_csharp_string(raw)
            if value.strip() and any(ch.isalpha() for ch in value):
                sources.add(value)

    for match in re.finditer(r'ItemsSource\s*=\s*new\s*\[\]\s*\{(?P<body>[\s\S]*?)\}', text):
        for raw in literal_re.findall(match.group("body")):
            value = _decode_csharp_string(raw)
            if value.strip() and any(ch.isalpha() for ch in value):
                sources.add(value)
    for raw in re.findall(r'\.Items\.Add\(\s*"((?:[^"\\]|\\.)*)"\s*\)', text):
        value = _decode_csharp_string(raw)
        if value.strip() and any(ch.isalpha() for ch in value):
            sources.add(value)

    return {_data_key(source): source for source in sorted(sources)}


def _find_interpolated_strings(text: str) -> list[tuple[int, int, str]]:
    """Return spans for regular C# interpolated strings ($\"...\")."""
    found: list[tuple[int, int, str]] = []
    i = 0
    while True:
        start = text.find('$"', i)
        if start < 0:
            break
        j = start + 2
        body_start = j
        depth = 0
        quote: str | None = None
        while j < len(text):
            ch = text[j]
            if depth == 0:
                if ch == '\\':
                    j += 2
                    continue
                if ch == '"':
                    found.append((start, j + 1, text[body_start:j]))
                    i = j + 1
                    break
                if ch == '{':
                    if j + 1 < len(text) and text[j + 1] == '{':
                        j += 2
                        continue
                    depth = 1
                    j += 1
                    continue
                if ch == '}' and j + 1 < len(text) and text[j + 1] == '}':
                    j += 2
                    continue
                j += 1
                continue
            if quote is not None:
                if ch == '\\':
                    j += 2
                    continue
                if ch == quote:
                    quote = None
                j += 1
                continue
            if ch in {'"', "'"}:
                quote = ch
                j += 1
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            j += 1
        else:
            i = start + 2
    return found


def _split_interpolated_body(body: str) -> tuple[str, list[str], bool]:
    """Normalize an interpolated-string body into a composite format string."""
    parts: list[str] = []
    args: list[str] = []
    literal: list[str] = []
    i = 0
    def flush_literal() -> None:
        if not literal:
            return
        decoded = _decode_csharp_string(''.join(literal))
        parts.append(decoded.replace('{', '{{').replace('}', '}}'))
        literal.clear()
    while i < len(body):
        ch = body[i]
        if ch == '\\' and i + 1 < len(body):
            literal.append(body[i:i + 2])
            i += 2
            continue
        if ch == '{' and i + 1 < len(body) and body[i + 1] == '{':
            literal.append('{')
            i += 2
            continue
        if ch == '}' and i + 1 < len(body) and body[i + 1] == '}':
            literal.append('}')
            i += 2
            continue
        if ch != '{':
            literal.append(ch)
            i += 1
            continue
        flush_literal()
        expr_start = i + 1
        j = expr_start
        depth = 1
        quote: str | None = None
        while j < len(body):
            cur = body[j]
            if quote is not None:
                if cur == '\\':
                    j += 2
                    continue
                if cur == quote:
                    quote = None
                j += 1
                continue
            if cur in {'"', "'"}:
                quote = cur
                j += 1
                continue
            if cur == '{':
                depth += 1
            elif cur == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:
            return body, [], False
        expression = body[expr_start:j].strip()
        args.append(expression)
        parts.append('{' + str(len(args) - 1) + '}')
        i = j + 1
    flush_literal()
    fmt = ''.join(parts)
    has_english_literal = any(('A' <= ch <= 'Z') or ('a' <= ch <= 'z') for ch in fmt if ch not in '{}0123456789')
    return fmt, args, has_english_literal


def _encode_csharp_string(value: str) -> str:
    return (value.replace('\\', '\\\\').replace('"', '\\"')
                 .replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t'))


def _interpolated_context(text: str, start: int) -> tuple[str, str] | None:
    prefix = text[max(0, start - 240):start]
    prop_alt = '|'.join(map(re.escape, UI_ASSIGN_PROPS))
    prop = re.search(rf'\b(?P<name>{prop_alt})\s*=\s*$', prefix)
    if prop:
        return 'property', prop.group('name')
    call_alt = '|'.join(map(re.escape, UI_CALLS))
    call = re.search(rf'(?P<name>{call_alt})\(\s*$', prefix)
    if call:
        return 'call', call.group('name')
    return None


def _is_probably_text_expression(expr: str) -> bool:
    expr = expr.strip()
    if not re.fullmatch(r'(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*', expr):
        return False
    tail = expr.rsplit('.', 1)[-1].lower()
    exact = {"text", "label", "title", "name", "content", "message", "description", "tip", "tooltip", "status"}
    return tail in exact or tail.endswith(("text", "label", "title", "name", "content", "message", "description", "tip", "tooltip", "status"))


def _transform_interpolated_ui(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    entries: dict[str, str] = {}
    replacements: list[tuple[int, int, str]] = []
    for start, end, body in _find_interpolated_strings(text):
        context = _interpolated_context(text, start)
        if not context:
            continue
        fmt, args, has_english = _split_interpolated_body(body)
        if not args:
            continue
        if not has_english and not any(_is_probably_text_expression(expr) for expr in args):
            continue
        kind, name = context
        key = _cs_key(relpath, fmt, f'interpolated:{kind}:{name}')
        entries[key] = fmt
        fallback = _encode_csharp_string(fmt)
        rendered_args = ', '.join(
            f'RenoDXCommander.Services.LocalizationService.GetDataString($"{{{expr}}}")'
            for expr in args
        )
        replacement = (
            f'RenoDXCommander.Services.LocalizationService.Format("{key}", "{fallback}"'
            + (f', {rendered_args}' if rendered_args else '') + ')'
        )
        replacements.append((start, end, replacement))
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    return text, entries


def _find_tooltip_calls(text: str) -> list[tuple[int, int, str, str]]:
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

        if expr.startswith('$"') and expr.endswith('"'):
            fmt, args, has_english = _split_interpolated_body(expr[2:-1])
            if args and has_english:
                key = _cs_key(relpath, fmt, "ToolTipService.SetToolTip:interpolated")
                entries[key] = fmt
                fallback = _encode_csharp_string(fmt)
                rendered_args = ', '.join(f'$"{{{arg}}}"' for arg in args)
                localized = (
                    f'RenoDXCommander.Services.LocalizationService.Format("{key}", "{fallback}"'
                    + (f', {rendered_args}' if rendered_args else '') + ')'
                )
                replacements.append((start, end, f'ToolTipService.SetToolTip({target}, {localized})'))
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

def _localize_literal_expr(relpath: str, prop: str, raw: str, kind: str, entries: dict[str, str]) -> str:
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
    """Localize only simple display-text identifiers, not calls or control expressions."""
    pattern = re.compile(
        r'\bText\s*=\s*(?P<expr>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)(?=\s*[,};])'
    )

    def sub(m: re.Match) -> str:
        expr = m.group("expr")
        if expr.startswith("RenoDXCommander.Services.LocalizationService"):
            return m.group(0)
        if not _is_probably_text_expression(expr):
            return m.group(0)
        return (
            "Text = RenoDXCommander.Services.LocalizationService.GetDataString("
            + expr + ")"
        )

    return pattern.sub(sub, text)

def _inject_combobox_item_template(text: str) -> str:
    """Use a display-only template so ComboBox values stay stable for program logic."""
    pattern = re.compile(r'new\s+ComboBox\s*\{')
    return pattern.sub(
        lambda m: m.group(0) + '\n            ItemTemplate = RenoDXCommander.Services.LocalizationService.ComboBoxItemTemplate,',
        text,
    )


def transform_csharp(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    runtime_entries = _collect_runtime_display_sources(text)
    if not _is_ui_file(relpath):
        return text, runtime_entries
    entries: dict[str, str] = dict(runtime_entries)
    prop_alt = "|".join(map(re.escape, UI_ASSIGN_PROPS))
    text, concat_entries = _transform_concatenated_properties(text, relpath, prop_alt)
    entries.update(concat_entries)
    text, ternary_entries = _transform_ternary_properties(text, relpath, prop_alt)
    entries.update(ternary_entries)
    prop_re = re.compile(rf'\b(?P<prop>{prop_alt})\s*=\s*"(?P<value>(?:[^"\\]|\\.)*)"')
    def prop_sub(m: re.Match) -> str:
        value = _decode_csharp_string(m.group("value"))
        if not value.strip() or not any(ch.isalpha() for ch in value):
            return m.group(0)
        key = _cs_key(relpath, value, m.group("prop"))
        entries[key] = value
        fallback = _encode_csharp_string(value)
        return f'{m.group("prop")} = RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'
    text = prop_re.sub(prop_sub, text)
    call_alt = "|".join(map(re.escape, UI_CALLS))
    call_re = re.compile(rf'(?P<call>{call_alt})\(\s*"(?P<value>(?:[^"\\]|\\.)*)"\s*\)')
    def call_sub(m: re.Match) -> str:
        value = _decode_csharp_string(m.group("value"))
        key = _cs_key(relpath, value, m.group("call"))
        entries[key] = value
        fallback = _encode_csharp_string(value)
        return f'{m.group("call")}(RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}"))'
    text = call_re.sub(call_sub, text)
    text, tooltip_entries = _transform_tooltips(text, relpath)
    entries.update(tooltip_entries)
    text, interpolated_entries = _transform_interpolated_ui(text, relpath)
    entries.update(interpolated_entries)
    text = _transform_dynamic_text_properties(text)
    text = _inject_combobox_item_template(text)
    return text, entries


def scan_csharp_unhandled(text: str, relpath: str) -> list[dict[str, str]]:
    if not _is_ui_file(relpath):
        return []
    findings: list[dict[str, str]] = []
    for start, _end, body in _find_interpolated_strings(text):
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
    return findings
