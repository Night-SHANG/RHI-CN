from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from tools.resw import read_resw, write_resw, materialize_zh
from tools.transform import transform_xaml, transform_csharp, scan_csharp_unhandled
from tools.manifest_scan import extract_user_visible_manifest_text

PACKAGE_VERSION = "2.3.0"
LANGUAGE_BUTTON = '''                    <Button x:Name="LanguageBtn" l:Uids.Uid="Toolbar_LanguageButton" Content="Language"
                            Background="{StaticResource SurfaceInputBrush}" Foreground="{StaticResource AccentTealBrush}"
                            BorderBrush="{StaticResource AccentTealBorderBrush}" BorderThickness="1"
                            CornerRadius="8" Padding="12,7" FontSize="12"
                            ToolTipService.ToolTip="Language changes apply after restarting RHI">
                        <Button.Flyout>
                            <MenuFlyout Placement="Bottom">
                                <MenuFlyoutItem l:Uids.Uid="Toolbar_LanguageSystem" Text="System" Click="LanguageSystem_Click"/>
                                <MenuFlyoutItem l:Uids.Uid="Toolbar_LanguageEnglish" Text="English" Click="LanguageEnglish_Click"/>
                                <MenuFlyoutItem l:Uids.Uid="Toolbar_LanguageChinese" Text="简体中文" Click="LanguageChinese_Click"/>
                            </MenuFlyout>
                        </Button.Flyout>
                    </Button>
'''


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_csproj(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
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


def _inject_language_button(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if 'x:Name="LanguageBtn"' in text:
        return
    idx = text.find('<Button x:Name="SettingsBtn"')
    if idx < 0:
        raise RuntimeError("MainWindow.xaml SettingsBtn anchor changed")
    line_start = text.rfind("\n", 0, idx) + 1
    indent = text[line_start:idx]
    snippet = "\n".join((indent + line if line else line) for line in LANGUAGE_BUTTON.splitlines()) + "\n"
    text = text[:line_start] + snippet + indent + text[idx:]
    path.write_text(text, encoding="utf-8")


def _data_key(text: str) -> str:
    return "Data_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


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


def materialize(source_root: Path, repo_root: Path) -> dict:
    source_root = Path(source_root)
    repo_root = Path(repo_root)
    project = source_root / "RenoDXCommander"
    required = [project / "RenoDXCommander.csproj", project / "App.xaml.cs", project / "MainWindow.xaml"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Required upstream files missing: {missing}")

    _patch_csproj(project / "RenoDXCommander.csproj")
    _patch_app(project / "App.xaml.cs")
    _inject_language_button(project / "MainWindow.xaml")

    overlay = repo_root / "overlay" / "RenoDXCommander"
    for rel in (Path("Services/LocalizationService.cs"), Path("MainWindow.Localization.cs")):
        src = overlay / rel
        if not src.exists():
            raise RuntimeError(f"Missing overlay file: {src}")
        dest = project / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    _patch_manifest_display(project)

    english: dict[str, str] = {}
    unhandled: list[dict] = []
    for path in sorted(project.rglob("*.xaml")):
        if any(part in {"obj", "bin"} for part in path.parts):
            continue
        rel = path.relative_to(source_root).as_posix()
        text, entries = transform_xaml(path.read_text(encoding="utf-8"), rel)
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
        unhandled.extend(scan_csharp_unhandled(original, rel))

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
    memory = _load_json(repo_root / "Localization" / "translation-memory.json", {})
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
    }
    (reports / "localization-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    result = materialize(args.source, args.repo)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
