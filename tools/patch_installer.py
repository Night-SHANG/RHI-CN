from __future__ import annotations
import argparse
import re
from pathlib import Path


def patch_installer_text(
    text: str,
    publish_dir: str,
    output_dir: str,
    chinese_isl: str,
    version: str | None = None,
) -> str:
    chinese_matches = re.findall(r'(?im)^\s*Name:\s*"chinesesimplified".*$', text)
    wanted = f'Name: "chinesesimplified"; MessagesFile: "{chinese_isl}"'
    if chinese_matches:
        if len(chinese_matches) != 1 or chinese_isl.lower() not in chinese_matches[0].lower():
            raise RuntimeError("Conflicting Simplified Chinese installer language entry")
    else:
        lang = re.search(r'(?im)^\[Languages\]\s*$', text)
        if not lang:
            raise RuntimeError("Installer [Languages] section missing")
        text = text[:lang.end()] + "\n" + wanted + text[lang.end():]

    if re.search(r'(?im)^ShowLanguageDialog=', text):
        text = re.sub(r'(?im)^ShowLanguageDialog=.*$', 'ShowLanguageDialog=yes', text)
    else:
        setup = re.search(r'(?im)^\[Setup\]\s*$', text)
        if not setup:
            raise RuntimeError("Installer [Setup] section missing")
        text = text[:setup.end()] + "\nShowLanguageDialog=yes" + text[setup.end():]

    if version:
        if not re.search(r'(?im)^#define\s+MyAppVersion\s+"[^"]+"', text):
            raise RuntimeError("Installer MyAppVersion define missing")
        text = re.sub(
            r'(?im)^#define\s+MyAppVersion\s+"[^"]+"',
            lambda _m: f'#define MyAppVersion "{version}"',
            text,
            count=1,
        )

    if re.search(r'(?im)^OutputDir=', text):
        text = re.sub(r'(?im)^OutputDir=.*$', lambda _m: f'OutputDir={output_dir}', text, count=1)
    else:
        text = text.replace('[Setup]', f'[Setup]\nOutputDir={output_dir}', 1)

    if re.search(r'(?im)^OutputBaseFilename=', text):
        base = f'RHI-CN-{version}-Setup' if version else 'RHI-CN-Setup'
        text = re.sub(r'(?im)^OutputBaseFilename=.*$', lambda _m: f'OutputBaseFilename={base}', text, count=1)

    if re.search(r'(?im)^SetupIconFile=', text):
        text = re.sub(r'(?im)^SetupIconFile=.*$', lambda _m: f'SetupIconFile={publish_dir}\\icon.ico', text, count=1)

    source_pattern = re.compile(r'(?im)^Source:\s*"(?P<path>[^"]+)"(?P<tail>;.*)$')
    source_count = 0
    def source_repl(m: re.Match) -> str:
        nonlocal source_count
        old = m.group('path')
        tail = m.group('tail')
        if '\\' not in old:
            return m.group(0)
        leaf = old.rsplit('\\', 1)[1]
        if leaf not in ('*', '{#MyAppExeName}') and not old.lower().startswith('c:\\users\\mark'):
            return m.group(0)
        source_count += 1
        return f'Source: "{publish_dir}\\{leaf}"{tail}'
    text = source_pattern.sub(source_repl, text)
    if source_count == 0:
        raise RuntimeError("Installer [Files] Source contract missing")

    if 'procedure CurStepChanged' not in text:
        if not re.search(r'(?im)^\[Code\]\s*$', text):
            raise RuntimeError("Installer [Code] section missing")
        cleanup = r'''

procedure CurStepChanged(CurStep: TSetupStep);
var
  LangDir, LangPath, SignalPath: String;
begin
  if CurStep <> ssPostInstall then Exit;

  LangDir := ExpandConstant('{localappdata}\RHI');
  if not DirExists(LangDir) then
    ForceDirectories(LangDir);

  LangPath := LangDir + '\ui-language.txt';
  if not FileExists(LangPath) then
  begin
    if ActiveLanguage = 'chinesesimplified' then
      SaveStringToFile(LangPath, 'zh-CN', False)
    else
      SaveStringToFile(LangPath, 'en-US', False);
  end;

  SignalPath := LangDir + '\rhi_shutdown_requested';
  if FileExists(SignalPath) then
    DeleteFile(SignalPath);
end;
'''
        text = text + cleanup
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--publish-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--chinese-isl", required=True)
    ap.add_argument("--version")
    args = ap.parse_args()
    text = args.path.read_text(encoding="utf-8-sig")
    args.path.write_text(
        patch_installer_text(text, args.publish_dir, args.output_dir, args.chinese_isl, args.version),
        encoding="utf-8",
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
