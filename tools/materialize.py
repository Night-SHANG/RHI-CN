from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.console import print_json
from tools.resw import read_resw, write_resw, materialize_zh
from tools.transform import transform_xaml, transform_csharp, scan_csharp_unhandled
from tools.manifest_scan import extract_user_visible_manifest_text
from tools.translation_memory import load_translation_memory

PACKAGE_VERSION = "2.3.0"
LANGUAGE_BUTTON = '''                    <Button x:Name="LanguageBtn" Content="Language"
                            Background="{StaticResource SurfaceInputBrush}" Foreground="{StaticResource AccentTealBrush}"
                            BorderBrush="{StaticResource AccentTealBorderBrush}" BorderThickness="1"
                            CornerRadius="8" Padding="12,7" FontSize="12"
                            ToolTipService.ToolTip="Language changes apply after restarting RHI">
                        <Button.Flyout>
                            <MenuFlyout Placement="Bottom">
                                <MenuFlyoutItem Text="System" Click="LanguageSystem_Click"/>
                                <MenuFlyoutItem Text="English" Click="LanguageEnglish_Click"/>
                                <MenuFlyoutItem Text="简体中文" Click="LanguageChinese_Click"/>
                            </MenuFlyout>
                        </Button.Flyout>
                    </Button>
'''


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _assembly_version(release_version: str) -> str:
    parts = release_version.strip().split(".")
    if not 2 <= len(parts) <= 4 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid release version: {release_version}")
    return ".".join((parts + ["0"] * 4)[:4])


def _set_project_version(text: str, release_version: str) -> str:
    version = _assembly_version(release_version)
    for tag in ("AssemblyVersion", "FileVersion"):
        pattern = rf'<{tag}>[^<]*</{tag}>'
        replacement = f'<{tag}>{version}</{tag}>'
        if re.search(pattern, text):
            text = re.sub(pattern, replacement, text, count=1)
        else:
            m = re.search(r'</PropertyGroup>', text)
            if not m:
                raise RuntimeError("RenoDXCommander.csproj PropertyGroup contract changed")
            text = text[:m.start()] + f'    {replacement}\n' + text[m.start():]
    return text


def _patch_csproj(path: Path, release_version: str | None = None) -> None:
    text = path.read_text(encoding="utf-8")
    if release_version:
        text = _set_project_version(text, release_version)
    if "WinUI3Localizer" not in text:
        idx = text.rfind("</ItemGroup>")
        if idx < 0:
            raise RuntimeError("RenoDXCommander.csproj package ItemGroup contract changed")
        insertion = f'    <PackageReference Include="WinUI3Localizer" Version="{PACKAGE_VERSION}" />\n'
        text = text[:idx] + insertion + text[idx:]
    if 'Content Include="Strings\\**\\*.resw"' not in text:
        marker = "  <ItemGroup>\n    <Content Remove=\"Assets\\manifest.json\" />"
        if marker not in text:
            first = text.find("<ItemGroup>")
            if first < 0:
                raise RuntimeError("RenoDXCommander.csproj content ItemGroup contract changed")
            block = '  <ItemGroup>\n    <Content Include="Strings\\**\\*.resw">\n      <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>\n      <ExcludeFromSingleFile>true</ExcludeFromSingleFile>\n    </Content>\n  </ItemGroup>\n'
            text = text[:first] + block + text[first:]
        else:
            block = '  <ItemGroup>\n    <Content Include="Strings\\**\\*.resw">\n      <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>\n      <ExcludeFromSingleFile>true</ExcludeFromSingleFile>\n    </Content>\n  </ItemGroup>\n\n'
            text = text.replace(marker, block + marker, 1)
    path.write_text(text, encoding="utf-8")


