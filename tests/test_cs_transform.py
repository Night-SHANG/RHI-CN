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


def test_localizes_toggle_switch_on_and_off_content_literals():
    src = 'var t = new ToggleSwitch { OnContent = "Custom filenames enabled", OffContent = "Override DLL filenames" };'
    out, entries = transform_csharp(src, "DetailPanelBuilder.Overrides.cs")
    assert out.count("LocalizationService.GetString") == 2
    assert set(entries.values()) == {"Custom filenames enabled", "Override DLL filenames"}


def test_localizes_tooltip_service_literal_second_argument():
    src = 'ToolTipService.SetToolTip(toggle, "Override the filenames ReShade is installed as.");'
    out, entries = transform_csharp(src, "DetailPanelBuilder.Overrides.cs")
    assert "ToolTipService.SetToolTip(toggle, RenoDXCommander.Services.LocalizationService.GetString" in out
    assert list(entries.values()) == ["Override the filenames ReShade is installed as."]


def test_programmatic_combobox_uses_localized_display_template_without_changing_values():
    src = 'var combo = new ComboBox { ItemsSource = new[] { "Global", "Select", "Off" }, SelectedItem = "Global" };'
    out, _ = transform_csharp(src, "DetailPanelBuilder.Overrides.ShadersAddons.cs")
    assert "ItemTemplate = RenoDXCommander.Services.LocalizationService.ComboBoxItemTemplate" in out
    assert 'ItemsSource = new[] { "Global", "Select", "Off" }' in out
    assert 'SelectedItem = "Global"' in out


def test_update_inclusion_helper_is_treated_as_ui_code():
    src = 'var button = new Button { Content = "Update Inclusion" };'
    out, entries = transform_csharp(src, "UpdateInclusionHelper.cs")
    assert "LocalizationService.GetString" in out
    assert list(entries.values()) == ["Update Inclusion"]


def test_localizes_ternary_ui_property_literals_without_changing_condition():
    src = 'var button = new Button { Content = isInstalled ? "↺  Reinstall ASI Loader" : "⬇  Install ASI Loader" };'
    out, entries = transform_csharp(src, "DetailPanelBuilder.Extras.cs")
    assert 'Content = isInstalled ?' in out
    assert out.count("LocalizationService.GetString") == 2
    assert set(entries.values()) == {"↺  Reinstall ASI Loader", "⬇  Install ASI Loader"}


def test_localizes_concatenated_literal_ui_text_as_one_resource():
    src = '''var text = new TextBlock
    {
        Text = "Press Backspace in-game to open the RTX 40 MFG menu.\\n\\n" +
               "• Follow game — uses the game's own MFG setting\\n" +
               "• Fixed 2x–6x — forces a specific multiplier\\n" +
               "• Dynamic — targets the display refresh rate or a custom FPS value\\n\\n" +
               "If frames freeze above 2x, try setting Frame Generation to Preset B in the NVIDIA App."
    };'''
    out, entries = transform_csharp(src, "DetailPanelBuilder.Extras.cs")
    assert out.count("LocalizationService.GetString") == 1
    combined = next(iter(entries.values()))
    assert "Follow game" in combined
    assert "Preset B" in combined
    assert " +\n" not in out
