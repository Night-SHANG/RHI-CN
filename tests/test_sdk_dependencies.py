from pathlib import Path
import pytest


def projects(tmp_path, app='2.5.1', test='1.6.250108002'):
    for name, version in [('RenoDXCommander', app), ('RenoDXCommander.Tests', test)]:
        p = tmp_path / name / f'{name}.csproj'
        p.parent.mkdir()
        p.write_text(f'<Project><ItemGroup><PackageReference Include="Microsoft.WindowsAppSDK" Version="{version}" ExcludeAssets="buildTransitive" /></ItemGroup></Project>')
    return tmp_path / 'RenoDXCommander.Tests/RenoDXCommander.Tests.csproj'


def test_sdk_alignment_fixes_upstream_downgrade_and_preserves_build_assets(tmp_path):
    from tools.sdk_dependencies import align_sdk, check_sdk
    p = projects(tmp_path)
    with pytest.raises(RuntimeError, match='mismatch'):
        check_sdk(tmp_path)
    align_sdk(tmp_path)
    assert 'Version="2.5.1" ExcludeAssets="buildTransitive"' in p.read_text()
    assert check_sdk(tmp_path) == '2.5.1'
    first = p.read_bytes()
    align_sdk(tmp_path)
    assert p.read_bytes() == first


@pytest.mark.parametrize('version', ['1.6.250108002', '2.6.0-preview.1'])
def test_alignment_uses_main_project_not_a_hardcoded_upgrade(tmp_path, version):
    from tools.sdk_dependencies import align_sdk, check_sdk
    projects(tmp_path, app=version)
    align_sdk(tmp_path)
    assert check_sdk(tmp_path) == version


@pytest.mark.parametrize('bad', ['$(SDKVersion)', '[2.5.1,)', ''])
def test_unknown_version_contract_fails_without_writing(tmp_path, bad):
    from tools.sdk_dependencies import align_sdk
    p = projects(tmp_path, app=bad)
    before = p.read_bytes()
    with pytest.raises(RuntimeError):
        align_sdk(tmp_path)
    assert p.read_bytes() == before


def test_conditional_reference_fails_closed(tmp_path):
    from tools.sdk_dependencies import align_sdk
    p = projects(tmp_path)
    p.write_text(p.read_text().replace('<ItemGroup>', '<ItemGroup Condition="true">'))
    before = p.read_bytes()
    with pytest.raises(RuntimeError):
        align_sdk(tmp_path)
    assert p.read_bytes() == before


@pytest.mark.parametrize('override', [
    '<PackageReference Update="Microsoft.WindowsAppSDK" Version="1.6.250108002" />',
    '<PackageReference Remove="Microsoft.WindowsAppSDK" />',
])
def test_additional_sdk_item_operations_fail_without_writing(tmp_path, override):
    from tools.sdk_dependencies import align_sdk
    p = projects(tmp_path)
    p.write_text(p.read_text().replace('</ItemGroup>', override + '</ItemGroup>'))
    before = p.read_bytes()
    with pytest.raises(RuntimeError):
        align_sdk(tmp_path)
    assert p.read_bytes() == before


def test_sdk_version_override_fails_without_writing(tmp_path):
    from tools.sdk_dependencies import align_sdk
    p = projects(tmp_path)
    p.write_text(p.read_text().replace('ExcludeAssets=', 'VersionOverride="1.6.250108002" ExcludeAssets='))
    before = p.read_bytes()
    with pytest.raises(RuntimeError):
        align_sdk(tmp_path)
    assert p.read_bytes() == before
