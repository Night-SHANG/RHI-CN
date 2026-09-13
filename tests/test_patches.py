import pytest
from tools.patch_publish import patch_publish_text
from tools.patch_installer import patch_installer_text


def test_publish_patch_is_fail_closed():
    src='set OUT=C:\\Users\\Mark\\Publish\\RHI\nset SRC=RenoDXCommander\ndotnet publish %SRC%\\RenoDXCommander.csproj -c Release -r win-x64 -p:PublishSingleFile=true -p:Platform=x64 --self-contained false -o "%OUT%"\n'
    out=patch_publish_text(src,r'D:\a\publish')
    assert 'set OUT=D:\\a\\publish' in out and 'PublishSingleFile=true' in out
    with pytest.raises(RuntimeError): patch_publish_text('echo changed','x')


def test_installer_real_contract_and_conflict_guard():
    src='''#define MyAppName "RHI"\n#define MyAppVersion "2.0.1"\n[Setup]\nOutputDir=C:\\Users\\Mark\\Installers\nOutputBaseFilename=RHI-Setup\nSetupIconFile=C:\\Users\\Mark\\icon.ico\n[Languages]\nName: "english"; MessagesFile: "compiler:Default.isl"\n[Files]\nSource: "C:\\Users\\Mark\\Publish\\RHI\\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion\nSource: "C:\\Users\\Mark\\Publish\\RHI\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs\n[Code]\nfunction InitializeSetup(): Boolean;\nbegin\n Result := True;\nend;\n'''
    out=patch_installer_text(src,r'D:\a\publish',r'D:\a\installer','Installer\\Languages\\ChineseSimplified.isl',version='2.7.0')
    assert 'C:\\Users\\Mark' not in out
    assert '#define MyAppVersion "2.7.0"' in out
    assert 'Name: "chinesesimplified"' in out
    assert 'ui-language.txt' in out and 'DeleteFile(SignalPath)' in out
    with pytest.raises(RuntimeError):
        patch_installer_text('[Languages]\nName: "chinesesimplified"; MessagesFile: "other.isl"\n','p','o','expected.isl')
