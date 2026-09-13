import pytest
from tools.transform import transform_xaml, transform_csharp, scan_csharp_unhandled


def test_xaml_localizes_literals_and_tooltips():
    src = '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><Button x:Name="B" Content="Refresh" ToolTipService.ToolTip="Reload data"/></Window>'
    out, entries = transform_xaml(src, "MainWindow.xaml")
    assert 'l:Uids.Uid="B"' in out
    assert entries["B.Content"] == "Refresh"
    assert entries["B.ToolTipService.ToolTip"] == "Reload data"


def test_xaml_does_not_attach_localizer_uid_to_winui_window():
    src = '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Title="RHI"><TextBlock Text="Hello"/></Window>'
    out, entries = transform_xaml(src, "MainWindow.xaml")
    window_tag = out.split(">", 1)[0]
    assert 'l:Uids.Uid=' not in window_tag
    assert not any(key.endswith(".Title") for key in entries)
    assert "Hello" in entries.values()


def test_xaml_binding_is_not_localized_and_conflicting_namespace_fails():
    src = '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><Button Content="{x:Bind ViewModel.Label}"/></Window>'
    _, entries = transform_xaml(src, "A.xaml")
    assert entries == {}
    bad = '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" xmlns:l="using:Other"><Button Content="Hello"/></Window>'
    with pytest.raises(RuntimeError):
        transform_xaml(bad, "A.xaml")


def test_csharp_is_conservative_and_reports_interpolation():
    out, entries = transform_csharp('var t = new TextBlock { Text = "Hello" };', "DetailPanelBuilder.cs")
    assert "LocalizationService.GetString" in out and list(entries.values()) == ["Hello"]
    untouched, entries = transform_csharp('var x = new Thing { Content = "payload" };', "Services/NetworkService.cs")
    assert untouched.endswith('"payload" };') and entries == {}
    findings = scan_csharp_unhandled('SetStatus($"Installed {count} items");', "MainWindow.Events.cs")
    assert findings
