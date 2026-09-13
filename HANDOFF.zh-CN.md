# RHI-CN 项目说明与维护交接

> 最后整理：2026-09-13  
> 仓库：`Night-SHANG/RHI-CN`  
> 上游：`RankFTW/RHI`  
> 当前正式中文版：`RHI-CN 2.7.0 r1`

---

## 1. 项目定位

RHI-CN 是 RHI 的非官方简体中文维护仓库。

目标不是独立重写 RHI，而是：

- 保持 RHI 上游核心功能、业务逻辑和下载源不变。
- 在干净上游源码上应用本地化 overlay。
- 提供 English / 简体中文双语言。
- 自动跟踪上游 `main`。
- 自动检测新增 UI 文本。
- 自动验证汉化完整性。
- 对 RHI 官方正式 Release 构建中文版 Portable ZIP 和 Setup EXE。
- 上游结构变化、补丁失败、测试失败时停止发布，避免生成损坏版本。

原则：

1. 不修改与汉化无关的业务逻辑。
2. 人工审核翻译优先，机器翻译不得覆盖 reviewed 翻译。
3. 英文必须始终作为 fallback。
4. 正式中文版 Release 只对应 RHI 官方正式 Release。
5. 不把上游开发版 `main` 冒充正式版。

许可证跟随上游：GNU GPL v3。

---

## 2. 当前已完成状态

当前开发基线已经完成完整本地化验证：

- English Keys：968
- Simplified Chinese Keys：968
- 覆盖率：100%
- fallback：0
- unhandled C# UI strings：0
- missing zh-CN：0
- unused zh-CN：0
- stale reviewed translations：0

完整 Windows CI 已实际通过：

- Python 测试
- 上游 RHI 官方 .NET 测试
- `materialize`
- 本地化严格检查
- 官方 `publish.bat`
- Portable ZIP
- en-US / zh-CN 资源实际进入发行目录
- Inno Setup Installer
- GitHub Release

这不是理论覆盖率，是实际 Windows GitHub Actions 构建验证结果。

---

## 3. 当前正式 Release

推荐版本：**RHI-CN 2.7.0 r1**

GitHub Tag：

`RHI-CN-2.7.0-r1`

它对应官方：

`RHI-2.7.0`

上游正式版 commit：

`a64cb55453a0afeb4162ca5371ddb048b2297b29`

Release 验证：

- 简体中文覆盖率：100%
- English fallback：0
- Unhandled C# UI：0
- 官方测试通过
- 官方 publish 通过
- Installer 通过

发布文件：

`RHI-CN-2.7.0-r1-Setup.exe`

SHA-256：

`a375f59835aa7d36aa2a55174511d58b6b19b47ebbad72dfc97bca96e5827c62`

`RHI-CN-2.7.0-r1-portable.zip`

SHA-256：

`dc30290be87ac178413f65ee94d34ea7b31657d269aad388d1ecd9d179cacb58`

仓库里还存在较早的 `RHI-CN 2.7.0`，它只有 99.69% 覆盖率，剩余 3 条正式 tag 专属旧文本未翻译。

**不要再把旧的 `RHI-CN 2.7.0` 当最终版本。**

`RHI-CN 2.7.0 r1` 已取代它，并且 GitHub Latest Release 已指向 r1。

---

## 4. 为什么会有 r1

开发时 current upstream `main` 已经达到 100%，但正式 `RHI-2.7.0` tag 比 current main 更旧，存在 3 条只属于正式 tag 的旧 UI 文本：

1. `Paste API key here...`
2. `Please paste your API key first. You can find it at nexusmods.com → Settings → API Keys.`
3. `Invalid API key or network error.`

因此第一次正式 Release 只有 99.69%。

最终把这 3 条加入：

`Localization/reviewed/formal-2.7.0-compat.json`

然后重新从官方 `RHI-2.7.0` tag 构建，生成 100% 的 `RHI-CN 2.7.0 r1`。

以后维护时要记住：

**不能只验证 upstream main；正式 Release tag 也必须独立 materialize 和严格检查。**

---

## 5. 仓库核心结构

