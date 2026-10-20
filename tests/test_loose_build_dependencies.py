import pytest


def test_clrmd_copy_declares_download_without_compile_reference():
    from tools.materialize import _patch_loose_build_dependencies
    source = r'''<Project><ItemGroup><None Include="$(UserProfile)\.nuget\packages\microsoft.diagnostics.runtime\3.1.512801\lib\net6.0\Microsoft.Diagnostics.Runtime.dll" CopyToOutputDirectory="PreserveNewest" ExcludeFromSingleFile="true" Link="Microsoft.Diagnostics.Runtime.dll" /></ItemGroup></Project>'''
    result = _patch_loose_build_dependencies(source)
    assert '<PackageDownload Include="Microsoft.Diagnostics.Runtime" Version="[3.1.512801]" />' in result
    assert 'PackageReference' not in result
    assert source.split('<None')[1].split('/>')[0] in result
    assert _patch_loose_build_dependencies(result) == result


def test_old_upstream_without_loose_clrmd_is_unchanged():
    from tools.materialize import _patch_loose_build_dependencies
    source = '<Project><ItemGroup /></Project>'
    assert _patch_loose_build_dependencies(source) == source


def test_unknown_clrmd_cache_layout_fails_closed():
    from tools.materialize import _patch_loose_build_dependencies
    with pytest.raises(RuntimeError):
        _patch_loose_build_dependencies('<Project><ItemGroup><None Include="$(OtherRoot)/Microsoft.Diagnostics.Runtime.dll" /></ItemGroup></Project>')
