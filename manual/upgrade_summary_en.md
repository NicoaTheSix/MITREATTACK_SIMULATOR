# Final upgrade summary, skip reasons and unfinished items

Open **Navigator → Review and upgrade layer…**, load a same-domain target and review the [complete comparison](upgrade_review_en.md), [paired content](upgrade_content_en.md) and [mapping/conflict decisions](upgrade_mapping_en.md). Press **Review final summary…**. It is available before every item is complete, so you can inspect what remains.

## Read the final summary

The header shows source/target releases and domain, full reviewed/total identities, Copy/Drop source-row counts, output annotation rows, selected techniques/occurrences and resolved/total conflicts. Unknown output counts display a dash while invalid mappings prevent a complete plan. A selected occurrence means one technique in one target tactic; it differs from the annotation-row count.

**Category summary** always shows Added, Changed, Removed, Replaced and Unchanged. Reviewed/total counts use the full identity comparison, including items hidden by category, annotated-only or pending-only filters. Each category has an explicit Empty, Incomplete, Skipped or Complete status. Invalid source mappings or relevant conflict checks make that category Incomplete even when all acknowledgements are checked. A category is Skipped when every identity is skipped; a category mixing retained and skipped identities is Complete once reviewed. A skipped identity is an empty Added review, or an identity whose source rows are all Drop with no independent target annotation. With no items, Empty is valid and does not block submission.

**Submit migration** is enabled only when all technique/source acknowledgements, destinations, independent drafts, name and current conflict resolutions validate. Merely opening the summary reviews nothing and changes no selections or annotations. Each valid submission creates a separate target document, preserving the original.

## Edit optional skip reasons

**Skipped items and reasons** lists each Drop source row and each Added technique without an independent annotation/inclusion draft. The action and technique/scope identify what is skipped. Reasons are optional; each accepts up to 4096 Unicode characters, including newlines.

Edit the **Skip reason** cell directly, or highlight one or more rows, type in the multiline editor and press **Apply reason to selected skipped items**. Text entered only in the multiline editor must be applied before returning or submitting. Applying affects only highlighted skipped items; it does not change Copy/Drop, annotations, inclusion or reviewed states.

**Back to review (keep reasons)** keeps reason drafts in the current upgrade dialog. **Cancel** discards changes made inside this summary and preserves the prior drafts. Returning through an unfinished-item button also keeps reasons. Reopen the summary to revise them. Switching a Drop source back to Copy omits its reason from the result; its draft is retained if you switch back. Reloading the target or closing the upgrade dialog discards all unsubmitted drafts. These dialog drafts are not session checkpoints.

Skipping an Added annotation means no additional independent annotation is being authored. It does **not** remove Copy contributions mapped into that new technique. For example, replacing an old technique with a new ID can still copy its old annotation while the new ID's separate Added annotation is skipped.

## Return to unfinished work

The **Unfinished items** tab lists all pending acknowledgements, invalid source destinations/drafts, invalid output name and unresolved/stale/invalid field conflicts found in the complete comparison. Hidden rows still appear. One source can have multiple issues that need separate correction.

- Select an issue and press **Return to selected unfinished item**, or double-click it.
- **Return to first unfinished item** opens the first issue immediately.
- Technique issues focus the owning full-review row; source issues focus the exact mapping row. The dialog clears category, annotated-only and pending-only filters and scrolls the row into view.
- Name issues select the output name. Conflict issues reopen current field review and focus the target/scope/field when available. Stale or generic issues open the relevant review area for correction.

After fixing the item, review it again if required, then reopen the summary. A snapshot fingerprint binds the source, target, mappings, reviews, conflict choices and output name. Changed inputs invalidate the old summary and require a fresh preview. Conflicts also retain their independent candidate fingerprints. Cancel/failed validation never installs a partial result.

## Example

1. Load a newer release and map a removed source row to **Drop**.
2. Review all identities, including empty Added items. Leave one changed source acknowledgement unchecked.
3. Open **Review final summary…**. Confirm the full category counts and blocked submission.
4. Enter `Out of scope for this release` on the dropped row and Apply.
5. Return to the unfinished source row, inspect it and mark it reviewed.
6. Reopen the summary, verify the retained reason and press **Submit migration**.
7. Use **Save / Save As…** for the complete Studio document or export Navigator JSON for exchange.

## Saved data and operation flow

`x_ttp_studio_upgrade.final_summary` stores category counts/status, output counts, source/target dataset provenance and active skips/reasons. Drop source decisions and skipped Added reviews also receive `skip_reason`. The enclosing review schema stays `2`; final-summary schema is `1`. Empty reasons remain explicit. Source archives remain in Studio `migration_archives`. Studio save/reopen, automatic session recovery of the resulting document and Navigator JSON preserve the summary extension; external applications may ignore Studio extensions.

Before computation, the operation reports in-memory inputs/no output files. **Upgrade summary 1/3** compares every identity and validates reasons/reviews → **2/3** validates all mappings/drafts and current conflicts → **3/3** presents readiness. Reason application reports **Skip reasons 1/2 → 2/2**. Submission reruns backend validation and existing **Upgrade 1/3 → 3/3** before installation. Save/Export separately announce absolute input/output paths and file-write progress. Preview/review writes no files.

Program flow: `source_dialogs.py` snapshots decisions and coordinates background preview/navigation/submit → `upgrade_summary.py` validates reasons, aggregates complete readiness and fingerprints → `upgrade_summary_dialog.py` renders summary/local drafts → `layer_upgrade.py` validates again and records the final audit. All modules document their workflow in the root README.

From the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_upgrade_summary.py'
```

The offline audit announces absolute paths and progresses through fixtures → incomplete input/reason validation → conflicts/empty plans/fingerprints → native dialogs/reasons/navigation → submit/stale/failure/close safety → Studio/session/Navigator → report publication. Outputs are under `artifacts/upgrade-summary`, including `audit.json`, `pending-en.png`, `summary-en.png` and `summary-zh.png`. It is registered in the Linux audit runner; native Linux execution remains a separate platform check.

Verification (2026-10-21): 86 dedicated checks and 420 regression checks passed (506 total); static checks passed for 108 Python files, 575 local Markdown links and 805 unique translation keys/placeholders.

[Guide index](README.md) · [繁體中文](upgrade_summary+_zh.md).