```text
RHI-CN/
├─ .github/
│  └─ workflows/
│     ├─ validate.yml
│     ├─ build.yml
│     ├─ upstream-sync.yml
│     └─ request-release.yml
│
├─ Localization/
│  ├─ en-US/Resources.resw
│  ├─ zh-CN/Resources.resw
│  ├─ reviewed/
│  │  ├─ xaml-2.7.0-*.json
│  │  ├─ csharp-2.7.0-*.json
│  │  ├─ interpolated-2.7.0.json
│  │  ├─ manifest-2.7.0.json
│  │  └─ formal-2.7.0-compat.json
│  ├─ translation-memory.json
│  ├─ glossary.json
│  ├─ status.json
│  └─ inventory/main.json
│
├─ overlay/
│  └─ RenoDXCommander/
│     ├─ Services/LocalizationService.cs
│     └─ MainWindow.Localization.cs
│
├─ tools/
│  ├─ materialize.py
│  ├─ check_localization.py
│  ├─ translate_missing.py
│  ├─ translation_memory.py
│  ├─ transform.py
│  ├─ resw.py
│  ├─ patch_publish.py
│  ├─ patch_installer.py
│  ├─ update_state.py
│  └─ ...
│
├─ tests/
├─ upstream.json
├─ release-request.json
├─ README.zh-CN.md
└─ MODIFICATIONS.md
```

---

## 6. 本地化实现方式

### XAML / WinUI 3

XAML 使用：

- `.resw`
- `x:Uid`
- WinUI3Localizer

目标是把用户可见文本从 XAML 中抽离到资源文件。

Tooltip 等附加属性使用 WinUI resource key，例如：

`Uid.ToolTipService.ToolTip`

### C# 动态 UI

C# 中动态创建的 UI、Dialog、状态文本等使用 `LocalizationService`。

普通文本走 `Get(...)`。

插值文本走参数化格式资源，例如原始：

```csharp
$"Peak Brightness: {value} nits"
```

资源：

```text
Peak Brightness: {0} nits
```

运行时使用 `LocalizationService.Format(...)`。

重要原则：

- 不翻译 C# 表达式本身。
- `{expression}` 原样运行。
- 中文只翻译模板。
- 可安全处理三元表达式、版本号、格式化数字等。
- 中文可调整占位符顺序。

### Manifest 文本

`manifest.json` 不整体翻译。

只处理明确会显示给用户的字段，例如：

- `installWarnings`
- 游戏 `notes`
- `notesUrlLabel`
- 明确的用户可见 label / warning / description

以下内容保持原样：

- URL
- DLL 名
- 文件路径
- INI Key
- cvar
- 内部 ID
- 游戏技术字段
- 参数如 `-dx11`

Manifest 文本通过源文本 hash 映射为 `Data_*` 资源。

---

## 7. 翻译记忆与 reviewed 分片

主要翻译数据有两层。

基础翻译记忆：

`Localization/translation-memory.json`

用于一般翻译记忆和可选机器翻译新增。

人工审核分片：

`Localization/reviewed/*.json`

加载规则：

- reviewed 覆盖 machine translation。
- reviewed 不允许被机器翻译覆盖。
- 两个 reviewed 分片对同一源文本给出不同翻译时应 fail closed。
- reviewed 分片按源文本作为权威 key。
- 分片中的 `source_hash` 应按源文本规范化/验证，避免人工搬运 hash 错误造成假失败。

---

## 8. 已修复的重要坑

### Unicode C# 字符串解码

旧逻辑在字符串同时含 `\n` 与非 ASCII 字符时，可能把 `—` 错误解码成 `â`。

已经修复，并有回归测试。

以后不要重新引入通过错误 codec 二次解码 Unicode 字符串的逻辑。

### 换行符差异

上游文本可能在 `\r`、`\n`、`\r\n` 之间变化。

资源 Key 仍应依据上游真实源文本生成，保证运行时映射正确；但翻译记忆查找时应把换行形式规范化，避免同一句话因为换行差异掉到英文 fallback。

### 动态 C# 扫描口径

扫描 `unhandled_csharp` 时必须扫描 **转换后的 C#**，不能扫描转换前源码。

如果 `unhandled_csharp` 数量异常升高，先检查扫描对象是不是转换后的文件。

---

## 9. `materialize.py` 是核心

`tools/materialize.py` 的作用：

1. 接收一份干净的 RHI 上游源码。
2. 应用本地化 overlay。
3. 修改 csproj 以加入本地化依赖/资源。
4. 初始化 LocalizationService。
5. 转换 XAML。
6. 转换 C# 普通和动态 UI 文本。
7. 提取 Manifest 用户可见文本。
8. 合并翻译记忆和 reviewed 分片。
9. 生成 en-US / zh-CN Resources.resw。
10. 输出 localization report。

