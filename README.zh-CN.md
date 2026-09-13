# RHI-CN

RHI 的非官方简体中文自动维护版本。

官方项目：`RankFTW/RHI`。本仓库不隶属于 RHI 官方，功能逻辑、Mod 下载源与核心行为均以上游为准；本仓库只维护本地化、同步、构建和发布层。

## 目标

- English / 简体中文双语言。
- 默认跟随 Windows：`zh-CN` / `zh-Hans` 使用简体中文，其他语言使用英文。
- 顶部工具栏的 `Language` 菜单可手动选择 `System / English / 简体中文`，重启 RHI 后生效。
- 中文缺少任何资源时自动显示英文，不允许空白、Key 或崩溃。
- XAML 使用 `.resw` + WinUI3Localizer `Uid`；C# 动态 UI 统一使用 `LocalizationService`。
- 每日检查 RHI 上游；新增文字进入检测/增量翻译流程。
- 上游结构变化、补丁锚点失效、测试或构建失败时停止发布。
- 正式中文版 Release 只对应 RHI 官方正式 Release，不把 `main` 开发版冒充正式版。

## 下载与安装

正式构建由 GitHub Actions 生成两种产物：

- `RHI-CN-x.y.z-Setup.exe`：安装版。
- `RHI-CN-x.y.z-portable.zip`：便携发行包。

安装器支持 English / 简体中文，并会把安装语言作为首次启动语言。之后可以通过 RHI 顶部工具栏的 `Language` 菜单修改界面语言。

## 为什么偶尔仍会看到英文

英文是强制 fallback。官方刚新增文字时，中文版优先保证功能可用；缺少中文的资源会暂时显示官方英文，并被 `reports/` 和 CI 列入待翻译。人工确认的翻译不会被机器翻译覆盖。

## 本地化结构

```text
Localization/
├─ zh-CN/Resources.resw          # 少量按 Key 的人工覆盖（可为空）
├─ translation-memory.json       # 主要翻译记忆：英文原文 -> 中文
├─ glossary.json                 # 术语表
├─ status.json                   # 特殊 Key 级审核状态
└─ inventory/main.json           # 已知无法自动迁移的 UI 文本基线

overlay/
└─ RenoDXCommander/
   ├─ Services/LocalizationService.cs
   └─ MainWindow.Localization.cs

tools/
├─ materialize.py                # 把本地化层应用到干净上游源码
├─ check_localization.py         # 完整性/新增硬编码检查
├─ translate_missing.py          # 可选增量机器翻译
├─ patch_publish.py              # 只重定向官方 publish.bat 输出目录
└─ patch_installer.py            # CI 化官方 Inno Setup + 中文安装语言
```

## Manifest 文本边界

`manifest.json` 不会整体翻译。RHI-CN 只提取确认会显示给用户的 `installWarnings`、游戏说明 `notes` 与 `notesUrlLabel` 等文本，并通过统一资源层翻译；游戏名、URL、DLL 名称、文件路径、INI Key、内部 ID 和其他技术字段保持官方原值。缺少中文时仍直接显示官方英文。

## 自动同步

`.github/workflows/upstream-sync.yml` 每天检查一次：

```text
RHI main / 最新正式 Release
        ↓
检测上游 commit/tag
        ↓
克隆干净上游
        ↓
应用 Localization overlay
        ↓
扫描新增 UI 文字 / 翻译缺口
        ↓
可选：只翻译新增文字
        ↓
测试当前 main
        ↓
若有新的正式 Release：测试 → 官方 publish.bat → Installer
        ↓
验证 en-US / zh-CN 资源实际进入发行目录
        ↓
固定 Inno Setup 版本并记录中文 Installer 语言文件 commit/SHA-256
        ↓
GitHub Release
```

任何关键步骤失败都会停止 Release。

## 可选机器翻译

默认不需要任何 API。没有 API 时，新文字直接走英文 fallback。

如需自动增量翻译，在 GitHub Secrets 配置：

- `TRANSLATION_API_URL`：OpenAI-compatible Chat Completions endpoint。
- `TRANSLATION_API_KEY`
- `TRANSLATION_MODEL`

脚本只处理翻译记忆中不存在的英文文本；`state: reviewed` 的人工翻译禁止覆盖。

## 开发验证

```bash
python -m pytest -q
python tools/materialize.py --source <RHI源码目录> --repo .
python tools/check_localization.py --source <RHI源码目录> --repo . --strict
```

Windows 完整构建使用官方 RHI 的 `publish.bat`，中文版工具只修改输出目录，不复制一套独立的发布逻辑。

## 许可证

本项目遵循上游 RHI 的 GNU GPL v3。修改内容见 `MODIFICATIONS.md`。

官方 RHI：<https://github.com/RankFTW/RHI>
