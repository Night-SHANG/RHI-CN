from tools.transform import transform_csharp, scan_csharp_unhandled


def test_localizes_simple_ui_property_literal():
    src = 'var t = new TextBlock { Text = "Hello" };'
    out, entries = transform_csharp(src, "DetailPanelBuilder.cs")
    assert "LocalizationService.GetString" in out
    assert list(entries.values()) == ["Hello"]


def test_does_not_rewrite_non_ui_file():
    src = 'var x = new Thing { Content = "payload" };'
    out, entries = transform_csharp(src, "Services/NetworkService.cs")
    assert out == src
    assert entries == {}


def test_reports_interpolated_ui_strings_without_guessing():
    src = 'SetStatus($"Installed {count} items");'
    findings = scan_csharp_unhandled(src, "MainWindow.Events.cs")
    assert any("Installed" in f["text"] for f in findings)


def test_preserves_unicode_when_decoding_csharp_escapes():
    src = 'var x = new TextBlock { Text = "Power Mode — everything\\nNext line" };'
    out, entries = transform_csharp(src, "DetailPanelBuilder.cs")
    assert "â" not in next(iter(entries.values()))
    assert next(iter(entries.values())) == "Power Mode — everything\nNext line"


def test_localizes_interpolated_ui_property_with_format_arguments():
    src = 'var t = new TextBlock { Text = $"Peak Brightness: {peak} nits" };'
    out, entries = transform_csharp(src, "MainWindow.Events.Components.cs")
    assert 'LocalizationService.Format(' in out
    assert '$"{peak}"' in out
    assert list(entries.values()) == ["Peak Brightness: {0} nits"]
    assert scan_csharp_unhandled(out, "MainWindow.Events.Components.cs") == []


def test_localizes_interpolated_call_and_preserves_inner_ternary_expression():
    src = 'SetStatus($"Updated {count} file{(count == 1 ? "" : "s")}");'
    out, entries = transform_csharp(src, "SettingsHandler.cs")
    assert 'LocalizationService.Format(' in out
    assert '$"{count}"' in out
    assert '$"{(count == 1 ? "" : "s")}"' in out
    assert list(entries.values()) == ["Updated {0} file{1}"]


def test_does_not_resourceize_interpolation_with_no_translatable_literal():
    src = 'var t = new TextBlock { Text = $"{currentLevel}%" };'
    out, entries = transform_csharp(src, "MainWindow.Events.Settings.cs")
    assert out == src
    assert entries == {}
    assert scan_csharp_unhandled(src, "MainWindow.Events.Settings.cs") == []