核心理念：

**RHI-CN 仓库不是上游源码完整 fork，而是一个可重复应用到干净 RHI 上游的本地化/构建层。**

这一点不要改掉。

---

## 10. 验证命令

```bash
python -m pytest -q
python tools/materialize.py --source <RHI源码目录> --repo .
python tools/check_localization.py --source <RHI源码目录> --repo . --strict
```

正式发布前必须关注：

- `coverage_percent`
- `fallback_keys`
- `unhandled_csharp`
- `missing_zh`
- `unused_zh`
- `stale reviewed`

正式版目标应尽量是：

```text
coverage = 100%
fallback = 0
unhandled_csharp = 0
```

---

## 11. GitHub Actions

### `validate.yml`

主要作用：

- Python 测试
- 克隆真实 RHI upstream
- materialize
- localization strict check
- 官方 RHI .NET tests

### `build.yml`

Windows 完整构建：

- Python tests
- 克隆 upstream
- materialize
- strict check
- 官方 .NET tests
- 官方 `publish.bat`
- 验证双语言资源
- Portable ZIP
- Installer patch
- Inno Setup
- 上传 Artifact

### `upstream-sync.yml`

长期自动维护核心，每天检查上游。

流程：

```text
RHI upstream main + 最新正式 Release
              ↓
克隆 current main
              ↓
materialize / strict check
              ↓
可选：只翻译新增文本
              ↓
测试 current main
              ↓
记录最新 upstream main
              ↓
判断是否有新的官方正式 Release
              ↓
若有：克隆正式 tag
              ↓
重新 materialize / strict check
              ↓
测试正式 tag
              ↓
官方 publish.bat
              ↓
Portable + Installer
              ↓
GitHub Release
```

任何关键步骤失败都应该停止发布。

### `request-release.yml`

手动触发正式同步/发布流程的桥接 workflow。

它监听 `release-request.json` 发生 push 变化，然后调用 `upstream-sync.yml`。

正常情况下每天的 `upstream-sync.yml` 已经会自动检查上游；只有需要手工立即触发时才修改 `release-request.json`。

---

## 12. GitHub Actions 权限

RHI-CN 的 workflow 已经在 YAML 内按需声明权限，例如：

- `contents: write`
- `actions: write`

因此仓库 Settings 中默认 Workflow permissions 不必依赖全局 `Read and write` 才能工作。

用户已经手动把仓库默认改成 `Read and write permissions`，这不会破坏 RHI-CN。

从最小权限角度可以改回默认只读，让各 workflow 使用自身声明的写权限；但不是必须。

当前自动提交和自动 Release 已经实际成功验证。

---

## 13. 可选机器翻译 API

默认不要求任何 API。

没有 API：

- 新英文文本会被 scanner 检出。
- 程序可以先走 English fallback。
- 后续人工补 reviewed 翻译。

如果希望自动翻译新增文本，在 `Settings → Secrets and variables → Actions` 配置：

```text
TRANSLATION_API_URL
TRANSLATION_API_KEY
TRANSLATION_MODEL
```

要求是 OpenAI-compatible Chat Completions endpoint。

机器翻译只能处理没有翻译记忆的新增文本。

**绝对不能覆盖 `state: reviewed` 的人工翻译。**

---

## 14. Installer 与 Portable

安装版：

`RHI-CN-x.y.z-Setup.exe`

当前固定：

- Inno Setup：`6.7.1`
- 中文 Inno 语言仓库：`kira-96/Inno-Setup-Chinese-Simplified-Translation`
- 固定 commit：`1ff90acc4ed4aee82b1cda43253243deee3daed4`
- SHA-256：`bf0751fa176569c6faa2f6e17ed2734617bef325d5cc06eae030fdd0258ee778`

便携版：

`RHI-CN-x.y.z-portable.zip`

解压后直接运行 `RHI.exe`。

注意：Portable 不是完全零数据绿色版。RHI 仍会使用 `%LocalAppData%\RHI` 保存设置、缓存、自定义 Addon、Shader、语言偏好等。

不要只单独复制 `RHI.exe`，应保留完整发行目录，尤其 `Strings/en-US` 与 `Strings/zh-CN`。

---

## 15. 语言切换

默认：

- Windows `zh-CN` / `zh-Hans` → 简体中文
- 其他系统语言 → English

顶部工具栏 `Language` 可选：

