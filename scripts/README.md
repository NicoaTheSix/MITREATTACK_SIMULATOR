# ATT&CK Data Download Workflow

## Fusion Studio branding

The Windows launch/setup scripts and `../start-ttpselecter.sh` display **Fusion Studio**. Existing command names, parameters and managed Linux ownership/PATH markers remain stable. Launchers retain the announce absolute program/environment/data/output paths → validate → launch → report progress workflow; root [README.md](../README.md#application-name-and-startup-flow) describes the shared runtime name, tagline and Windows identity. This rename does not install commands or edit user profiles. `update_info_content.py` uses the Fusion Studio User-Agent while retaining its existing source validation and progress flow.

## Pinned ATLAS source

Run `.venv/Scripts/python.exe -B scripts/download_atlas.py` from the project. The script announces both exact HTTPS source URLs, absolute target files and the provenance manifest before starting. **1/3** downloads the native YAML from MITRE ATLAS commit `3259f388d19cbcca11bacf12a0ef97f4198f711b`, **2/3** downloads its original Apache-2.0 license, **3/3** writes release/format/commit and per-file SHA-256 provenance. Each download is bounded to 16 MiB, staged as a sibling `.tmp` file and published with replacement. No execution or service is started.

Inputs: `https://raw.githubusercontent.com/mitre-atlas/atlas-data/3259f388d19cbcca11bacf12a0ef97f4198f711b/dist/v6/ATLAS-2026.09.yaml` and the same commit's `LICENSE`. Outputs: `D:\MITREATTACK_SIMULATOR\data\atlas\ATLAS-2026.09.yaml`, `D:\MITREATTACK_SIMULATOR\data\atlas\LICENSE`, and `D:\MITREATTACK_SIMULATOR\data\atlas\source.json`. Normal application startup reads these local files and does not invoke this downloader. See the root README's ATLAS Workplace section for projection, UI and save/recovery flows.

## Linux Command Setup

From an installed Linux checkout, run `bash setup-ttpselecter.sh`. The root Bash entry point resolves its own directory and invokes `install_linux_command.py` with native `python3`. No executable bit is required on downloaded `.sh` files because both setup and the generated command invoke Bash explicitly. The generated executable is `~/.local/bin/ttpselecter`; it quotes the absolute project launcher path and forwards `"$@"`. The existing `start-ttpselecter.sh` selects the Linux virtual environment and runs the app in the foreground.

The Python installer prints the absolute source project, launcher, destination command, temporary command and profile paths. **1/4** checks Linux and calls the existing launcher with `--check` without opening a GUI. **2/4** rejects unmanaged/conflicting commands or incomplete/edited PATH blocks, plans profile writes and prints each backup output. **3/4** atomically publishes its own executable wrapper, backs up existing profiles before appending a marked POSIX-compatible PATH block, and reports progress for each profile. It covers `.profile`, `.bashrc`, Zsh `.zprofile`/`.zshrc` (under exported absolute `ZDOTDIR` when set), plus the first existing `.bash_profile`/`.bash_login`. **4/4** reads back all blocks and checks the installed command's forwarding with `--check`.

The PATH block retains existing PATH entries and adds `$HOME/.local/bin` only when absent. Existing profile bytes remain intact before the appended block. Backups use `.ttpselecter-backup-<UTC timestamp>-<unique suffix>`; rerunning an unchanged setup creates no duplicate block or backup. A moved project can update only this tool's marked command by rerunning setup from the new folder. Preflight failures leave commands/profiles unchanged; write-time failures can retain completed steps, with backups identified in the output. No system PATH, administrator privileges or dependency downloads are involved. Bash/Zsh startup files refresh the next terminal; for an existing terminal use `export PATH="$HOME/.local/bin:$PATH"`. Fish and other shell startup formats are not configured.

The source program lives beside this README; the root README documents the Bash entry point and generated-command flow. Linux feature-test evidence is separate from command-installer verification.

Run `.venv/bin/python -B scripts/audit_linux_command.py --gui-smoke` in an isolated Linux project to verify setup. The six-stage audit prints its absolute inputs/output fixture directory, then tests preserved profile bytes/backups, Bash and Zsh interactive/login startup (including `ZDOTDIR`), repeat setup, unrelated-command and modified-block refusal, missing-environment preflight, quoted project paths, and optionally an actual xcb/WSLg smoke launch through bare `ttpselecter` from `/tmp`. It uses generated HOME directories under `artifacts/linux-command-setup/<run-id>`, not personal shell profiles. Each subprocess has a 90-second timeout and its own log. The final JSON is published only after assertions pass; missing Zsh is recorded as NOT_RUN. The optional GUI uses `--no-session`; all command/profile fixtures remain under the audit directory. It does not install into the real user's account.

On 2026-10-20, all **43 assertions** passed on Kali WSL2, including all four Bash/Zsh startup modes and a real xcb GUI launch. The current Kali account was then configured separately and verified in fresh Bash/Zsh processes. Exported evidence is in `artifacts/linux-command-setup` at the project root; it excludes generated HOME contents and personal profile backups. Those files remain in the Linux test environment.

## Linux / WSL2 Feature Audits

`audit_linux.py` runs the existing feature audits with native Linux Python. Use an isolated Linux copy with its own `.venv` and cached ATT&CK releases (v20.0, v19.2, v11.3, v11.2 and v1.0 for the historical tests), excluding Windows `.venv`, settings and recovery files. The audits write fixtures, reports and previews inside that copy; they should not run against an active personal workspace. Run `.venv/bin/python -B scripts/audit_linux.py` for the full suite, or add `--platform xcb --only audit_manual_language.py` to exercise the real WSLg/X11 GUI. `--platform wayland` targets the alternative native Wayland backend. The version test uses its cached picker mode, avoiding the full downloader/network audit; custom URL tests use a local HTTP fixture server.

Before starting, the runner prints the absolute project, Python, dataset-pointer, every input audit, report and log output path. For each audit it reports **n/total start → PASS/FAIL and duration**, running a separate process with UTF-8 output and the selected Qt backend. Logs and incremental `audit.json` are in `artifacts/linux-wsl/<platform>`; existing feature-specific artifacts remain under `artifacts`. The default timeout is 240 seconds per audit (`--timeout` changes it). Timeout cleanup terminates only that audit's own process group. A nonzero exit, timeout or traceback fails the case; final verification checks official pointer hashes and exits nonzero when any case fails. The report records OS, Python, key package versions and Qt backend. The runner does not install packages or modify official pointers. Linux system dependency and installation instructions belong in the root README.

Use `--output-dir artifacts/linux-wsl/rechecks` with `--only` to keep targeted rechecks separate from the initial run. On 2026-10-20, the initial 31-program sweep had 21 passes; the latest targeted results passed all 31 after the source-path fix and audit maintenance. `artifacts/linux-wsl/verification.json` preserves the attempt history and chooses the latest recheck for each case, rather than claiming a single 31/31 run. Actual xcb/WSLg checks additionally passed all 30 bilingual Manual cases and the custom-source UI workflow; Wayland and automatic-backend smoke checks also passed. The [full report](../LINUX_WSL2_TEST_REPORT.md) documents evidence and unverified areas. Linux artifacts were exported from the isolated native workspace; `pip-freeze-linux.txt` records its installed packages.

## PowerShell and cmd Command Setup

After the [Installation steps](../README.md#installation), double-click the root `setup-ttpselecter.cmd`, or run it from either PowerShell or cmd. It invokes `Install-TtpSelecterCommand.ps1 -Pause`, so the result remains visible until Enter is pressed. For automation, use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-TtpSelecterCommand.ps1` from the project root; omitting `-Pause` returns immediately after setup. The process-only policy override leaves persistent execution policy unchanged.

The installer derives the absolute project path from its own script location, independently of the current directory. Before processing, it displays the project, launch script, both command-file inputs and `HKEY_CURRENT_USER\Environment\Path` as the output setting; it creates no files. **1/4 validate** checks the project files. **2/4 check** runs the existing launcher with `-Check` in a child Windows PowerShell, verifying `.venv`, required imports and a dataset pointer without opening the app or changing PATH. **3/4 register** appends the project directory to the user `Path` only when absent; comparisons ignore case and trailing separators, expand environment variables, and preserve all existing entries. **4/4 verify** reads back the saved registration. Failures print a diagnostic and exit nonzero; failed preflight checks leave PATH unchanged. No administrator privileges, machine PATH changes, PowerShell profile edits, downloads or package installations are needed.

Restart PowerShell/cmd or the entire Windows Terminal after setup to inherit the user PATH. Run `ttpselecter` from any directory; `ttpselector` remains an equivalent spelling. Both root `.cmd` launchers run `Start-TtpSelector.ps1` using the project's `.venv`, without activation. Run `ttpselecter -Check` for a read-only path/dependency check. Keep the downloaded project folder in place. After moving it, remove the old project entry from the user PATH in Windows Environment Variables and rerun setup from the new folder. Removing the project entry also unregisters both commands.

The launcher first prints all absolute program, Python, dataset-pointer, settings, session and log paths. **1/3** validates required files; **2/3** starts the visible Windows Qt application with the project as its working directory; **3/3** reports the launcher PID and returns control to the shell while application loading continues. Each launch writes separate stdout/stderr logs under `<project-root>\artifacts\launch`, named by timestamp and launcher PID. Settings/session writes remain controlled by the existing application. `-Check` creates no files, checks imports in **2/3**, and reports readiness in **3/3**. Failures exit nonzero with a diagnostic. If a command is unavailable in an already open shell, restart it or invoke the root `.cmd` by its full path. Missing dependencies require completing Installation; application failures after launch appear in the printed error log.

## Offline Info Release Notes

`update_info_content.py` refreshes the local release introductions for **Info → Version update history**. Run `<project-root>\.venv\Scripts\python.exe -B <project-root>\scripts\update_info_content.py`. Before processing it prints the official input URL, the absolute output `<project-root>\data\info\attack-release-notes.json`, and its `.part` path. **1/3** discovers version/release-note links from the official ATT&CK history page; **2/3** reads official HTTPS pages with four bounded workers and prints per-release progress; **3/3** atomically publishes a numerically sorted cache only after every entry succeeds. Each entry contains at most 25 words of the official introduction and a link to the complete log. Network, unexpected redirects, missing introductions, or invalid history stop the refresh with a nonzero exit code and retain the previous published cache. Cancellation reports status and exits 130. Normal application startup reads this cache offline and never downloads pages. The new v20 snapshot was prepared with `attack_versions.discover_versions` / `prepare_version` and both `latest.json` and `active.json` were published only after three-domain validation; earlier snapshots remain available.

Run the commands below from your own project root (the folder containing `main.py`) after creating a project-local `.venv`. Follow [the project setup instructions](../README.md#how-to-open-the-project) first. `<project-root>` denotes the absolute path of your project folder; scripts resolve it at runtime and display the actual absolute input/output paths.

## Windows Icon Packaging

`build_windows_icon.py` packages the existing application pixel PNG as a multi-size Windows ICO for the taskbar. Run it with the project environment:

```powershell
& '.\.venv\Scripts\python.exe' -B '.\scripts\build_windows_icon.py'
```

Input: `<project-root>\assets\fusion-studio-icon-pixel-v2.png`. Output: `<project-root>\assets\fusion-studio-icon-pixel-v2.ico`. Both absolute paths are printed before processing. **1/3 read** validates the image; **2/3 encode** reports each of the 16/32/48/64/128/256-pixel frames, preserving alpha and using nearest-neighbor scaling; **3/3 publish** writes the ICO directory and PNG payloads and reports completion. Missing/unreadable input, encoding failure or write failure raises an error and exits nonzero. The source PNG remains intact. Regeneration replaces only this ICO. Root README documents how the application reads the ICO into native taskbar properties.

## Official Data Download

`download_attack_data.py` downloads the latest stable release from the official `mitre-attack/attack-stix-data` repository. It uses Python 3.11 and standard-library modules only; PySide6 is not required for downloading data.

## Run

From PowerShell in the project root:

```powershell
& '.\.venv\Scripts\python.exe' '.\scripts\download_attack_data.py'
```

The default output root is `<project-root>\data\attack`, resolved relative to the script location, independently of the working directory. Use `--output-dir 'ABSOLUTE_DIRECTORY'` to choose another output root. HTTPS access to `api.github.com` and `raw.githubusercontent.com` is required. No packages are installed and no system configuration is changed.

## Inputs and Outputs

There are no local input data files. Sources are the official latest-release API, its resolved commit, and files at that immutable commit. At startup, the program prints its Python executable, input status, and absolute output root. Release discovery happens in memory without file writes. Once the version is known, it prints every resolved output path and temporary path before writing files.

A version directory such as `data/attack/v19.2` contains:

- Original Enterprise, Mobile, and ICS STIX 2.1 JSON bundles, named with their version.
- `index.json`: the official catalog index from the pinned commit.
- `release.json`: GitHub release metadata and the resolved commit SHA.
- `LICENSE.txt`: the upstream terms.
- `manifest.json`: version, source URLs, download timestamp, sizes, SHA-256 hashes, and object statistics.
- `README.md`: snapshot provenance and domain statistics.

`data/attack/latest.json` points to the successfully downloaded version using paths relative to that file's directory. The interface should start with the Enterprise bundle.

## Processing Stages and Progress

1. **Discover:** query the latest stable release and resolve its tag to a commit; display each request and the resolved version.
2. **Prepare:** display absolute final and temporary file paths, create the snapshot directory, and save release metadata.
3. **Catalog:** download and validate the official index entries and license; report transfer bytes and percentages when Content-Length is available.
4. **Data:** download each domain to a `.part` file; report transfer progress, validate JSON, STIX bundle structure, collection version, and technique domains; publish each valid bundle and display active tactic/technique counts.
5. **Publish:** save the manifest and snapshot README, then update `latest.json` only after all three domains succeed.

Validation checks are structural and do not implement the complete STIX schema. SHA-256 values are locally computed integrity records, not upstream signatures. Original data keeps revoked/deprecated entries; active counts exclude them and distinguish techniques from sub-techniques.

## NAV-018/NAV-019/NAV-020 formula references

The development-only [formula-reference workflow](formula-reference/README.md) pins mathjs 15.2.0, reads trusted case JSON and writes reproducible golden results. `generate.cjs` covers scalar expressions; `generate-scope.cjs` hash-checks and executes the reviewed official method with limited model stubs for missing-score/scope rules. `generate-gradient.cjs` executes hash-pinned official service/Gradient TypeScript with pinned development-only tinycolor2/tinygradient/TypeScript dependencies, producing automatic-gradient configuration references. All three announce absolute input/output paths before runtime checks → case-count evaluation progress → publication. Node and official-source execution are development-only; the desktop application and offline Python audits do not need Node/mathjs. Read that directory's README for regeneration commands, upstream provenance, the six-stage scalar audit and seven-stage scope/gradient audits. `audit_linux.py` includes the scalar, scope and gradient Python audits in its normal list; use `--only audit_formula_gradient.py` for the gradient audit alone.

## Failure Handling

NAV-023 registers `audit_upgrade_mapping.py` in `audit_linux.py`. Its seven stages announce absolute paths, prepare isolated source/three-tactic target fixtures → validate destination expansion/partial selection → review candidate/custom/clear choices, stale fingerprints and three-way merges → exercise native destinations/branch edits/cancel → exercise native conflict JSON/reopening/invalidation and bilingual controls → round-trip Studio/session/Navigator and old single-target behavior → publish `artifacts/upgrade-mapping/audit.json` and previews. Inputs are generated fixtures plus cached version metadata; no third-party requests are used. See the [English guide](../manual/upgrade_mapping_en.md) or [中文手冊](../manual/upgrade_mapping+_zh.md). Source/target caches and output examples stay inside the dedicated artifact directory.

NAV-022 registers `audit_upgrade_content.py` in `audit_linux.py`. It announces absolute inputs/outputs, then runs fixtures → full escaped content → target-edit validation → native paired/editor/cancel/remap → mocked archive checks/browser dispatch → Studio/session/Navigator → historical v11.3 record and report. All outputs/cache are under `<project-root>/artifacts/upgrade-content`. No live third-party requests are used; public archive availability is verified only when an application user clicks its version-page button. See the [English guide](../manual/upgrade_content_en.md) or [中文手冊](../manual/upgrade_content+_zh.md).

NAV-021 adds `audit_upgrade_review.py` to the desktop audit list in `audit_linux.py`. It announces absolute dataset/output paths, then runs seven stages: deterministic fixtures → complete classification/review validation → Added annotations/selection/conflicts → native dialog/filter/edit/cancel/failure → Studio/session/Navigator round trips → real historical catalogs → report publication. Outputs and isolated cache are under `<project-root>/artifacts/upgrade-review`. See the [English workflow](../manual/upgrade_review_en.md) or [中文手冊](../manual/upgrade_review+_zh.md). The audit uses no external HTTP server; cached official v11.3 and current snapshots are required for its historical stage.

Requests have a 60-second socket timeout and a 150 MiB limit per file. HTTP, network, parsing, or validation errors print a failure message and return exit code 1. Cancellation returns 130. Transient Windows sharing locks are retried up to 11 times with bounded delays and visible retry messages. Incomplete `.part` downloads are removed when possible; cleanup failures are reported without masking the original error. Files from successful earlier stages may remain after a failure; the current run does not update `latest.json` until final publishing succeeds. Rerunning refreshes files in the same version directory; older version directories are retained. Concurrent runs against the same output root are not supported.


## NAV-024 final-summary audit registration

`audit_linux.py` includes the root `audit_upgrade_summary.py` audit. It reports absolute catalog/artifact paths, then prepares fixtures → validates incomplete inputs/reasons → checks conflict/empty-plan/snapshot readiness → exercises native summaries, local reason drafts and direct return → tests submit/stale/failure/close → round-trips Studio/session/Navigator → publishes `artifacts/upgrade-summary/audit.json`. The runner retains per-audit process/log/report progress. See the [English manual](../manual/upgrade_summary_en.md) and [中文手冊](../manual/upgrade_summary+_zh.md). This registration does not itself claim a native Linux pass.

## NAV-025 SVG theme audit registration

`audit_linux.py` includes root `audit_svg_themes.py`. It reports absolute catalog/artifact paths, then prepares isolated fixtures → renders three layouts/two themes with actual pixel/contrast checks → checks headers/legends/visibility/aggregates → tests alpha overlays and source switches → exercises native bilingual theme/preview/file equality → tests invalid input/failure/cancel/real domains and source preservation → publishes `artifacts/svg-themes/audit.json` and SVG/PNG previews. The runner keeps its existing per-audit process/log/report progress. See the [English guide](../manual/svg_themes_en.md) and [中文手冊](../manual/svg_themes+_zh.md). Registration does not itself claim a native Linux pass.

## NAV-026 paper-preset audit registration

`audit_linux.py` includes root `audit_svg_paper.py`. It announces absolute fixture/cache/vector/screenshot/report paths, then prepares fixtures → verifies every preset/orientation/unit with SVG XML and Qt rendering → checks Custom/Auto/header/legend/layout/theme → exercises native locking/round trips/Custom restoration/limits → tests bilingual controls and identical preview/export/cancel → tests publication failures and source preservation → publishes `artifacts/svg-paper/audit.json` and 30 preset SVG examples. The runner retains its per-audit process/log/report progress. See the [English manual](../manual/svg_paper_en.md) and [中文手冊](../manual/svg_paper+_zh.md). Registration does not itself claim a native Linux pass.

## Fixed CAR acquisition

`download_car.py` reads `https://codeload.github.com/mitre-attack/car/zip/1b922fe1527d956e222a99473472e594f10f610b` (64 MiB maximum), announces the absolute `data/car` output root/manifest and every selected destination, then **1/3 download → 2/3 write/hash original members → 3/3 publish verified-count manifest**. It retains analytics/data_model/sensors YAML, source generator/schema references and LICENSE/NOTICE. It never extracts outside the root or executes upstream code. Runtime startup reads local snapshot files only. CAR integration and IO workflow are documented in the root README.
