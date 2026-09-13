import json
from pathlib import Path
from tools.materialize import materialize


def make_source(root: Path):
    p=root/'RenoDXCommander'; (p/'Services').mkdir(parents=True); (p/'ViewModels').mkdir(parents=True)
    (p/'RenoDXCommander.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><ItemGroup><PackageReference Include="SharpCompress" Version="1" /></ItemGroup></Project>',encoding='utf-8')
    (p/'App.xaml.cs').write_text('namespace RenoDXCommander; public partial class App { protected override void OnLaunched(LaunchActivatedEventArgs args) { DownloadsMigrationService.RunOnce(); } }',encoding='utf-8')
    (p/'MainWindow.xaml').write_text('<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><StackPanel><Button x:Name="SettingsBtn" Content="Settings"/></StackPanel></Window>',encoding='utf-8')
    (p/'DetailPanelBuilder.cs').write_text('namespace RenoDXCommander; public class X { void A(){ var t = new TextBlock { Text = "Install" }; } }',encoding='utf-8')


def make_repo(root: Path):
    (root/'Localization'/'zh-CN').mkdir(parents=True)
    (root/'Localization'/'translation-memory.json').write_text(json.dumps({"Settings":{"translation":"设置","state":"reviewed"},"Install":{"translation":"安装","state":"reviewed"}},ensure_ascii=False),encoding='utf-8')
    (root/'Localization'/'zh-CN'/'Resources.resw').write_text('<root/>',encoding='utf-8')
    (root/'overlay'/'RenoDXCommander'/'Services').mkdir(parents=True)
    (root/'overlay'/'RenoDXCommander'/'Services'/'LocalizationService.cs').write_text('// service',encoding='utf-8')
    (root/'overlay'/'RenoDXCommander'/'MainWindow.Localization.cs').write_text('// partial',encoding='utf-8')


def test_materialize_creates_complete_resources_and_overlay(tmp_path):
    src=tmp_path/'src'; repo=tmp_path/'repo'; make_source(src); make_repo(repo)
    result=materialize(src,repo)
    assert result['english_keys'] >= 2
    assert (src/'RenoDXCommander'/'Strings'/'en-US'/'Resources.resw').exists()
    assert (src/'RenoDXCommander'/'Strings'/'zh-CN'/'Resources.resw').exists()
    assert 'WinUI3Localizer' in (src/'RenoDXCommander'/'RenoDXCommander.csproj').read_text(encoding='utf-8')
    assert 'LocalizationService.InitializeAsync' in (src/'RenoDXCommander'/'App.xaml.cs').read_text(encoding='utf-8')
    assert 'LanguageBtn' in (src/'RenoDXCommander'/'MainWindow.xaml').read_text(encoding='utf-8')


def test_manifest_visible_text_gets_resource_key(tmp_path):
    src=tmp_path/'src'; repo=tmp_path/'repo'; make_source(src); make_repo(repo)
    (src/'manifest.json').write_text(json.dumps({"installWarnings":{"Game":{"reshade":"Close the game."}}}),encoding='utf-8')
    materialize(src,repo)
    en=(src/'RenoDXCommander'/'Strings'/'en-US'/'Resources.resw').read_text(encoding='utf-8')
    assert 'Close the game.' in en and 'Data_' in en