```text
System
English
简体中文
```

当前设计允许重启后生效。

语言偏好保存到：

`%LocalAppData%\RHI\ui-language.txt`

英文资源是强制 fallback。

任何中文 Key 缺失，都应该显示英文，而不是空白、资源 Key 或崩溃。

---

## 16. 当前分支状态

当前仓库仍有开发期间留下的临时分支：

```text
bootstrap-localization
translate-xaml-2.7.0
translate-csharp-manifest-2.7.0
restore-csharp-batch4
fix-manifest-line-endings
main
```

这些临时分支的有效内容都已经进入 `main`。

长期维护只需要 `main`。

其余 5 个分支可以删除。删除它们不会删除 main 中的代码、不会删除 Release、不会影响自动同步和未来构建。

---

## 17. Release 与 `upstream.json`

`upstream.json` 用于记录：

- upstream 仓库
- 最近验证过的 upstream main commit
- 最近观察到的正式 Release tag
- 已发布的 upstream Release tag

当前 upstream 正式版仍是 `RHI-2.7.0`。

注意：RHI-CN 修正版 tag 是 `RHI-CN-2.7.0-r1`，但从 upstream 状态角度，它仍然对应 `RHI-2.7.0`。

所以 `published_release_tag` 记录 `RHI-2.7.0` 是正常的。

不要错误地把 upstream state 改成 `RHI-CN-2.7.0-r1`。

---

## 18. 上游更新后的标准维护流程

### upstream main 有新 commit，但没有新正式 Release

1. 拉取 upstream main。
2. materialize。
3. strict scan。
4. 发现新增 UI 文本。
5. 没有翻译 API则先保留 English fallback。
6. 有翻译 API则只翻译新增文本。
7. 运行官方测试。
8. 更新 inventory / upstream state。
9. 不创建正式中文版 Release。

人工维护者之后补 reviewed 中文即可。

### RHI 发布新正式版本，例如 `RHI-2.8.0`

1. current main 先验证。
2. 单独 clone `RHI-2.8.0` tag。
3. 对正式 tag 再次 materialize。
4. 对正式 tag 再次 strict scan。
5. 不能假设 current main 的 100% = 正式 tag 的 100%。
6. 补正式 tag 独有旧文本。
7. 官方 .NET tests。
8. 官方 `publish.bat`。
9. 验证 en-US / zh-CN 真正进入 publish。
10. 构建 Portable。
11. 构建 Installer。
12. 生成 Release Notes。
13. 创建 `RHI-CN-2.8.0` Release。
14. 更新 `upstream.json`。

---

## 19. 新版本翻译原则

应翻译：

- Button
- Menu
- Dialog
- Status
- Tooltip
- Warning
- Description
- Placeholder
- User-facing manifest note
- 动态生成 UI 文本

通常不翻译：

- RenoDX
- ReShade
- OptiScaler
- DLSS
- Streamline
- NVIDIA
- Discord
- Mod 名称
- API 名称
- DLL 文件名
- 路径
- URL
- INI Key
- cvar
- CLI 参数
- 游戏内部 ID

术语优先参考 `Localization/glossary.json`。

---

## 20. 不要做的事情

1. 不要直接 fork 一份完整 RHI 源码长期魔改。
2. 不要把上游业务逻辑复制进本仓库维护。
3. 不要为了汉化随意改安装/Mod 逻辑。
4. 不要用机器翻译覆盖 reviewed。
5. 不要看到 100% current main 就直接发布正式版。
6. 不要跳过正式 tag 二次扫描。
7. 不要忽略 `unhandled_csharp`。
8. 不要把 technical strings 盲目翻译。
9. 不要删除 English fallback。
10. 不要把 Build Artifact 当正式 Release。
11. 不要覆盖已有 Release 资产；修正版使用明确的新修订 tag，例如 `-r1`。
12. 不要修改官方 publish 逻辑；只允许通过 `patch_publish.py` 重定向输出目录。

---

## 21. CI 失败排查

### materialize 失败

通常代表：

- 上游文件结构变了。
- patch anchor 失效。
- XAML/C# 模式发生变化。

不要强行跳过，应检查 upstream diff 后更新 transformer/overlay。

### strict localization check 失败

优先看：

`reports/localization-report.json`

关注：

```text
fallback_keys
unhandled_csharp
missing_zh_keys
unused_zh_keys
stale reviewed
```

### C# 编译失败

优先检查：

