from tools.translation_memory import merge_machine_translations, stale_reviewed_entries


def test_reviewed_translation_is_never_overwritten():
    memory = {"Refresh": {"translation": "刷新", "state": "reviewed"}}
    merged = merge_machine_translations(memory, {"Refresh": "重新整理", "New": "新建"})
    assert merged["Refresh"]["translation"] == "刷新"
    assert merged["Refresh"]["state"] == "reviewed"
    assert merged["New"]["translation"] == "新建"
    assert merged["New"]["state"] == "machine"


def test_changed_reviewed_source_is_reported_by_hash():
    memory = {
        "Old": {"translation": "旧", "state": "reviewed", "source_hash": "bad"}
    }
    assert stale_reviewed_entries(memory) == ["Old"]


def test_translation_memory_loads_reviewed_shards_and_fails_on_conflict(tmp_path):
    import json
    import pytest
    from tools.translation_memory import load_translation_memory

    loc = tmp_path / "Localization"
    reviewed = loc / "reviewed"
    reviewed.mkdir(parents=True)
    (loc / "translation-memory.json").write_text(json.dumps({
        "Base": {"translation": "基础", "state": "reviewed"},
        "Pending": {"translation": "旧机器翻译", "state": "machine"},
    }, ensure_ascii=False), encoding="utf-8")
    (reviewed / "xaml.json").write_text(json.dumps({
        "Pending": {"translation": "已审核", "state": "reviewed"},
        "New": {"translation": "新增", "state": "reviewed"},
    }, ensure_ascii=False), encoding="utf-8")

    merged = load_translation_memory(loc)
    assert merged["Base"]["translation"] == "基础"
    assert merged["Pending"]["translation"] == "已审核"
    assert merged["New"]["translation"] == "新增"

    (reviewed / "conflict.json").write_text(json.dumps({
        "Base": {"translation": "冲突", "state": "reviewed"}
    }, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Conflicting reviewed translation"):
        load_translation_memory(loc)
