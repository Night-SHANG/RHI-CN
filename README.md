# RHI-CN

Unofficial, automatically maintained Simplified Chinese localization layer for [RankFTW/RHI](https://github.com/RankFTW/RHI).

RHI-CN intentionally keeps its changes narrow: localization, upstream synchronization, validation, Windows build automation, and release packaging. It does not maintain an independent fork of RHI feature logic.

## Features

- English and Simplified Chinese UI.
- System-language default (`zh-CN` / `zh-Hans` → Chinese; otherwise English).
- Manual `System / English / 简体中文` selector; restart required after changing it.
- Guaranteed English fallback for every missing Chinese resource.
- `.resw` resources with WinUI3Localizer for unpackaged WinUI 3.
- Central `LocalizationService` for dynamic C# UI.
- Manifest-backed user-visible notes/warnings localized without translating technical manifest fields.
- Deterministic XAML/C# localization migration and hardcoded-string detection.
- Reviewed translation memory protected from machine-translation overwrite.
- Daily upstream checks, fail-closed conflict handling, Windows build verification, Installer build, and GitHub Releases.

See [README.zh-CN.md](README.zh-CN.md) for the Chinese user guide, [TRANSLATION.md](TRANSLATION.md) for translation maintenance, and [UPSTREAM.md](UPSTREAM.md) for synchronization behavior.

## Validation

```bash
python -m pytest -q
python tools/materialize.py --source <RHI-source-path> --repo .
python tools/check_localization.py --source <RHI-source-path> --repo . --strict
```

Full application validation runs on `windows-latest` because RHI is an unpackaged .NET 8 / WinUI 3 application.

## License

GNU GPL v3, matching upstream RHI. This repository is not an official RHI localization. See [MODIFICATIONS.md](MODIFICATIONS.md).
