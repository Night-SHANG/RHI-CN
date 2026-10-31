# RHI upstream localization maintenance — 2026-10-31

## Scope and provenance

- Localization repository baseline: `48f5f18` (RHI-CN overlay, not RHI-CS).
- Previous validated upstream marker: `b1f339610f575daab91d9c5e577697dab53429cb`.
- Main reviewed: `7c8eee421d9d0d5c47e7b89425f46371b282d088` (Settings redesign, 2.8.9 Beta 2).
- Formal release compatibility: `RHI-2.8.8`, `368942888b3ab57c8c68292d2601d53204888680`.
- No application feature changes, release publication, or upstream state-marker changes.

## What changed

Added 560 distinct English-source translation-memory entries. Existing entries, including reviewed translations, were preserved byte-for-byte semantically. New translations are marked `machine`, not misrepresented as human-reviewed. Product names, INI keys, DLL names and runtime selection values remain unchanged. An independent FAQ review checked text, navigation, paragraph breaks and path escaping.

Resource coverage alone initially concealed runtime omissions in upstream's new UI architecture. Source-level inspection found and addressed:

1. `CogDialog`/`OsCell`/`RdxCompatCell`/`OsComboCell` and `AddSetting` display strings and help text.
2. Runtime `help` / `cell.Help` tooltip boundaries, dialog headers, captions and dynamically assembled component titles.
3. Target-typed `new()` in `CogDialog.MakeCombo`, which bypassed the old ComboBox display-template injector. Selected English values remain intact; only display uses translation.
4. `CogDialog.MakeTextBox` editable `Text` must remain an input value, not a translated label. Its placeholder remains translatable.
5. Settings search result count switch expressions, result-limit suffix and accessibility name.
6. Update countdown and last-check return strings and interpolated durations.
7. New FAQ source literals, while retaining the existing title/description/tip/bullet display-boundary localization.
8. Success/error messages and RenoDX compatibility-help interpolations.

Review also checked added C# prose independently of generated resources, distinguishing complete concatenated sentences from fragments, product names, INI comment exports and log-only text. User-data strings, game names, arbitrary API errors and technical identifiers are not automatically translated.

## Validation

- Repository Python tests: **98 passed** (previously 86).
- Current main materialization and `--strict --no-fallback`: **3450 keys**, no missing/unused Chinese keys, no fallback, no newly unhandled C# findings.
- Formal 2.8.8 materialization and `--strict --no-fallback`: **3430 keys**, same checks pass.
- New translation placeholder multisets match English; prior memory entries unchanged.
- WindowsAppSDK dependency preflight: application/tests both **2.5.1**, main and release pass.
- Independent C# syntax parser: main **306 files**, release **298 files**, no introduced parse errors relative to their upstream revisions.
- XAML/resw XML parsing: six documents per materialized checkout pass.
- `git diff --check` passes.

These are cloud Linux source/resource checks, **not a Windows build or visual proof of every runtime screen**. The workspace lacks the Windows WinUI toolchain. Before merging/publishing, run the repository Windows validation workflow and inspect Settings navigation/search, all component cog dialogs, ComboBox selections, language fallback, long Chinese tooltips, and FAQ. Only after successful Windows verification should automation advance `validated_main_commit`; the published-release marker must only change after successful publication.

## Handoff / safe integration

This repository deliberately has two upstream channels, not two application forks:

- `main` is compatibility/early-string detection, currently **2.8.9 Beta 2**. `validate.yml` and `build.yml` clone main; the latter creates CI package artifacts, not a formal GitHub Release.
- Public stable release synchronization uses the latest formal upstream Release tag, currently **RHI-2.8.8**. Do not substitute the beta main checkout for stable release source.

Recommended next step (requires remote-write authorization): push this maintenance branch and open a draft PR. Both validation and Windows package workflows subscribe to `pull_request`, so a PR starts Windows checks. A branch push alone does not trigger their main-only push event. Authorized manual `workflow_dispatch` may select the maintenance branch; do not dispatch `upstream-sync.yml` just to test, because that workflow writes main, creates tags/releases and marks published state.

Merging these files into main triggers validation/package workflows. It does **not** directly dispatch the formal-release workflow: that dispatch is gated by changes to `release-request.json`, which this patch does not change. However, the existing daily `upstream-sync.yml` schedule will subsequently use the merged overlay and may commit state, translate, or publish a new formal upstream release. The two historical `release-2.7.*` workflow files and all release request/state files are unchanged. Coordinate that existing automation before any public rollout. Windows artifact generation is not evidence that stable publication occurred.
