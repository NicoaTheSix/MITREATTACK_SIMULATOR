# Upgrade content comparison and target annotation editing

Open **Navigator → Review and upgrade layer…**, choose a same-domain target and press **Load target and compare**. The upper section retains the complete technique review and source annotation mapping tabs. The lower **Content comparison** tab has independently scrollable **Before upgrade** and **After upgrade** panes. Drag the horizontal divider to give the comparison more space.

## Inspect both snapshots

Select a technique in **Technique review** to inspect its full source/target records and associated annotation rows. Select a row in **Annotation mappings** to inspect that exact source occurrence, its currently chosen destination and revised annotation. Selecting a different target updates the right pane. When one identity has several source annotation rows, choose the specific mapping row before editing it.

Each pane includes the ID/name, exact catalog release/domain, custom dataset hash when applicable, active/revoked/deprecated state, description, tactic names/slugs, platforms, annotations and complete STIX JSON including extension fields. Original descriptions and user text are escaped; embedded HTML/images are not executed or fetched. Full raw record data remains available by scrolling. **Raw differences** retains the existing field-by-field JSON comparison and original annotations.

A record missing from a snapshot has an explicit empty state. Inactive raw records remain readable even when unavailable as an active destination. An invalid/removed destination tactic requires a new valid mapping before editing. **Drop** shows no copied target annotation. The before pane always comes from the original snapshot; target drafts do not modify it.

## Open the corresponding website version

Official records offer **Open version page…** on each side. For example, dataset v11.3 with T1053.005 proposes `https://attack.mitre.org/versions/v11/techniques/T1053/005/`. The label distinguishes the exact local dataset release from the website's major-version archive: an archive is not a guarantee of an exact patch-version match. The cached STIX record is the precise comparison source.

Clicking the button checks the requested archive in a background worker before launching the system browser. Only the same official HTTPS archive, technique and sub-technique are accepted, including an equivalent `index.html` form. Missing pages, timeouts, errors and redirects to another version/ID or the current website produce a failure message. No latest-page fallback is opened. A successful check opens only the requested version URL. Closing during the check prevents late browser launch. Website availability can change; the local viewer works offline.

Custom datasets do not receive an invented official website version, even if an external reference points to MITRE. Missing records have no version-page button. Both cases keep the exact local content available. This feature does not fetch remote custom reference URLs.

## Edit an existing mapped annotation

In **Annotation mappings**, choose **Copy**, a valid target technique and a valid tactic (or **All tactics**), then press **Edit target annotation…** beneath the comparison. The editor starts with the annotation that would be copied to that destination. Edit Comment, Score, Color, Enabled, Links or Metadata. A blank score removes the stored score; blank color/comment and empty lists clear those fields.

The mapping row controls the destination ID/tactic; the editor's tactic selector is locked. Inclusion is unchanged and is not offered in this editor. This keeps annotation edits independent of selection and prevents accidental scope expansion. Editing an already replaced technique works the same way: first choose its replacement and scope.

Save stores a row-bound draft, refreshes the right pane and clears the source-row and technique acknowledgements. Inspect and mark Reviewed again. Cancel preserves the previously saved draft. An explicit subsequent remap carries the editable fields to the new destination and requires review again. Choosing Drop omits the row and its edits from the result; the audit retains that explicit decision. Target reload/change or closing the upgrade discards uncommitted drafts.

Only the six supported annotation fields can be patched. Identity, tactic and other layer fields cannot be injected through an edit. Unrelated annotation extensions are preserved. Edited scores must be finite, colors valid, structured fields well formed and edited links HTTP(S). Compatible rows merge; unresolved scalar conflicts block creation until explicitly reviewed through [one-to-many mapping and field conflict resolution](upgrade_mapping_en.md).

## Annotate a previously unannotated target

For a technique with no source annotation/selection row, select it in **Technique review** and choose **Edit target annotation…**. This adds a separate target annotation draft without selecting the technique. Existing techniques with source rows take you to the first mapping row; select another row there when needed. Added techniques retain **Annotate added target…** and their explicit, default-off inclusion checkbox from [complete technique review](upgrade_review_en.md).

## Create and preserve the result

After resolving mappings and reviewing all identities, **Review final summary… → Submit migration** validates the patched rows, independent target drafts and every acknowledgement before installing a new document. Original content and its complete source archive remain unchanged. `x_ttp_studio_upgrade.decisions[].annotation_patch` records mapped edits; `technique_reviews[].annotation_rows` records independent target annotations. Studio save/reopen, session recovery and Navigator JSON preserve resulting annotations and review provenance; full source archives are saved in Studio JSON.

All annotation review operations announce in-memory inputs/no output files, followed by edit progress. Comparison/migration reports **Upgrade 1/3** compare → **2/3** validate/apply → **3/3** complete. Version-page checks announce the exact input URL/no output files, then **Upgrade page 1/2** check → **2/2** verified; loading/exporting separately reports absolute file paths. No draft writes a file before Save/Export.

## Verification

From the project root, with dependencies installed and cached v11.3 data:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_upgrade_content.py'
```

Seven stages announce absolute inputs/outputs and exercise deterministic snapshots → full/escaped content → validated target edits → native paired panes/editor/cancel/remapping → archive URL/error/browser handling → Studio/session/Navigator round trips → real historical sub-technique URL/content and report. Archive HTTP responses and browser opening are mocked; this verifies behavior without claiming every public archive is reachable. Artifacts, isolated cache and English/Traditional Chinese screenshots are under `artifacts/upgrade-content`; report: `audit.json`. The audit is registered in `scripts/audit_linux.py`.

The workflow follows [Navigator v5.3.2 Mapping Annotations](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/USAGE.md#mapping-annotations). The website's major-version convention and separate patch data are illustrated by [MITRE's April 2022 release page](https://attack.mitre.org/resources/updates/updates-april-2022/). [Guide index](README.md).

Final submission now passes through [the complete summary, optional skip reasons and unfinished-item navigation](upgrade_summary_en.md).
