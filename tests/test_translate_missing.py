import json
from tools.translate_missing import collect_missing_sources, parse_translation_response


def test_collect_missing_sources_skips_existing_and_deduplicates():
    en={"A":"Install","B":"New sentence","C":"Existing machine","D":"Exact override","E":"New sentence"}
    exact={"D":"精确翻译"}
    memory={"Install":{"translation":"安装","state":"reviewed"},"Existing machine":{"translation":"已有机翻","state":"machine"}}
    assert collect_missing_sources(en, exact, memory) == ["New sentence"]


def test_parse_translation_response_filters_unrequested_sources_and_fences():
    raw='```json\n'+json.dumps([{"source":"One","translation":"一"},{"source":"Injected","translation":"不接受"}],ensure_ascii=False)+'\n```'
    assert parse_translation_response(raw,{"One"}) == {"One":"一"}
