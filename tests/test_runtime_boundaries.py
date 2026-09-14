from tools.transform import transform_csharp


def test_dynamic_info_content_is_localized_at_text_display_boundary():
    src = 'var block = new TextBlock { Text = result.Content };'
    out, entries = transform_csharp(src, "DialogService.Game.cs")
    assert "LocalizationService.GetDataString(result.Content)" in out
    assert entries == {}
