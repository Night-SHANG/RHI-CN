from tools.transform import transform_csharp


def test_shader_popup_tooltip_literal_is_localized():
    src = 'ToolTipService.SetToolTip(saveBtn, "Save the current shader selection.");'
    out, entries = transform_csharp(src, "ShaderPopupHelper.cs")
    assert "LocalizationService.GetString" in out
    assert list(entries.values()) == ["Save the current shader selection."]


def test_dynamic_tooltip_is_localized_only_at_display_boundary():
    src = 'ToolTipService.SetToolTip(dxvkModeCombo, card.DxvkToggleTooltip);'
    out, entries = transform_csharp(src, "DetailPanelBuilder.Overrides.Dxvk.cs")
    assert "LocalizationService.GetDataString(card.DxvkToggleTooltip)" in out
    assert entries == {}


def test_concatenated_tooltip_literals_become_one_resource():
    src = 'ToolTipService.SetToolTip(combo, "First line. " + "Second line.");'
    out, entries = transform_csharp(src, "MainWindow.Events.cs")
    assert out.count("LocalizationService.GetString") == 1
    assert list(entries.values()) == ["First line. Second line."]


# Regression guard for R4: interpolated hover text must be localized without
# changing the runtime value that is inserted into the tooltip.
def test_interpolated_tooltip_uses_localized_format_without_changing_argument():
    src = 'ToolTipService.SetToolTip(button, $"Installed as: {currentDllName}\\nClick to open GitHub releases");'
    out, entries = transform_csharp(src, "DetailPanelBuilder.Extras.cs")
    assert "LocalizationService.Format" in out
    assert '$"{currentDllName}"' in out
    assert list(entries.values()) == ["Installed as: {0}\nClick to open GitHub releases"]


def test_tooltip_source_property_is_collected_without_changing_program_value():
    src = 'card.DxvkToggleTooltip = "DXVK is unavailable for this game.";'
    out, entries = transform_csharp(src, "Models/GameCard.cs")
    assert out == src
    assert "DXVK is unavailable for this game." in entries.values()
    assert any(key.startswith("Data_") for key in entries)


def test_driver_option_array_display_names_are_collected_as_runtime_data():
    src = '''public static readonly (string Name, uint Value)[] PowerManagementOptions =
    [
        ("Optimal Performance", 0x00000005),
        ("Adaptive", 0x00000000),
        ("Maximum Performance", 0x00000001),
    ];'''
    out, entries = transform_csharp(src, "Services/DlssPresetService.DriverSettings.cs")
    assert out == src
    assert {"Optimal Performance", "Adaptive", "Maximum Performance"}.issubset(set(entries.values()))
    assert all(key.startswith("Data_") for key in entries)


def test_items_add_display_string_is_collected_as_runtime_data():
    src = 'hdrCombo.Items.Add("On"); hdrCombo.Items.Add("Off");'
    out, entries = transform_csharp(src, "MainWindow.Events.cs")
    assert 'Items.Add("On")' in out and 'Items.Add("Off")' in out
    assert {"On", "Off"}.issubset(set(entries.values()))
