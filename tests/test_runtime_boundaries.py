from pathlib import Path
from tools.transform import transform_csharp


def test_dynamic_info_content_is_localized_at_text_display_boundary():
    src = 'var block = new TextBlock { Text = result.Content };'
    out, entries = transform_csharp(src, "DialogService.Game.cs")
    assert "LocalizationService.GetDataString(result.Content)" in out
    assert entries == {}


def test_missing_localizer_key_uses_english_fallback():
    # Windows CI exposed Localizer returning its key rather than empty/throwing
    # before resource initialization (seven upstream countdown tests failed).
    source = (Path(__file__).parents[1] / 'overlay/RenoDXCommander/Services/LocalizationService.cs').read_text(encoding='utf-8')
    assert 'string.Equals(value, key, StringComparison.Ordinal)' in source
    assert '? fallback : value' in source
