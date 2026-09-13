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
