# Complete technique review before a layer upgrade

For the paired complete content viewer, checked historical website links and edits to existing target annotations, see [Upgrade content and target editing](upgrade_content_en.md). These capabilities are available in addition to the classification workflow below.

Open **Navigator → Review and upgrade layer…**. Choose a cached official release or an open custom dataset in the same domain, then press **Load target and compare**. Download other official releases through Version first. This operation creates a new document; the source stays open.

## Classification

The **Technique review** tab covers the union of active source and target technique identities, plus unresolved IDs in source annotations. It includes techniques with no annotations. Each identity belongs to exactly one category:

| Category | Meaning |
| --- | --- |
| Added | Active in the target but absent from the active source catalog. |
| Changed | Active in both catalogs, with any STIX record field changed, including version/timestamps. |
| Removed | Absent from the active target, including revoked/deprecated entries without a unique active replacement. Unresolved imported annotation IDs also appear here. |
| Replaced | No longer active under the old ID, with one explicit valid `revoked-by` successor active in the target. Ambiguous successors require manual mapping. |
| Unchanged | Active under the same ID with an identical record. Starts reviewed if its source scopes remain valid. |

A new successor ID also has its own Added entry; the old identity remains Replaced. This makes the categories disjoint by identity without hiding the new target. Replacement suggestions never infer a match from names.

## Review and filters

Choose **All categories** or a category, optionally **Only annotated techniques** and **Show only rows requiring review**. The counters show reviewed/total for every complete category and the whole comparison. Filters do not change these denominators or the required review set. Empty results display a message.

Comments, zero scores, colors, disabled state, links and named metadata count as annotations. A selection marker, divider or expansion setting alone does not. Added drafts with authored annotations also match the annotation filter.

Check **Reviewed** for one identity, or use **Mark visible decisions reviewed** to acknowledge the currently visible identities and their source annotation rows. Review the listed changes and mappings before acknowledging. Hidden pending items still prevent creation. Added items with no draft or explicit inclusion are recorded as **Skip added** when reviewed; they are not automatically selected. Unchanged identities start reviewed.

## Source annotation decisions

The **Annotation mappings** tab retains every source annotation row, including unannotated selections. Choose **Copy** with a valid target technique and tactic, or **Drop**. A removed tactic requires an explicit valid replacement scope. An identity can have several source rows; each must be reviewed. Editing a mapping or unchecking its acknowledgement invalidates the technique review. Recheck it after resolving the change.

Unresolved scalar collisions stop migration. Use **Review migration conflicts…** to choose a candidate, custom value or field removal, or revise the mapping/draft. Compatible comments, links and metadata merge. [One-to-many mappings and an interactive field conflict resolver](upgrade_mapping_en.md) are now available; the [final summary and skip-reason guide](upgrade_summary_en.md) covers the remaining submission checks.

## Annotate Added techniques before completion

Select an Added row and press **Annotate added target…**. The editor supports tactic scope, comment, score, color, enabled state, links and metadata. **Include this TTP in the document** starts unchecked. Save stores an in-memory draft without changing the source. Explicitly checking inclusion adds the chosen tactic occurrences; an annotation alone does not select the technique. Cancel leaves the previous draft intact.

Saving an edit clears its review acknowledgement. Inspect it and mark Reviewed again. Drafts survive filter changes but are cleared when changing/reloading the target or closing the review. A replacement may independently carry source selection to its new ID through an explicitly reviewed Copy mapping.

## Create, save and recover

**Review final summary… → Submit migration** validates all technique reviews and source decisions, including filtered-out rows, then creates a new tab. Failure leaves the review editable and installs no partial result. Cancel preserves the source. Studio JSON keeps the full original source under `migration_archives`; `x_ttp_studio_upgrade` records category counts, every identity review, Added drafts/selection and source mapping decisions. Save/reopen and session recovery retain these records. Navigator JSON preserves the review extension and resulting annotations; source archives belong to Studio JSON.

Inputs are the immutable source/target catalogs and source layer in memory; no output file is written by review/create. The operation reports this before processing, followed by comparison/classification → reviewed mapping and Added-draft validation → new-document completion. Loading a cached release/custom source reports its actual absolute file paths. Save/Export separately announces absolute input/output paths and progress. See [saving and recovery](studio_files_en.md).

## Example and verification

For an old ID A replaced by new B, review A as Replaced and decide whether to Copy its annotations to B. Review B's Added entry explicitly, leaving it empty to skip an independent new annotation or editing it before completion. Review an unrelated new C without checking inclusion: C remains unselected. A hidden, unreviewed C still blocks creation.

From the project root after installing dependencies and caching official v11.3/current snapshots:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_upgrade_review.py'
```

The seven-stage audit prints absolute inputs/outputs, writes deterministic source/target fixtures and isolated cache under `artifacts/upgrade-review`, then checks classification → validation → Added drafts → native dialog/error/cancel → Studio/session/Navigator → real historical partition → `audit.json`. Screenshot: `artifacts/upgrade-review/review.png`. No external server is used.

The workflow follows the [official v5.3.2 upgrade guide](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/USAGE.md#upgrading-a-layer-to-the-current-version), with the complete-identity counters and strict acknowledgement policy documented above. [Guide index](README.md).
