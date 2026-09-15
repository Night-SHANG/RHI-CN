from tools.check_localization import evaluate_report, should_fail


def test_empty_resources_are_zero_percent():
    assert evaluate_report({}, {}, [], [], [], [])["coverage_percent"] == 0.0


def test_new_unhandled_is_detected_and_strict_fails():
    current = [{"file":"A.cs","text":"New {x}","kind":"interpolated"}]
    result = evaluate_report({"A":"Hello"},{"A":"你好"},[],current,[],[])
    result["new_manifest_visible_text"] = []
    assert len(result["new_unhandled_csharp"]) == 1
    assert should_fail(result, True)


def test_new_manifest_text_alone_does_not_fail():
    result = {"missing_zh_keys":[],"stale_reviewed_sources":[],"new_unhandled_csharp":[],"new_manifest_visible_text":["New note"]}
    assert not should_fail(result, True)


def test_no_fallback_mode_fails_when_any_english_fallback_remains():
    result = {
        "missing_zh_keys": [],
        "stale_reviewed_sources": [],
        "new_unhandled_csharp": [],
        "new_manifest_visible_text": [],
        "fallback_keys": ["CS_deadbeef"],
    }
    assert should_fail(result, True, no_fallback=True)


def test_no_fallback_mode_passes_when_coverage_is_complete():
    result = {
        "missing_zh_keys": [],
        "stale_reviewed_sources": [],
        "new_unhandled_csharp": [],
        "new_manifest_visible_text": [],
        "fallback_keys": [],
    }
    assert not should_fail(result, True, no_fallback=True)
