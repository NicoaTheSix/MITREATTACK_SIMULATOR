# Studio Files, Saving and Session Recovery

CAR integration adds a third default-on content choice, independent analytic inclusion, seven nonempty content combinations and CAR-only files. Full Save/recovery includes all three content types. Navigator and matrix Excel remain TTP-only projections. See the [CAR operating guide](car_integration_en.md) for the schema, archived snapshots and IO limits.

## Open and Save

| Operation | Menu / shortcut | Behavior |
| --- | --- | --- |
| New document | File → New File / Ctrl+N | Creates an independent Enterprise tab |
| Open Studio JSON | File → Open Studio JSON… / Ctrl+O | Restores a complete document with a clean saved baseline |
| Save | File → Save / Ctrl+S | Chooses a location on first use; then reuses the bound Studio path |
| Save As | File → Save As… / Ctrl+Shift+S | Binds a new path/name and retains the original file |
| Import Navigator | File → Import Navigator Layer… / Ctrl+Alt+O | Uses the existing Navigator version/ID preview workflow |

Studio JSON and Navigator Layer JSON are different formats. Studio uses `schema_version: "1.0"` and preserves the document UUID, creation time, included TTPs, independent enabled flags, global/tactic annotations, colors, scores, Links, Metadata, presentation and domain/version/migration archives. Selection preferences, search fields and partial tactic selections are also retained; see the [selection/search guide](selection_and_search_en.md). Existing Studio 1.0 exports can also be opened; new files additionally store `navigator_import_selected` for exact restoration.

**Example:** Create a file, include T1053.005, add a score/comment and disable it. Press Ctrl+Shift+S and choose `<project-root>/examples/research.json` (create the folder first). Further edits add `*` to the tab; Ctrl+S clears it after success. Close the tab and use Ctrl+O to reopen the file. Confirm inclusion, disabled state and annotations remain. Opening the same path focuses its existing tab; another path with the same document UUID is rejected until the existing document is closed, avoiding duplicate identities.

Save preserves an explicit in-app rename; Save As adopts the new filename stem. Both preserve UUID/creation time. Save compares the previous file SHA-256 with disk contents; external changes stop overwriting. Choose a different Save As path or close and reopen the changed file. Saving over another open tab's path or the active recovery checkpoint is blocked.

CSV, Navigator JSON, SVG and Excel are exchange/report outputs. They do not replace a complete Studio save or clear outstanding changes. The existing Export → Studio JSON action also establishes a Studio save path/baseline because it writes the complete document. Tab tooltips distinguish the Studio save path from the last export path.

## Datasets and Historical Releases

Opening resolves the exact recorded ATT&CK domain/version, including archived versions, rather than applying the current tab's dataset. Official snapshots must already be cached; use Version to download a missing release, then retry. Custom data resolves and verifies `<project-root>/data/attack/custom/<sha256>.json`. Load the matching STIX Bundle first if it is missing. Transfer the Bundle with the Studio document when moving to another computer, and prepare the required official releases there.

Opening never automatically fetches embedded source URLs or changes official `active.json`/`latest.json` pointers. Invalid formats, unavailable versions, inactive/inconsistent selected IDs or invalid archives fail the whole open operation; no partial document or silently reduced selection is installed. Studio/recovery JSON is bounded to 64 MiB; cached custom Bundles to 128 MiB.

## Closing and Exiting

Closing a changed tab, File → Exit / Ctrl+Q, and the main-window close button offer **Save / Discard / Cancel**.

- Save writes complete Studio JSON for each listed document, asking for destinations where needed.
- Discard drops changes in the scope being closed.
- Cancel keeps the documents and application open.

Cancelling a destination dialog or encountering validation/write failure stops closing. During a multi-document exit, if the first save succeeds and the second is cancelled, the first file remains saved and all tabs stay open.

**Exit → Discard clears the entire recovery document list**, preventing discarded drafts from returning next launch. Existing saved Studio JSON files remain available for manual opening. Closing one tab instead removes only that tab from the next recovery checkpoint.

## Automatic Checkpoints and Recovery

Normal startup uses `<project-root>/data/workspace-session.json` plus a `.lock` companion. Absolute paths are reported before processing. Only one live instance owns a recovery file; other instances retain manual Open/Save functionality.

After edits settle for about 1.5 seconds, a background worker atomically writes a checkpoint without overwriting Studio files. It retains up to 50 tabs, order/active tab, full content, unsaved drafts, saved paths/baselines, domain/version archives, primary workspace page, sidebar category and overlay/color-display choices. Exact scroll positions and search text are not restored.

On the next launch, the complete checkpoint is validated in the background and **automatically restored without a recovery confirmation question**. All tabs, saved/dirty states, active document and supported workspace settings return. After the workspace/matrix is ready, the bottom **Output** panel opens and reports the restored tab count, number of tabs with unsaved changes and absolute checkpoint path. The notice follows the interface language. A missing checkpoint starts a fresh workspace; an empty checkpoint reports that there are no tabs to restore. Invalid/cancelled validation preserves the checkpoint and pauses automatic replacement, with no false success notice.

Explicitly choosing **File → Restore last session…** still asks before replacing an already-open workspace:

- Yes restores all tabs and their individual saved/dirty states.
- No keeps the current workspace and starts a new checkpoint.
- Cancel retains the previous checkpoint and suspends its automatic replacement.

Use **File → Restore last session…** to retry. Failed/cancelled recovery retains the checkpoint and current workspace. To explicitly replace it with the current workspace, choose **Start new recovery session…**. A successful saved exit still allows clean tabs to return next launch. After an abnormal termination, recovery uses the last completed checkpoint; input newer than that checkpoint may be absent.

Checkpoints contain document content and absolute paths and remain local. Default checkpoint/lock files are excluded from Git. If a saved file changed or disappeared externally, the recovered draft is marked unsaved and retains conflict detection.

Disable automatic sessions (manual saving and exit prompts remain enabled):

```powershell
.\.venv\Scripts\python.exe -B .\main.py --no-session
```

Choose another checkpoint:

```powershell
.\.venv\Scripts\python.exe -B .\main.py --session-file .\data\my-workspace.json
```

## Progress, Failure Protection and Verification

Open: report absolute input/no-output paths → bounded read → exact dataset resolution → document/archive validation → install a new tab only after success. Save: report absolute input/output/temporary paths → check external changes → serialize/write a sibling temporary file → atomically replace → adopt the saved baseline/path. Once saving starts, it finishes without mid-operation cancellation so the disk and in-memory baseline remain consistent; failures leave the editor available.

Session: capture immutable drafts → report absolute checkpoint/temporary paths → create a checksummed snapshot → publish atomically in the background. Failed writes preserve the previous checkpoint. A failed final exit checkpoint keeps the main window open and reports the reason. Stages appear in Output, the status bar and terminal.

Verify from the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_studio_lifecycle.py
```

Inputs are cached official datasets (including v11.3); outputs go to the announced absolute `<project-root>/artifacts/studio-lifecycle` directory: example documents, isolated checkpoints, screenshots and `audit.json`. The audit covers round trips, cancellation/failure, external changes, exit and multi-tab recovery with isolated settings/sessions, leaving official pointers unchanged. See [README](../README.md) and the [batch guide](batch_operations_en.md) for other workflows.
