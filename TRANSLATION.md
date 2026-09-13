# Translation maintenance

## Runtime model

`tools/materialize.py` generates `Strings/en-US/Resources.resw` from the user-visible XAML/C# text discovered in the selected upstream checkout.

Chinese resolution order is:

1. exact Key override in `Localization/zh-CN/Resources.resw`;
2. reviewed/machine translation in `Localization/translation-memory.json`, matched by English source text;
3. English source text.

The final materialized `zh-CN/Resources.resw` is therefore complete even when Chinese translation coverage is not. Missing Chinese never becomes blank UI or a resource Key.

## Translation memory

Example:

```json
{
  "Install": {
    "translation": "安装",
    "state": "reviewed"
  }
}
```

States:

- `reviewed`: human-confirmed; machine translation must never overwrite it.
- `machine`: generated translation; it may be replaced by a later machine pass or human review.

Matching by English text allows a reviewed translation to survive generated resource-Key changes when upstream moves a control to another file or renames the control.

## Glossary

`Localization/glossary.json` defines project terminology. Current core choices include:

- Add-on → 附加组件
- Mod → 模组
- Shader → 着色器
- Profile → 配置文件
- Game Directory → 游戏目录

Product names and technical identifiers such as RenoDX, ReShade, OptiScaler, DLSS, HDR, DLL names, paths, CLI arguments, and API names are not translated unless they form part of explanatory UI text.

## New strings

After materialization:

```bash
python tools/check_localization.py --source <upstream-path>
python tools/translate_missing.py --source <upstream-path> --repo . --dry-run
```

Without a translation API, the build remains valid and new strings use English fallback.

With an OpenAI-compatible translation API, configure these environment variables / GitHub Secrets:

- `TRANSLATION_API_URL`
- `TRANSLATION_API_KEY`
- `TRANSLATION_MODEL`

Then run:

```bash
python tools/translate_missing.py --source <upstream-path> --repo .
```

Only missing distinct English strings are sent. The glossary is included. Reviewed entries are immutable to the machine merge step.

## XAML coverage

The transformer handles user-visible `Text`, `Content`, `Header`, `PlaceholderText`, dialog button text, accessibility names, titles, and WinUI `ToolTipService.ToolTip`. Plain-text `TextBlock` bodies are normalized into localized `Text` properties. Bindings, `Tag`, event handlers, IDs, and technical values are left untouched.

## C# coverage

C# rewriting is deliberately conservative. It is limited to probable UI/code-behind files such as `MainWindow*`, `SetupWindow*`, dialogs, panel builders, `UIFactory`, and `SettingsHandler`. This prevents a business/service DTO with a property named `Content` or `Title` from being modified accidentally.

Complex interpolated UI strings are reported and baselined rather than guessed. New unhandled patterns fail the scheduled synchronization after the initial baseline is established. The visible language selector is injected as a compact toolbar menu immediately before the upstream named `SettingsBtn`; it is not part of the upstream Settings page.

## Manifest-backed text

RHI displays a small subset of `manifest.json` as UI. RHI-CN extracts `installWarnings` and the user-facing `notes` / `notesUrlLabel` fields from known game-note containers. These values receive deterministic `Data_<SHA-256 prefix>` resource keys and are resolved through `LocalizationService.GetDataString()`. URLs, game names, DLL names, paths, configuration keys, internal IDs and other technical manifest fields are never rewritten.