- transform 后生成的 C#。
- 插值表达式参数化。
- quote / escape。
- Unicode。
- 三元表达式。
- format specifier。

不要直接对原 C# 表达式做翻译。

### Installer 失败

检查：

- Inno Setup 是否仍是 6.7.1。
- 中文 `.isl` 固定 commit 是否可访问。
- `patch_installer.py` 是否仍能匹配官方 `RHI Setup.iss`。
- publish 输出目录是否存在。
- EXE/资源是否完整。

---

## 22. 用户数据注意事项

RHI 数据目录：

`%LocalAppData%\RHI`

长期使用后可能包含重要配置和自定义内容，例如：

```text
%LocalAppData%\RHI\Custom\reshade\Shaders\
%LocalAppData%\RHI\Custom\Addons\
```

官方 Installer 卸载逻辑可能删除 `%LocalAppData%\RHI`。

因此重装/卸载前建议先备份 `%LocalAppData%\RHI`。

---

## 23. 当前 RHI 功能背景

RHI 当前已经用于统一管理：

- RenoDX HDR
- ReShade
- Luma Framework
- DXVK HDR
- DLSS / DLSS RR / FG / Streamline
- DLSS5 / Neural Rendering
- DLSS5 Feeder
- ShortFuse DLSS Tool
- DX11 Bridge
- NR Cost Scaler
- OptiScaler
- OptiPatcher
- ReLimiter
- Display Commander
- NVIDIA Driver Profiles
- RTX HDR
- ReBAR
- Smooth Motion
- G-Sync
- Shader Packs
- ReShade Addons
- HDR Auto Toggle
- Update All

后续汉化要特别留意：新工具名称一般不翻译；工具说明、按钮、状态、错误信息需要翻译；新功能经常会在 C# 动态生成 UI，而不只是在 XAML。

---

## 24. 后续维护建议

短期：

1. 删除 5 个已经合并的临时分支，只保留 `main`。
2. 可考虑把仓库默认 Workflow permissions 改回只读，继续依赖 workflow 自身的最小权限声明。
3. 实际使用 `RHI-CN 2.7.0 r1` 后收集中文排版问题：截断、按钮宽度、Dialog、Tooltip、安装器语言、切换语言等。

注意：**资源扫描 100% 不等于中文排版体验 100%。**

中期：

RHI 2.8.0 或更高版本发布时不要从头汉化，继续复用 translation memory，只处理新增/修改源文本。

长期可加强：

- 自动截图/UI smoke test。
- 占位符集合严格校验。
- Release tag 自动兼容 reviewed 分片。
- 自动生成新增文本 review 清单。
- Release Notes 自动附翻译完整性报告。

---

## 25. 新对话接手提示词

```text
继续维护我的 GitHub 仓库 Night-SHANG/RHI-CN。

这是 RankFTW/RHI 的非官方简体中文自动维护项目。
请先读取仓库中的 HANDOFF.zh-CN.md、README.zh-CN.md、
Localization/status.json、upstream.json，以及 .github/workflows/。

重要原则：
1. 不修改 RHI 无关业务逻辑。
2. 继续使用 materialize/overlay 架构，不改成完整源码 fork。
3. reviewed 人工翻译绝对不能被机器翻译覆盖。
4. English fallback 必须保留。
5. current upstream main 和正式 Release tag 必须分别验证。
6. 正式发布前要求官方测试、publish、Portable、Installer 全流程通过。
7. 遇到新增文本先完整扫描，不要凭猜测修改。
8. 优先一次性完成完整修改、验证和打包，不要让我反复测试半成品。

当前最新正式中文版应为 RHI-CN 2.7.0 r1，
对应官方 RHI-2.7.0，正式 tag 汉化覆盖率 100%，
fallback=0，unhandled_csharp=0。

接手后先检查仓库当前 main、最新 upstream RHI 状态和 GitHub Actions，
再继续后续维护。
```

---

## 26. 关键结论

当前 RHI-CN 已经从“一次性汉化”变成了一套可长期维护的本地化系统。

真正重要的是这条流水线：

```text
上游源码
   ↓
自动扫描
   ↓
translation memory / reviewed
   ↓
XAML + C# + Manifest 转换
   ↓
严格完整性检查
   ↓
官方测试
   ↓
官方 publish
   ↓
Portable + Installer
   ↓
正式中文版 Release
```

后续维护应继续围绕这条流水线增量更新，不要重新从零汉化。
