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


def test_ternary_tooltip_localizes_interpolated_false_branch_without_invalid_dollar_prefix():
    src = '''ToolTipService.SetToolTip(toggle, rtx40MfgConflict
        ? "RTX 40 MFG Unlock is already installed."
        : $"Disable {mutualExclusivePeer} first to enable this addon.");'''
    out, entries = transform_csharp(src, "AddonPopupHelper.cs")
    assert out.count("ToolTipService.SetToolTip") == 1
    assert "$RenoDXCommander.Services.LocalizationService" not in out
    assert "LocalizationService.Format" in out
    assert "LocalizationService.GetString" in out
    assert '$"{mutualExclusivePeer}"' in out
    assert "RTX 40 MFG Unlock is already installed." in entries.values()
    assert "Disable {0} first to enable this addon." in entries.values()


def test_ternary_tooltip_localizes_interpolated_true_branch_without_invalid_dollar_prefix():
    src = '''ToolTipService.SetToolTip(installBtn, isInstalled
        ? $"Reinstall Ultimate ASI Loader (currently '{installedAs}')"
        : "Install Ultimate ASI Loader — choose which DLL name to use");'''
    out, entries = transform_csharp(src, "DetailPanelBuilder.Extras.cs")
    assert out.count("ToolTipService.SetToolTip") == 1
    assert "$RenoDXCommander.Services.LocalizationService" not in out
    assert "LocalizationService.Format" in out
    assert "LocalizationService.GetString" in out
    assert '$"{installedAs}"' in out
    assert "Reinstall Ultimate ASI Loader (currently '{0}')" in entries.values()
    assert "Install Ultimate ASI Loader — choose which DLL name to use" in entries.values()


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


def test_compact_cog_help_is_localized_at_display_boundary():
    for path, expr in [("CogDialog.cs", "help"),
                       ("MainWindow.Events.Components.OptiScaler.cs", "cell.Help"),
                       ("MainWindow.Events.Components.Rdx.cs", "cell.Help")]:
        out, _ = transform_csharp(f'ToolTipService.SetToolTip(label, {expr});', path)
        assert f'LocalizationService.GetDataString({expr})' in out


def test_compact_cog_literals_collected_without_changing_ini_logic():
    src = '''var c = OsComboCell(cog, "FG Enabled", "Turns FG on. " + "Auto leaves it off.", items, 0, f);
var r = new RdxCompatCell("Mode", "Saved in INI.", items, 0, f);
var o = new OsCell("Version", "Choose a version.", combo);
var technical = ReadIni("FrameGen", "Enabled", "false");'''
    out, entries = transform_csharp(src, "MainWindow.Events.Components.OptiScaler.cs")
    assert out == src
    assert {'FG Enabled', 'Turns FG on. Auto leaves it off.', 'Mode', 'Saved in INI.', 'Version', 'Choose a version.'} <= set(entries.values())
    assert 'FrameGen' not in entries.values()


def test_cog_combo_sources_and_header_display():
    src = 'cog.AddCombo("Variant", "Choose variant.", items, 0, f); cog.AddSection("Advanced"); var t = new TextBlock { Text = header };'
    out, entries = transform_csharp(src, 'CogDialog.cs')
    assert {'Variant', 'Choose variant.', 'Advanced'} <= set(entries.values())
    assert 'GetDataString(header)' in out


def test_target_typed_cog_combo_preserves_values_and_localizes_display():
    src = 'public static ComboBox MakeCombo(IList<string> items, int selectedIndex, bool isEnabled = true) => new() { ItemsSource = items, SelectedIndex = selectedIndex };'
    out, _ = transform_csharp(src, 'CogDialog.cs')
    assert 'ItemTemplate = RenoDXCommander.Services.LocalizationService.ComboBoxItemTemplate' in out
    assert 'ItemsSource = items' in out


def test_settings_search_count_formats_are_localized():
    src = 'string countText = matches.Count switch { 0 => $"No settings match \\"{q}\\"", 1 => $"1 setting matches \\"{q}\\"", _ => $"{matches.Count} settings match \\"{q}\\"" }; countText += $". Showing the first {MaxSearchResults}; keep typing to narrow it down.";'
    out, entries = transform_csharp(src, 'SettingsHandler.Navigation.cs')
    assert out.count('LocalizationService.Format') == 4
    assert 'No settings match "{0}"' in entries.values()


def test_cog_string_buttons_are_localized_but_elements_are_not():
    src = 'Content = text; Content = content; Title = _title; CloseButtonText = _closeText; dlg.PrimaryButtonText = _primaryText;'
    out, _ = transform_csharp(src, 'CogDialog.cs')
    assert 'Content = content' in out
    for value in ('text', '_title', '_closeText', '_primaryText'):
        assert f'GetDataString({value})' in out


def test_accessibility_name_is_localized():
    src = 'Microsoft.UI.Xaml.Automation.AutomationProperties.SetName(_searchBox, "Find a setting");'
    out, entries = transform_csharp(src, 'SettingsHandler.Navigation.cs')
    assert 'AutomationProperties.SetName(_searchBox, RenoDXCommander.Services.LocalizationService.GetString(' in out
    assert list(entries.values()) == ['Find a setting']


def test_new_faq_literals_are_collected_without_translating_brush_keys():
    src = 'private void BuildFaqContent() { BuildFaqSection(null, "Welcome", "AccentTealBrush", "New guide."); } private void Helper() {}'
    out, entries = transform_csharp(src, 'MainWindow.FaqBuilder.cs')
    assert {'Welcome', 'New guide.'} <= set(entries.values())
    assert 'AccentTealBrush' not in entries.values()
    assert out == src


def test_countdown_return_values_localized_with_english_fallback():
    src = 'if (last == null) return "Not yet"; return $"{ago.Minutes:00}m ago";'
    out, entries = transform_csharp(src, 'SettingsHandler.UpdateCountdown.cs')
    assert 'LocalizationService.GetString' in out
    assert 'LocalizationService.Format' in out
    assert 'Not yet' in entries.values()
    assert '$"{ago.Minutes:00}"' in out


def test_cog_editable_text_remains_untranslated():
    src = 'public static TextBox MakeTextBox(string text = "", string? placeholder = null) => new() { Text = text, PlaceholderText = placeholder ?? "" };'
    out, _ = transform_csharp(src, 'CogDialog.cs')
    assert 'Text = text,' in out
    assert 'GetDataString(placeholder)' in out


def test_dynamic_cog_title_localizes_suffix_not_stored_title():
    out, entries = transform_csharp('Title = _title,', 'CogDialog.cs')
    assert '_title[..^9]' in out
    assert '{0} Settings' in entries.values()


def test_compatibility_help_formats_preserve_ini_key_argument():
    out, entries = transform_csharp('var help = $"Saved as {setting.Key} in reshade.ini.";', 'MainWindow.Events.Components.Rdx.cs')
    assert 'LocalizationService.Format' in out
    assert 'Saved as {0} in reshade.ini.' in entries.values()
    assert '$"{setting.Key}"' in out
