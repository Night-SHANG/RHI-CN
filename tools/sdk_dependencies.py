"""Keep the test host's explicit WinAppSDK reference aligned with upstream RHI.

Do not remove ExcludeAssets or suppress NU1605: both protect the upstream build.
Unknown MSBuild layouts fail closed rather than guessing an evaluated version.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET

PACKAGE = 'Microsoft.WindowsAppSDK'
APP = Path('RenoDXCommander/RenoDXCommander.csproj')
TEST = Path('RenoDXCommander.Tests/RenoDXCommander.Tests.csproj')


def _reference(path: Path) -> tuple[str, str, re.Match]:
    text = path.read_text(encoding='utf-8')
    root = ET.fromstring(text)
    items = root.findall('.//PackageReference')
    if any(item.get(op, '').casefold() == PACKAGE.casefold()
           for item in items for op in ('Update', 'Remove')):
        raise RuntimeError(f'{path}: SDK item overrides need manual review')
    refs = [item for item in items if item.get('Include', '').casefold() == PACKAGE.casefold()]
    if len(refs) != 1:
        raise RuntimeError(f'{path}: expected exactly one explicit {PACKAGE} reference')
    ref = refs[0]
    if 'VersionOverride' in ref.attrib or len(ref):
        raise RuntimeError(f'{path}: SDK version metadata needs manual review')
    parents = {child: parent for parent in root.iter() for child in parent}
    node = ref
    while node is not None:
        if 'Condition' in node.attrib:
            raise RuntimeError(f'{path}: conditional SDK reference needs manual review')
        node = parents.get(node)
    version = ref.get('Version', '')
    if not re.fullmatch(r'\d+(?:\.\d+){1,3}(?:-[0-9A-Za-z.-]+)?', version):
        raise RuntimeError(f'{path}: SDK version must be a literal NuGet version')
    matches = [m for m in re.finditer(r'<PackageReference\b[^>]*\s*/>', text)
               if re.search(r'\bInclude\s*=\s*([\"\'])Microsoft\.WindowsAppSDK\1', m[0])]
    if len(matches) != 1:
        raise RuntimeError(f'{path}: SDK reference layout changed')
    return text, version, matches[0]


def check_sdk(source: Path) -> str:
    _, app, _ = _reference(source / APP)
    _, test, _ = _reference(source / TEST)
    if app != test:
        raise RuntimeError(f'WindowsAppSDK mismatch: app={app}, tests={test}; align the test reference before restore')
    return app


def align_sdk(source: Path) -> str:
    _, app, _ = _reference(source / APP)
    text, test, match = _reference(source / TEST)
    if app != test:
        replacement, count = re.subn(r'(\bVersion\s*=\s*)([\"\'])[^\"\']*\2',
                                    lambda m: m[1] + m[2] + app + m[2], match[0])
        if count != 1:
            raise RuntimeError('Expected exactly one SDK Version attribute')
        (source / TEST).write_text(text[:match.start()] + replacement + text[match.end():], encoding='utf-8')
    return check_sdk(source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--check', action='store_true', help='Verify alignment without changing files')
    args = parser.parse_args()
    version = (check_sdk if args.check else align_sdk)(args.source)
    print(f'WindowsAppSDK preflight passed: application and tests use {version}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
