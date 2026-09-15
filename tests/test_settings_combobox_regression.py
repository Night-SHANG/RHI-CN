from pathlib import Path
import json

from tools.materialize import materialize


def _make_repo(repo: Path) -> None:
    (repo / "Localization" / "zh-CN").mkdir(parents=True)
    (repo / "Localization" / "translation-memory.json").write_text("{}", encoding="utf-8")
    (repo / "Localization" / "zh-CN" / "Resources.resw").write_text("<root/>", encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "Services").mkdir(parents=True)
    (repo / "overlay" / "RenoDXCommander" / "Services" / "LocalizationService.cs").write_text("// service", encoding="utf-8")
    (repo / "overlay" / "RenoDXCommander" / "MainWindow.Localization.cs").write_text("// partial", encoding="utf-8")


def test_materialize_skips_localized_item_template_for_code_display_member_path(tmp_path: Path):
    src = tmp_path / "src"
    project = src / "RenoDXCommander"
    project.mkdir(parents=True)
    (project / "RenoDXCommander.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup><PackageReference Include="SharpCompress" Version="1" /></ItemGroup></Project>',
        encoding="utf-8",
    )
    (project / "App.xaml.cs").write_text(
        'namespace RenoDXCommander; public partial class App { protected override void OnLaunched(LaunchActivatedEventArgs args) { DownloadsMigrationService.RunOnce(); } }',
        encoding="utf-8",
    )
    (project / "MainWindow.xaml").write_text(
        '''<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
<StackPanel>
<Button x:Name="SettingsBtn" Content="Settings"/>
<ComboBox x:Name="ResolutionTargetCombo"/>
<ComboBox x:Name="ColorDisplayCombo"/>
<ComboBox x:Name="ShaderCacheSizeCombo"/>
</StackPanel>
</Window>''',
        encoding="utf-8",
    )
    (project / "SettingsHandler.cs").write_text(
        '''namespace RenoDXCommander; public class SettingsHandler { void Open() {
_window.ResolutionTargetCombo.DisplayMemberPath = "Label";
_window.ColorDisplayCombo.DisplayMemberPath = "Name";
} }''',
        encoding="utf-8",
    )

    repo = tmp_path / "repo"
    _make_repo(repo)
    materialize(src, repo)

    xaml = (project / "MainWindow.xaml").read_text(encoding="utf-8")
    resolution_attrs = xaml.split('<ComboBox x:Name="ResolutionTargetCombo"', 1)[1].split('>', 1)[0]
    colour_attrs = xaml.split('<ComboBox x:Name="ColorDisplayCombo"', 1)[1].split('>', 1)[0]
    shader_attrs = xaml.split('<ComboBox x:Name="ShaderCacheSizeCombo"', 1)[1].split('>', 1)[0]

    assert "ItemTemplate=" not in resolution_attrs
    assert "ItemTemplate=" not in colour_attrs
    assert 'ItemTemplate="{StaticResource LocalizedComboBoxItemTemplate}"' in shader_attrs
