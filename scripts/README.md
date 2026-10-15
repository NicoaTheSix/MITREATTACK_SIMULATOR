# ATT&CK Data Download Workflow

Run the commands below from your own project root (the folder containing `main.py`) after creating a project-local `.venv`. Follow [the project setup instructions](../README.md#how-to-open-the-project) first. `<project-root>` denotes the absolute path of your project folder; scripts resolve it at runtime and display the actual absolute input/output paths.

## Windows Icon Packaging

`build_windows_icon.py` packages the existing application pixel PNG as a multi-size Windows ICO for the taskbar. Run it with the project environment:

```powershell
& '.\.venv\Scripts\python.exe' -B '.\scripts\build_windows_icon.py'
```

Input: `<project-root>\assets\ttp-selection-studio-icon-pixel.png`. Output: `<project-root>\assets\ttp-selection-studio-icon-pixel.ico`. Both absolute paths are printed before processing. **1/3 read** validates the image; **2/3 encode** reports each of the 16/32/48/64/128/256-pixel frames, preserving alpha and using nearest-neighbor scaling; **3/3 publish** writes the ICO directory and PNG payloads and reports completion. Missing/unreadable input, encoding failure or write failure raises an error and exits nonzero. The source PNG remains intact. Regeneration replaces only this ICO. Root README documents how the application reads the ICO into native taskbar properties.

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

## Failure Handling

Requests have a 60-second socket timeout and a 150 MiB limit per file. HTTP, network, parsing, or validation errors print a failure message and return exit code 1. Cancellation returns 130. Transient Windows sharing locks are retried up to 11 times with bounded delays and visible retry messages. Incomplete `.part` downloads are removed when possible; cleanup failures are reported without masking the original error. Files from successful earlier stages may remain after a failure; the current run does not update `latest.json` until final publishing succeeds. Rerunning refreshes files in the same version directory; older version directories are retained. Concurrent runs against the same output root are not supported.

