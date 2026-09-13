from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    p = ROOT / '.github' / 'workflows' / name
    assert p.exists()
    return yaml.safe_load(p.read_text(encoding='utf-8')), p.read_text(encoding='utf-8')


def test_validate_workflow_runs_tests_and_materializes_upstream():
    _, text = load('validate.yml')
    assert 'python -m pytest -q' in text and 'tools/materialize.py' in text
    assert 'dotnet test' in text and 'windows-latest' in text


def test_build_workflow_pins_inno_and_verifies_resources():
    _, text = load('build.yml')
    assert '6.7.1' in text and '1ff90acc4ed4aee82b1cda43253243deee3daed4' in text
    assert 'Strings\\en-US\\Resources.resw' in text and 'Strings\\zh-CN\\Resources.resw' in text


def test_upstream_sync_is_daily_strict_and_never_clobbers_release():
    data, text = load('upstream-sync.yml')
    on = data.get('on') or data.get(True)
    assert 'schedule' in on and 'workflow_dispatch' in on
    assert '--strict' in text and '--update-baseline' in text
    assert 'gh release view' in text and '--clobber' not in text and 'published_release_tag' in text
