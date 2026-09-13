from tools.manifest_scan import extract_user_visible_manifest_text


def test_manifest_extracts_only_visible_fields():
    manifest = {
        "installWarnings":{"Game":{"reshade":"Close the game first."}},
        "gameNotes":{"Game":{"notes":"Use borderless mode.","notesUrl":"https://example.com","notesUrlLabel":"Guide"}},
        "dxvkGameNotes":{"Game":{"notes":"DXVK note","notesUrlLabel":"DXVK guide"}},
        "dllNameOverrides":{"Game":{"reshade":"dxgi.dll"}}
    }
    out = extract_user_visible_manifest_text(manifest)
    assert "Close the game first." in out and "Use borderless mode." in out and "Guide" in out
    assert "DXVK note" in out and "DXVK guide" in out
    assert "https://example.com" not in out and "dxgi.dll" not in out
