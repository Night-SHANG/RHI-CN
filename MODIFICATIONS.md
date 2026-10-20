# Modification notice

RHI-CN is a modified/derived distribution workflow for RHI and is not an official RHI release.

Modification layer maintained by the RHI-CN project, 2026:

- adds English/Simplified Chinese localization resources;
- adds WinUI3Localizer integration for the unpackaged WinUI 3 application;
- adds a language preference selector and localization service;
- migrates user-visible XAML and selected dynamic C# UI strings into resources;
- adds localization coverage checks, translation memory, optional incremental translation, upstream synchronization, Windows build verification, and automated GitHub Release packaging;
- adapts the official Inno Setup script for CI paths and installer language selection;
- leaves unrelated RHI feature logic under upstream control.

Upstream source and copyright notices remain governed by the GNU GPL v3 and the notices in the upstream RHI project.

## Upstream synchronization compatibility

- Align the test host's explicit `Microsoft.WindowsAppSDK` version with the
  application's literal version during materialization. Preserve upstream's
  `ExcludeAssets="buildTransitive"` and keep NuGet downgrade errors enabled.
  A read-only SDK preflight runs before Windows test/restore steps. Ambiguous,
  conditional, or property-based SDK references stop for review.
- Support upstream's hyperlink-aware install warnings by translating the full
  manifest message before its existing URL split; older direct-content warning
  layouts remain supported, and unknown layouts still fail closed.
- Declare the upstream loose ClrMD DLL as an exact-version `PackageDownload`,
  derived from its existing cache path. This populates clean runner caches without
  introducing the `PackageReference` that upstream avoids for WinUI publishing.
