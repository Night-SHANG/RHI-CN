import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_direct_script_entrypoints_can_import_tools_package():
    for script in ('materialize.py','check_localization.py','translate_missing.py'):
        proc=subprocess.run([sys.executable,str(ROOT/'tools'/script),'--help'],cwd=ROOT,capture_output=True,text=True)
        assert proc.returncode == 0, f'{script}: {proc.stderr}'
