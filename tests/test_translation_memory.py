from tools.translation_memory import merge_machine_translations, stale_reviewed_entries


def test_reviewed_translation_is_never_overwritten():
    memory = {"Refresh":{"translation":"刷新","state":"reviewed"}}
    merged = merge_machine_translations(memory, {"Refresh":"重新整理","New":"新建"})
    assert merged["Refresh"]["translation"] == "刷新"
    assert merged["New"]["state"] == "machine"


def test_changed_reviewed_source_is_reported_by_hash():
    assert stale_reviewed_entries({"Old":{"translation":"旧","state":"reviewed","source_hash":"bad"}}) == ["Old"]
