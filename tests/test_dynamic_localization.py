from pathlib import Path
import hashlib
import json

from tools.materialize import materialize


def _make_source(root: Path, *, with_dynamic_ui: bool = False) -> Path:
    project = root / "RenoDXCommander"
    (project / "Services").mkdir(parents=True)
    (project / "ViewModels").mkdir(parents=True)
    (project / "RenoDXCommander.csproj").write_text(
        '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <AssemblyVersion>2.6.9.0</AssemblyVersion>
    <FileVersion>2.6.9.0</FileVersion>
  </PropertyGroup>
  <ItemGroup><PackageReference Include="SharpCompress" Version="1" /></ItemGroup>
</Project>''', encoding="utf-8")
    (project / "App.xaml.cs").write_text(
        '''namespace RenoDXCommander; public partial class App { protected override void OnLaunched(LaunchActivatedEventArgs args) { DownloadsMigrationService.RunOnce(); } }''',
        encoding="utf-8")
    (project / "App.xaml").write_text(
        '''<Application x:Class="RenoDXCommander.App" xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><Application.Resources><ResourceDictionary /></Application.Resources></Application>''',
        encoding="utf-8")
    (project / "MainWindow.xaml").write_text(
        '''<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><StackPanel><Button x:Name="SettingsBtn" Content="Settings"/></StackPanel></Window>''',
        encoding="utf-8")
    (project / "DetailPanelBuilder.cs").write_text(
        '''namespace RenoDXCommander; public class X { void A() { var t = new TextBlock { Text = "Install" }; } }''',
        encoding="utf-8")
    if with_dynamic_ui:
        (project / "MainWindow.FaqBuilder.cs").write_text(
            '''namespace RenoDXCommander; public partial class MainWindow { void X(string title, string description, string? tip, string bullet) { var a = new TextBlock { Text = title }; var b = new TextBlock { Text = description }; var c = new TextBlock { Text = tip }; var d = new TextBlock { Text = $"• {bullet}" }; } }''',
            encoding="utf-8")
        (project / "UIFactory.cs").write_text(
            '''namespace RenoDXCommander; public static class UIFactory { static TextBlock MakeLabel(string text) => new TextBlock { Text = text }; static Button MakeActionButton(string content) => new Button { Content = content }; }''',
            encoding="utf-8")
        (project / "ViewModels" / "MainViewModel.cs").write_text(
            '''namespace RenoDXCommander.ViewModels; public class MainViewModel { public string LayoutToggleLabel => Current ? "Detail View" : "Simple View"; bool Current => true; }''',
            encoding="utf-8")
        (project / "DetailPanelBuilder.Components.cs").write_text(
            '''namespace RenoDXCommander; public partial class DetailPanelBuilder { static object WithInfoArrow(string label, bool hasInfo) { return label; } }''',
            encoding="utf-8")
    return project


def _make_repo(root: Path, memory: dict | None = None) -> Path:
    repo = root / "repo"
    (repo / "Localization" / "zh-CN").mkdir(parents=True)
    (repo / "Localization" / "translation-memory.json").write_text(
        json.dumps(memory or {}, ensure_ascii=False), encoding="utf-8")
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text('<root/>', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "Services").mkdir(parents=True)
    source_repo = Path(__file__).resolve().parents[1]
    for rel in ("Services/LocalizationService.cs", "MainWindow.Localization.cs"):
        src = source_repo / "overlay" / "RenoDXCommander" / rel
        dst = repo / "overlay" / "RenoDXCommander" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return repo


def test_formal_release_version_overrides_stale_upstream_assembly_version(tmp_path: Path):
    src = tmp_path / "src"
    project = _make_source(src)
    repo = _make_repo(tmp_path)
    materialize(src, repo, release_version="2.7.0")
    csproj = (project / "RenoDXCommander.csproj").read_text(encoding="utf-8")
    assert '<AssemblyVersion>2.7.0.0</AssemblyVersion>' in csproj
    assert '<FileVersion>2.7.0.0</FileVersion>' in csproj


def test_reviewed_dynamic_source_is_emitted_as_data_resource(tmp_path: Path):
    src = tmp_path / "src"
    project = _make_source(src)
    source = "Detail View"
    translation = "详细视图"
    repo = _make_repo(tmp_path, {
        source: {"translation": translation, "state": "reviewed", "source_hash": hashlib.sha256(source.encode()).hexdigest()}
    })
    materialize(src, repo)
    en = (project / "Strings" / "en-US" / "Resources.resw").read_text(encoding="utf-8")
    zh = (project / "Strings" / "zh-CN" / "Resources.resw").read_text(encoding="utf-8")
    data_key = "Data_" + hashlib.sha256(source.encode()).hexdigest()[:16]
    assert data_key in en and source in en
    assert data_key in zh and translation in zh


def test_language_button_uid_is_applied_after_localizable_content(tmp_path: Path):
    src = tmp_path / "src"
    project = _make_source(src)
    repo = _make_repo(tmp_path, {
        "Settings": {"translation": "设置", "state": "reviewed"},
        "Language": {"translation": "语言", "state": "reviewed"},
        "System": {"translation": "跟随系统", "state": "reviewed"},
    })
    materialize(src, repo)
    xaml = (project / "MainWindow.xaml").read_text(encoding="utf-8")
    start = xaml.index('<Button x:Name="LanguageBtn"')
    end = xaml.index('>', start)
    tag = xaml[start:end]
    assert 'Content="Language"' in tag
    assert 'l:Uids.Uid=' in tag
    assert tag.index('Content="Language"') < tag.index('l:Uids.Uid=')


def test_dynamic_ui_display_boundaries_use_data_localization(tmp_path: Path):
    src = tmp_path / "src"
    project = _make_source(src, with_dynamic_ui=True)
    repo = _make_repo(tmp_path)
    materialize(src, repo)
    faq = (project / "MainWindow.FaqBuilder.cs").read_text(encoding="utf-8")
    factory = (project / "UIFactory.cs").read_text(encoding="utf-8")
    vm = (project / "ViewModels" / "MainViewModel.cs").read_text(encoding="utf-8")
    components = (project / "DetailPanelBuilder.Components.cs").read_text(encoding="utf-8")
    assert "LocalizationService.GetDataString(title)" in faq
    assert "LocalizationService.GetDataString(description)" in faq
    assert "LocalizationService.GetDataString(tip)" in faq
    assert "LocalizationService.GetDataString(bullet)" in faq
    assert "LocalizationService.GetDataString(text)" in factory
    assert "LocalizationService.GetDataString(content)" in factory
    assert 'LocalizationService.GetDataString("Detail View")' in vm
    assert 'LocalizationService.GetDataString("Simple View")' in vm
    assert "label = LocalizationService.GetDataString(label);" in components


def test_app_resources_define_localized_combobox_item_template(tmp_path: Path):
    src = tmp_path / "src"
    project = _make_source(src)
    repo = _make_repo(tmp_path)
    materialize(src, repo)
    app_xaml = (project / "App.xaml").read_text(encoding="utf-8")
    assert "LocalizedStringConverter" in app_xaml
    assert 'x:Key="LocalizedComboBoxItemTemplate"' in app_xaml


def test_app_resources_keep_merged_dictionaries_before_resource_items(tmp_path: Path):
    src = tmp_path / "src"
    project = _make_source(src)
    (project / "App.xaml").write_text(
        '''<?xml version="1.0" encoding="utf-8"?>
<Application x:Class="RenoDXCommander.App"
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <Application.Resources>
        <ResourceDictionary>
            <ResourceDictionary.MergedDictionaries>
                <ResourceDictionary Source="Themes/DarkTheme.xaml"/>
            </ResourceDictionary.MergedDictionaries>
            <Color x:Key="ExistingColor">#FF000000</Color>
        </ResourceDictionary>
    </Application.Resources>
</Application>''', encoding="utf-8")
    repo = _make_repo(tmp_path)
    materialize(src, repo)
    app_xaml = (project / "App.xaml").read_text(encoding="utf-8")
    merged_end = app_xaml.index('</ResourceDictionary.MergedDictionaries>')
    converter = app_xaml.index('<services:LocalizedStringConverter')
    assert merged_end < converter