def _patch_app(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "LocalizationService.InitializeAsync" in text:
        return
    sig = "protected override void OnLaunched(LaunchActivatedEventArgs args)"
    if sig in text:
        text = text.replace(sig, "protected override async void OnLaunched(LaunchActivatedEventArgs args)", 1)
    elif "protected override async void OnLaunched(LaunchActivatedEventArgs args)" not in text:
        raise RuntimeError("App.OnLaunched signature changed")
    anchor = "DownloadsMigrationService.RunOnce();"
    if anchor not in text:
        m = re.search(r'OnLaunched\([^)]*\)\s*\{', text)
        if not m:
            raise RuntimeError("App.OnLaunched bootstrap anchor changed")
        pos = m.end()
        text = text[:pos] + "\n        await RenoDXCommander.Services.LocalizationService.InitializeAsync();" + text[pos:]
    else:
        text = text.replace(anchor, anchor + "\n        await RenoDXCommander.Services.LocalizationService.InitializeAsync();", 1)
    path.write_text(text, encoding="utf-8")


def _patch_app_resources(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if 'xmlns:services="using:RenoDXCommander.Services"' not in text:
        xns = re.search(r'xmlns:x="[^"]+"', text)
        if not xns:
            raise RuntimeError("App.xaml x namespace contract changed")
        text = text[:xns.end()] + '\n    xmlns:services="using:RenoDXCommander.Services"' + text[xns.end():]
    if 'x:Key="LocalizedComboBoxItemTemplate"' not in text:
        resources = '''
                <services:LocalizedStringConverter x:Key="LocalizedStringConverter"/>
                <DataTemplate x:Key="LocalizedComboBoxItemTemplate">
                    <TextBlock Text="{Binding Converter={StaticResource LocalizedStringConverter}}"/>
                </DataTemplate>'''
        self_closing = re.search(r'<ResourceDictionary\s*/>', text)
        if self_closing:
            replacement = '<ResourceDictionary>' + resources + '\n            </ResourceDictionary>'
            text = text[:self_closing.start()] + replacement + text[self_closing.end():]
        else:
            opening = re.search(r'<ResourceDictionary(?:\s+[^>]*)?>', text)
            if not opening:
                raise RuntimeError("App.xaml ResourceDictionary contract changed")
            merged_close = re.search(r'</ResourceDictionary\.MergedDictionaries\s*>', text[opening.end():])
            if merged_close:
                insert_pos = opening.end() + merged_close.end()
            else:
                insert_pos = opening.end()
            text = text[:insert_pos] + resources + text[insert_pos:]
    path.write_text(text, encoding="utf-8")


def _inject_language_button(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if 'x:Name="LanguageBtn"' in text:
        return
    idx = text.find('<Button x:Name="SettingsBtn"')
    if idx < 0:
        raise RuntimeError("MainWindow.xaml SettingsBtn anchor changed")
    line_start = text.rfind("\n", 0, idx) + 1
    prefix = text[line_start:idx]
    if prefix.strip():
        insert_pos = idx
        indent = ""
    else:
        insert_pos = line_start
        indent = prefix
    snippet = "\n".join((indent + line if line else line) for line in LANGUAGE_BUTTON.splitlines()) + "\n"
    text = text[:insert_pos] + snippet + text[insert_pos:]
    path.write_text(text, encoding="utf-8")


def _data_key(text: str) -> str:
    return "Data_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _patch_dynamic_ui(project: Path) -> None:
    """Localize display-only runtime values without changing persisted/program state values."""
    faq = project / "MainWindow.FaqBuilder.cs"
    if faq.exists():
        text = faq.read_text(encoding="utf-8")
        text = re.sub(r'\bText\s*=\s*title\b', 'Text = RenoDXCommander.Services.LocalizationService.GetDataString(title)', text)
        text = re.sub(r'\bText\s*=\s*description\b', 'Text = RenoDXCommander.Services.LocalizationService.GetDataString(description)', text)
        text = re.sub(r'\bText\s*=\s*tip\b', 'Text = RenoDXCommander.Services.LocalizationService.GetDataString(tip)', text)
        text = text.replace('Text = $"• {bullet}"', 'Text = $"• {RenoDXCommander.Services.LocalizationService.GetDataString(bullet)}"')
        faq.write_text(text, encoding="utf-8")

    factory = project / "UIFactory.cs"
    if factory.exists():
        text = factory.read_text(encoding="utf-8")
        text = re.sub(r'\bText\s*=\s*label\b', 'Text = RenoDXCommander.Services.LocalizationService.GetDataString(label)', text)
        text = re.sub(r'\bText\s*=\s*text\b', 'Text = RenoDXCommander.Services.LocalizationService.GetDataString(text)', text)
        text = re.sub(r'\bContent\s*=\s*content\b', 'Content = RenoDXCommander.Services.LocalizationService.GetDataString(content)', text)
        factory.write_text(text, encoding="utf-8")

    main_vm = project / "ViewModels" / "MainViewModel.cs"
    if main_vm.exists():
        text = main_vm.read_text(encoding="utf-8")
        text = text.replace('"Detail View"', 'RenoDXCommander.Services.LocalizationService.GetDataString("Detail View")')
        text = text.replace('"Simple View"', 'RenoDXCommander.Services.LocalizationService.GetDataString("Simple View")')
        main_vm.write_text(text, encoding="utf-8")

    components = project / "DetailPanelBuilder.Components.cs"
    if components.exists():
        text = components.read_text(encoding="utf-8")
        marker = re.search(r'((?:private\s+)?static\s+object\s+WithInfoArrow\([^)]*\)\s*\{)', text)
        if marker and "label = LocalizationService.GetDataString(label);" not in text:
            pos = marker.end()
            text = text[:pos] + '\n        label = LocalizationService.GetDataString(label);' + text[pos:]
        text = text.replace(
            'ToolTipService.SetToolTip(infoBtn, tooltip);',
            'ToolTipService.SetToolTip(infoBtn, LocalizationService.GetDataString(tooltip));')
        text = re.sub(
            r'(\.Text\s*=\s*)(card\.[A-Za-z_][A-Za-z0-9_]*StatusText)(?=;)',
            r'\1LocalizationService.GetDataString(\2)',
            text)
        components.write_text(text, encoding="utf-8")


def _patch_manifest_display(project: Path) -> None:
    warning_file = project / "ViewModels" / "MainViewModel.Install.Luma.cs"
    if warning_file.exists():
        text = warning_file.read_text(encoding="utf-8")
        anchor = "Content = message,"
        replacement = "Content = RenoDXCommander.Services.LocalizationService.GetDataString(message),"
        if replacement not in text:
            if anchor not in text:
                if "CheckInstallWarningAsync" in text:
                    raise RuntimeError("Install warning display contract changed")
            else:
                text = text.replace(anchor, replacement, 1)
                warning_file.write_text(text, encoding="utf-8")

    dialog_file = project / "DialogService.Game.cs"
    if dialog_file.exists():
        text = dialog_file.read_text(encoding="utf-8")
        if "GetDataString(text);" not in text and "AddTextOrHyperlink(" in text:
            signature_end = re.search(r'(private static void AddTextOrHyperlink\([\s\S]*?\)\s*\{)', text)
            if not signature_end:
                raise RuntimeError("DialogService AddTextOrHyperlink contract changed")
            pos = signature_end.end()
            inject = "\n        text = LocalizationService.GetDataString(text);\n        if (!string.IsNullOrEmpty(urlLabel)) urlLabel = LocalizationService.GetDataString(urlLabel);"
            text = text[:pos] + inject + text[pos:]
        if "GetDataString(label);" not in text and "AddHyperlinkBlock(" in text:
            signature_end = re.search(r'(private static void AddHyperlinkBlock\([\s\S]*?\)\s*\{)', text)
            if not signature_end:
                raise RuntimeError("DialogService AddHyperlinkBlock contract changed")
            pos = signature_end.end()
            text = text[:pos] + "\n        label = LocalizationService.GetDataString(label);" + text[pos:]
        text = text.replace("Text         = result.Content,", "Text         = LocalizationService.GetDataString(result.Content),")
        text = text.replace("Text         = entry.Notes,", "Text         = LocalizationService.GetDataString(entry.Notes),")
        dialog_file.write_text(text, encoding="utf-8")


def materialize(source_root: Path, repo_root: Path, release_version: str | None = None) -> dict:
    source_root = Path(source_root)
    repo_root = Path(repo_root)
    project = source_root / "RenoDXCommander"
    required = [project / "RenoDXCommander.csproj", project / "App.xaml.cs", project / "MainWindow.xaml"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Required upstream files missing: {missing}")

    _patch_csproj(project / "RenoDXCommander.csproj", release_version=release_version)
    _patch_app(project / "App.xaml.cs")
    _patch_app_resources(project / "App.xaml")
    _inject_language_button(project / "MainWindow.xaml")

    overlay = repo_root / "overlay" / "RenoDXCommander"
    for rel in (Path("Services/LocalizationService.cs"), Path("MainWindow.Localization.cs")):
        src = overlay / rel
        if not src.exists():
            raise RuntimeError(f"Missing overlay file: {src}")
        dest = project / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    _patch_dynamic_ui(project)
    _patch_manifest_display(project)

    english: dict[str, str] = {}
    unhandled: list[dict] = []
    combobox_display_member_names: set[str] = set()
    for cs_path in sorted(project.rglob("*.cs")):
        if any(part in {"obj", "bin"} for part in cs_path.parts):
            continue
        cs_text = cs_path.read_text(encoding="utf-8")
        combobox_display_member_names.update(
            re.findall(r'\b([A-Za-z_]\w*)\.DisplayMemberPath\s*=', cs_text)
        )
    for path in sorted(project.rglob("*.xaml")):
        if any(part in {"obj", "bin"} for part in path.parts):
            continue
        rel = path.relative_to(source_root).as_posix()
        text, entries = transform_xaml(path.read_text(encoding="utf-8"), rel, skip_combobox_item_templates=combobox_display_member_names)
        path.write_text(text, encoding="utf-8")
        english.update(entries)
    for path in sorted(project.rglob("*.cs")):
        if any(part in {"obj", "bin"} for part in path.parts) or path.name == "LocalizationService.cs":
            continue
        rel = path.relative_to(project).as_posix()
        original = path.read_text(encoding="utf-8")
        text, entries = transform_csharp(original, rel)
        if text != original:
            path.write_text(text, encoding="utf-8")
        english.update(entries)
        unhandled.extend(scan_csharp_unhandled(text, rel))

    manifest_path = source_root / "manifest.json"
    manifest_visible: list[str] = []
    if manifest_path.exists():
        try:
            manifest_visible = extract_user_visible_manifest_text(json.loads(manifest_path.read_text(encoding="utf-8-sig")))
        except Exception as exc:
            raise RuntimeError(f"Unable to parse manifest.json: {exc}") from exc

    for text in manifest_visible:
        english[_data_key(text)] = text

    exact = read_resw(repo_root / "Localization" / "zh-CN" / "Resources.resw")
    memory = load_translation_memory(repo_root / "Localization")
    # Runtime-generated UI strings use GetDataString. Emit every known translation-memory
    # source as a Data_* resource so display-only wrappers can translate without changing
    # the underlying program values used for comparisons, persistence, and install logic.
    for source in memory:
        if isinstance(source, str) and source:
            english.setdefault(_data_key(source), source)
    zh, fallback = materialize_zh(english, exact, memory)
    write_resw(project / "Strings" / "en-US" / "Resources.resw", english)
    write_resw(project / "Strings" / "zh-CN" / "Resources.resw", zh)

    reports = repo_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    result = {
        "english_keys": len(english),
        "translated_keys": len(english) - len(fallback),
        "fallback_keys": fallback,
        "coverage_percent": round(((len(english) - len(fallback)) / len(english) * 100.0), 2) if english else 0.0,
        "unhandled_csharp": unhandled,
        "manifest_visible_text": manifest_visible,
        "release_version_override": release_version,
    }
    (reports / "localization-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--release-version")
    args = ap.parse_args()
    result = materialize(args.source, args.repo, release_version=args.release_version)
    print_json(result)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())