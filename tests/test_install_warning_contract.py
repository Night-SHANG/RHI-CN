import pytest
from tools.materialize import _patch_manifest_display


def test_hyperlink_warning_localizes_before_splitting_url(tmp_path):
    p = tmp_path / 'ViewModels/MainViewModel.Install.Luma.cs'
    p.parent.mkdir()
    p.write_text('''public async Task<bool> CheckInstallWarningAsync(string gameName, string component) {
        if (string.IsNullOrEmpty(message)) return true;
        var urlMatch = System.Text.RegularExpressions.Regex.Match(message, @"https?://\\S+$");
        var textPart = message.Substring(0, urlMatch.Index).TrimEnd();
        var url = urlMatch.Value;
        dialogContent = message;
        Content = dialogContent,
        NavigateUri = new Uri(url),
    }''')
    _patch_manifest_display(tmp_path)
    result = p.read_text()
    assert result.index('message = RenoDXCommander.Services.LocalizationService.GetDataString(message);') < result.index('Regex.Match(message')
    assert 'NavigateUri = new Uri(url)' in result
    _patch_manifest_display(tmp_path)
    assert p.read_text() == result


def test_unknown_warning_layout_still_fails_closed(tmp_path):
    p = tmp_path / 'ViewModels/MainViewModel.Install.Luma.cs'
    p.parent.mkdir()
    p.write_text('public void CheckInstallWarningAsync() { NewWarningRenderer(message); }')
    with pytest.raises(RuntimeError, match='contract changed'):
        _patch_manifest_display(tmp_path)


def test_translation_memory_preserves_trailing_warning_urls():
    import re
    from pathlib import Path
    from tools.translation_memory import load_translation_memory
    memory = load_translation_memory(Path(__file__).resolve().parents[1] / 'Localization')
    for source, item in memory.items():
        match = re.search(r'https?://\S+$', source)
        if match:
            assert item['translation'].endswith(match[0]), source
