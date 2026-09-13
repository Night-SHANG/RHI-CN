import json
from tools.update_state import update_state


def test_update_state_preserves_unspecified_fields_and_updates_inventory(tmp_path):
    state=tmp_path/'upstream.json'; inv=tmp_path/'Localization'/'inventory'/'main.json'; inv.parent.mkdir(parents=True)
    state.write_text(json.dumps({"upstream":"RankFTW/RHI","validated_main_commit":"old","observed_release_tag":"RHI-1.0","published_release_tag":None}),encoding='utf-8')
    inv.write_text(json.dumps({"upstream_commit":None,"unhandled_csharp":[]}),encoding='utf-8')
    update_state(state,inv,validated_main='new',observed_release='RHI-2.0',inventory_main='new')
    s=json.loads(state.read_text(encoding='utf-8')); i=json.loads(inv.read_text(encoding='utf-8'))
    assert s['validated_main_commit']=='new' and s['published_release_tag'] is None and i['upstream_commit']=='new'
