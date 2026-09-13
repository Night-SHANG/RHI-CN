# Upstream maintenance

Upstream repository: `https://github.com/RankFTW/RHI.git`.

RHI-CN uses an overlay model instead of permanently carrying a modified copy of the RHI source tree. CI clones a clean upstream checkout and runs `tools/materialize.py` against it.

## Channels

`main` is used for early compatibility validation and new-string detection. Public RHI-CN releases are created only from the latest formal upstream GitHub Release tag.

`upstream.json` records the last successfully validated `main` commit, latest observed release tag, and last release tag actually published by RHI-CN. The published marker is written only after GitHub Release creation succeeds, so a failed Release remains retryable.

## Fail-closed behavior

Automation stops instead of guessing when any of the following happens:

- required RHI project files disappear;
- `App.OnLaunched` exists but no longer matches the safe localization bootstrap contract;
- the named `SettingsBtn` toolbar anchor used for the compact language menu changes or disappears;
- official `publish.bat` no longer contains the expected single-file publish contract;
- official Inno Setup fields/files can no longer be patched deterministically, or a conflicting Simplified Chinese language entry appears;
- a previously baselined source scan detects new unhandled UI strings;
- upstream tests, build, publish, resource-package verification, or installer build fails.

The workflow does not force-reset, overwrite conflicting upstream logic, or publish a package after a failed integration check.

## Installer reproducibility

The workflow installs a pinned Inno Setup version and resolves the Simplified Chinese Inno language file to a concrete upstream commit before downloading it. The commit and SHA-256 are written to `reports/installer-translation.json` and included in release notes. An already-created RHI-CN release is treated as immutable during retry: its two expected assets are verified rather than overwritten.

## First synchronization

On the first successful sync, `Localization/inventory/main.json` records existing UI patterns that cannot yet be migrated automatically (primarily complex/interpolated C#). Later runs compare against that baseline and reject newly introduced unhandled strings.

This bootstrap is intentional: legacy upstream text must not permanently disable CI, while new regressions still fail closed.

## Future official localization

RHI-CN currently uses WinUI3Localizer because RHI is unpackaged WinUI 3 and upstream does not currently ship a complete localization system. If upstream adopts its own `.resw`/localization service, the overlay should be reduced rather than maintained in parallel. Any upstream localization architecture change is treated as a review point before the next automated release.
