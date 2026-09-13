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
    "AddonPopupHelper", "SettingsHandler", "InstallEventHandler", "SetupWindow",
    "Dialog", "UIFactory",
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


def transform_xaml(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    text = _ensure_localizer_namespace(text)
    entries: dict[str, str] = {}
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
        found: list[tuple[str, str]] = []
        for attr in LOCALIZABLE_ATTRS:
            am = re.search(rf'(?<![\w:.]){re.escape(attr)}\s*=\s*"([^"]*)"', attrs)
            if am and _valid_literal(am.group(1)):
                found.append((attr, html.unescape(am.group(1))))
        if not found:
            return m.group(0)
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


def _transform_interpolated_ui(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    entries: dict[str, str] = {}
    replacements: list[tuple[int, int, str]] = []
    for start, end, body in _find_interpolated_strings(text):
        context = _interpolated_context(text, start)
        if not context:
            continue
        fmt, args, has_english = _split_interpolated_body(body)
        if not has_english or not args:
            continue
        kind, name = context
        key = _cs_key(relpath, fmt, f'interpolated:{kind}:{name}')
        entries[key] = fmt
        fallback = _encode_csharp_string(fmt)
        rendered_args = ', '.join(f'$"{{{expr}}}"' for expr in args)
        replacement = (
            f'RenoDXCommander.Services.LocalizationService.Format("{key}", "{fallback}"'
            + (f', {rendered_args}' if rendered_args else '') + ')'
        )
        replacements.append((start, end, replacement))
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    return text, entries


def _transform_tooltip_literals(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    entries: dict[str, str] = {}
    tooltip_re = re.compile(
        r'ToolTipService\.SetToolTip\(\s*(?P<target>[^,\n]+?)\s*,\s*"(?P<value>(?:[^"\\]|\\.)*)"\s*\)'
    )
    def tooltip_sub(m: re.Match) -> str:
        raw = m.group("value")
        value = _decode_csharp_string(raw)
        if not value.strip() or not any(ch.isalpha() for ch in value):
            return m.group(0)
        key = _cs_key(relpath, value, "ToolTipService.SetToolTip")
        entries[key] = value
        fallback = _encode_csharp_string(value)
        return (
            f'ToolTipService.SetToolTip({m.group("target")}, '
            f'RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}"))'
        )
    return tooltip_re.sub(tooltip_sub, text), entries


def _inject_combobox_item_template(text: str) -> str:
    """Use a display-only template so ComboBox values stay stable for program logic."""
    pattern = re.compile(r'new\s+ComboBox\s*\{')
    return pattern.sub(
        lambda m: m.group(0) + '\n            ItemTemplate = RenoDXCommander.Services.LocalizationService.ComboBoxItemTemplate,',
        text,
    )


def transform_csharp(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    if not _is_ui_file(relpath):
        return text, {}
    entries: dict[str, str] = {}
    prop_alt = "|".join(map(re.escape, UI_ASSIGN_PROPS))
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
    text, tooltip_entries = _transform_tooltip_literals(text, relpath)
    entries.update(tooltip_entries)
    text, interpolated_entries = _transform_interpolated_ui(text, relpath)
    entries.update(interpolated_entries)
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
        if has_english and args:
            findings.append({"file": relpath, "text": body, "format": fmt, "kind": "interpolated"})
    return findings
