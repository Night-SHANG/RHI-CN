from pathlib import Path
from tools.materialize import materialize
from tools.resw import read_resw


def _make_source(root: Path) -> None:
    project = root / "RenoDXCommander"
    (project / "Services").mkdir(parents=True)
    (project / "RenoDXCommander.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup><PackageReference Include="SharpCompress" Version="1" /></ItemGroup></Project>',
        encoding="utf-8",
    )
    (project / "App.xaml.cs").write_text(
        'namespace RenoDXCommander; public partial class App { protected override void OnLaunched(LaunchActivatedEventArgs args) { DownloadsMigrationService.RunOnce(); } }',
        encoding="utf-8",
    )
    (project / "MainWindow.xaml").write_text(
        '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><Button x:Name="SettingsBtn" Content="Settings"/></Window>',
        encoding="utf-8",
    )
    (project / "DetailPanelBuilder.cs").write_text(
        'namespace RenoDXCommander; public class X { void A() { var t = new TextBlock { Text = $"Installed: {version}" }; } }',
        encoding="utf-8",
    )


def test_materialize_scans_transformed_csharp_for_unhandled_text(tmp_path: Path):
    source = tmp_path / "source"
    _make_source(source)
    repo = tmp_path / "repo"
    (repo / "Localization" / "zh-CN").mkdir(parents=True)
    (repo / "Localization" / "translation-memory.json").write_text('{}', encoding="utf-8")
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text('<root/>', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "Services").mkdir(parents=True)
    (repo / "overlay" / "RenoDXCommander" / "Services" / "LocalizationService.cs").write_text('// service', encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").write_text('// partial', encoding="utf-8")

    result = materialize(source, repo)

    assert result["unhandled_csharp"] == []
    english = read_resw(source / "RenoDXCommander" / "Strings" / "en-US" / "Resources.resw")
    assert "Installed: {0}" in english.values()
