from pathlib import Path
import json
from tools.materialize import materialize


def make_source(root: Path):
    p = root / "RenoDXCommander"
    (p / "Services").mkdir(parents=True)
    (p / "ViewModels").mkdir(parents=True)
    (p / "RenoDXCommander.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk"><ItemGroup><PackageReference Include="SharpCompress" Version="1" /></ItemGroup></Project>''', encoding="utf-8")
    (p / "App.xaml.cs").write_text('''namespace RenoDXCommander; public partial class App { protected override void OnLaunched(LaunchActivatedEventArgs args) { MigrateLegacyAppData(); DownloadsMigrationService.RunOnce(); } }''', encoding="utf-8")
    (p / "MainWindow.xaml").write_text('''<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><StackPanel><Button x:Name="SettingsBtn" Content="Settings"/></StackPanel></Window>''', encoding="utf-8")
    (p / "DetailPanelBuilder.cs").write_text('''namespace RenoDXCommander; public class X { void A() { var t = new TextBlock { Text = "Install" }; } }''', encoding="utf-8")


def test_materialize_creates_complete_resources_and_overlay(tmp_path: Path):
    src = tmp_path / "src"
    make_source(src)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Localization").mkdir()
    (repo / "Localization" / "translation-memory.json").write_text(json.dumps({"Settings":{"translation":"设置","state":"reviewed"},"Install":{"translation":"安装","state":"reviewed"}}, ensure_ascii=False), encoding="utf-8")
    (repo / "Localization" / "zh-CN").mkdir()
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text('<?xml version="1.0" encoding="utf-8"?><root/>', encoding="utf-8")
    overlay = repo / "overlay" / "RenoDXCommander" / "Services"
    overlay.mkdir(parents=True)
    (overlay / "LocalizationService.cs").write_text('// service', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").write_text('// partial', encoding="utf-8")
    result = materialize(src, repo)
    assert result["english_keys"] >= 2
    assert (src / "RenoDXCommander" / "Strings" / "en-US" / "Resources.resw").exists()
    assert (src / "RenoDXCommander" / "Strings" / "zh-CN" / "Resources.resw").exists()
    csproj = (src / "RenoDXCommander" / "RenoDXCommander.csproj").read_text(encoding="utf-8")
    assert "WinUI3Localizer" in csproj
    app = (src / "RenoDXCommander" / "App.xaml.cs").read_text(encoding="utf-8")
    assert "LocalizationService.InitializeAsync" in app
    xaml = (src / "RenoDXCommander" / "MainWindow.xaml").read_text(encoding="utf-8")
    assert "LanguageBtn" in xaml


def test_language_button_injection_keeps_settings_button_indented(tmp_path: Path):
    src = tmp_path / "src"
    make_source(src)
    xaml_path = src / "RenoDXCommander" / "MainWindow.xaml"
    xaml_path.write_text('''<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n    <StackPanel>\n        <Button x:Name="SettingsBtn" Content="Settings"/>\n    </StackPanel>\n</Window>''', encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / "Localization" / "zh-CN").mkdir(parents=True)
    (repo / "Localization" / "translation-memory.json").write_text('{}', encoding="utf-8")
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text('<root/>', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "Services").mkdir(parents=True)
    (repo / "overlay" / "RenoDXCommander" / "Services" / "LocalizationService.cs").write_text('// service', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").write_text('// partial', encoding="utf-8")
    materialize(src, repo)
    out = xaml_path.read_text(encoding="utf-8")
    assert '\n        <Button x:Name="SettingsBtn"' in out


def test_manifest_text_gets_data_resource_and_shared_display_patch(tmp_path: Path):
    src = tmp_path / "src"
    make_source(src)
    (src / "manifest.json").write_text(json.dumps({"installWarnings":{"Game":{"reshade":"Close the game."}}}), encoding="utf-8")
    vm = src / "RenoDXCommander" / "ViewModels" / "MainViewModel.Install.Luma.cs"
    vm.write_text('''namespace RenoDXCommander.ViewModels; public partial class MainViewModel { void X(){ var dialog = new ContentDialog { Content = message, PrimaryButtonText = "Continue" }; } }''', encoding="utf-8")
    dlg = src / "RenoDXCommander" / "DialogService.Game.cs"
    dlg.write_text('''namespace RenoDXCommander; public partial class DialogService { private static void AddTextOrHyperlink(StackPanel panel, string text, string? url, string? urlLabel, SolidColorBrush textColour, SolidColorBrush linkColour) { } private static void AddHyperlinkBlock(StackPanel panel, string label, string url, SolidColorBrush linkColour) { } void X(){ var t = new TextBlock { Text = result.Content }; } }''', encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / "Localization" / "zh-CN").mkdir(parents=True)
    (repo / "Localization" / "translation-memory.json").write_text(json.dumps({"Close the game.":{"translation":"请先关闭游戏。","state":"reviewed"}}, ensure_ascii=False), encoding="utf-8")
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text('<root/>', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "Services").mkdir(parents=True)
    (repo / "overlay" / "RenoDXCommander" / "Services" / "LocalizationService.cs").write_text('// service', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").write_text('// partial', encoding="utf-8")
    result = materialize(src, repo)
    en = (src / "RenoDXCommander" / "Strings" / "en-US" / "Resources.resw").read_text(encoding="utf-8")
    zh = (src / "RenoDXCommander" / "Strings" / "zh-CN" / "Resources.resw").read_text(encoding="utf-8")
    assert "Close the game." in en and "请先关闭游戏。" in zh
    assert "GetDataString(message)" in vm.read_text(encoding="utf-8")
    assert "GetDataString(text)" in dlg.read_text(encoding="utf-8")


def test_language_handlers_show_restart_notice_after_saving(tmp_path: Path):
    src = tmp_path / "src"
    make_source(src)
    repo = tmp_path / "repo"
    (repo / "Localization" / "zh-CN").mkdir(parents=True)
    (repo / "Localization" / "translation-memory.json").write_text(json.dumps({
        "Language preference saved.": {"translation": "语言偏好已保存。", "state": "reviewed"},
        "Restart RHI to apply the selected interface language.": {"translation": "请重启 RHI 以应用所选界面语言。", "state": "reviewed"},
        "OK": {"translation": "确定", "state": "reviewed"},
    }, ensure_ascii=False), encoding="utf-8")
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text('<root/>', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "Services").mkdir(parents=True)
    (repo / "overlay" / "RenoDXCommander" / "Services" / "LocalizationService.cs").write_text(
        (Path(__file__).resolve().parents[1] / "overlay" / "RenoDXCommander" / "Services" / "LocalizationService.cs").read_text(encoding="utf-8"), encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").write_text(
        (Path(__file__).resolve().parents[1] / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").read_text(encoding="utf-8"), encoding="utf-8")
    materialize(src, repo)
    code = (src / "RenoDXCommander" / "MainWindow.Localization.cs").read_text(encoding="utf-8")
    zh = (src / "RenoDXCommander" / "Strings" / "zh-CN" / "Resources.resw").read_text(encoding="utf-8")
    assert "ContentDialog" in code
    assert "ShowSafeAsync" in code
    assert "语言偏好已保存。" in zh
    assert "请重启 RHI 以应用所选界面语言。" in zh


def test_materialize_uses_reviewed_translation_shards(tmp_path: Path):
    src = tmp_path / "src"
    make_source(src)
    repo = tmp_path / "repo"
    (repo / "Localization" / "zh-CN").mkdir(parents=True)
    (repo / "Localization" / "reviewed").mkdir(parents=True)
    (repo / "Localization" / "translation-memory.json").write_text('{}', encoding="utf-8")
    (repo / "Localization" / "reviewed" / "ui.json").write_text(json.dumps({
        "Settings": {"translation": "设置（分片）", "state": "reviewed"}
    }, ensure_ascii=False), encoding="utf-8")
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text('<root/>', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "Services").mkdir(parents=True)
    (repo / "overlay" / "RenoDXCommander" / "Services" / "LocalizationService.cs").write_text('// service', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").write_text('// partial', encoding="utf-8")

    materialize(src, repo)
    zh = (src / "RenoDXCommander" / "Strings" / "zh-CN" / "Resources.resw").read_text(encoding="utf-8")
    assert "设置（分片）" in zh
