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
    if not value or value.startswith("{"):
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
        return f'<TextBlock{attrs} Text="{html.escape(raw, quote=True)}"/>'
    text = body_re.sub(body_sub, text)
    tag_re = re.compile(r'<(?P<tag>[A-Za-z_][\w:.]*)(?P<attrs>\s+[^<>]*?)(?P<close>/?)>', re.S)
    def tag_sub(m: re.Match) -> str:
        tag, attrs, close = m.group("tag"), m.group("attrs"), m.group("close")
        if tag.startswith("/") or tag in {"Run"}:
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


def _cs_key(relpath: str, text: str, kind: str) -> str:
    digest = hashlib.sha1(f"{relpath}|{kind}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"CS_{digest}"


def transform_csharp(text: str, relpath: str) -> tuple[str, dict[str, str]]:
    if not _is_ui_file(relpath):
        return text, {}
    entries: dict[str, str] = {}
    prop_alt = "|".join(map(re.escape, UI_ASSIGN_PROPS))
    prop_re = re.compile(rf'\b(?P<prop>{prop_alt})\s*=\s*"(?P<value>(?:[^"\\]|\\.)*)"')
    def prop_sub(m: re.Match) -> str:
        value = bytes(m.group("value"), "utf-8").decode("unicode_escape") if "\\" in m.group("value") else m.group("value")
        if not value.strip() or not any(ch.isalpha() for ch in value):
            return m.group(0)
        key = _cs_key(relpath, value, m.group("prop"))
        entries[key] = value
        fallback = m.group("value").replace('"', '\\"')
        return f'{m.group("prop")} = RenoDXCommander.Services.LocalizationService.GetString("{key}", "{fallback}")'
    text = prop_re.sub(prop_sub, text)
    call_alt = "|".join(map(re.escape, UI_CALLS))
    call_re = re.compile(rf'(?P<call>{call_alt})\(\s*"(?P<value>(?:[^"\\]|\\.)*)"\s*\)')
    def call_sub(m: re.Match) -> str:
        value = m.group("value")
        key = _cs_key(relpath, value, m.group("call"))
        entries[key] = value
        return f'{m.group("call")}(RenoDXCommander.Services.LocalizationService.GetString("{key}", "{value}"))'
    return call_re.sub(call_sub, text), entries


def scan_csharp_unhandled(text: str, relpath: str) -> list[dict[str, str]]:
    if not _is_ui_file(relpath):
        return []
    findings: list[dict[str, str]] = []
    patterns = [
        re.compile(r'(?P<callee>(?:SetStatus|Show\w*Dialog|NotifyUser|MessageBox\.Show))\(\s*\$"(?P<text>[^"]*[A-Za-z][^"]*)"'),
        re.compile(r'\b(?:Text|Content|Header|Title)\s*=\s*\$"(?P<text>[^"]*[A-Za-z][^"]*)"'),
    ]
    for pat in patterns:
        for m in pat.finditer(text):
            findings.append({"file": relpath, "text": m.group("text"), "kind": "interpolated"})
    return findings
