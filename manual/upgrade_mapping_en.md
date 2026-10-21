# One-to-many tactic migration and field conflict review

Open **Navigator → Review and upgrade layer…**, load a same-domain target and select a source row in **Annotation mappings**. The [complete review](upgrade_review_en.md) and [paired content/editor](upgrade_content_en.md) workflows remain available.

## Choose an explicit destination list

Press **Edit mapping targets…**. Each row identifies a target technique and either one valid target tactic or **All tactics**. Add/remove rows to map one source occurrence to several tactics, including destinations under different techniques. Technique choices are searchable. Save installs the list as an in-memory draft and selects Copy; Cancel preserves the previous list.

A Copy needs 1–100 destinations. Duplicate technique/tactic pairs, missing or removed tactics, inactive IDs and an empty list are rejected. Under the same source row, All tactics cannot coexist with specific tactics for the same target technique. Use explicit tactic rows for a subset; use Drop to omit the source row entirely. The expanded migration is limited to 20,000 annotation contributions.

The mapping table shows the destination count. Multi-destination rows lock their primary technique/tactic cells; edit the list through the button. With one destination, the original cells remain editable. Editing a single destination through those cells preserves its annotation edits while remapping. Drop keeps the draft for possible reuse but emits neither its annotations nor its selection.

## Inspect and annotate each destination

Select the source mapping row. For multiple destinations, the comparison's destination selector chooses the target shown on the right and edited by **Edit target annotation…**. Each destination can have its own comment, score, color, enabled state, links and metadata. Editing one branch leaves others intact. The destination ID/scope stays locked in the annotation editor; change it in the mapping list instead.

Mapped source selection follows the explicit destinations only. For example, copying a selected source into Execution and Initial Access on a target with three tactics selects those two occurrences, leaving Persistence unselected. An unselected source annotation remains unselected. Annotation enabled flags are independent of selection. All tactics explicitly includes every valid tactic of that target. Family/cross-tactic selection preferences do not broaden this mapping.

## Review conflicting fields

After choosing valid Copy/Drop mappings, press **Review migration conflicts…**. This runs a background plan over every source row and independent target draft, including rows hidden by filters. Preview is allowed before source acknowledgements; final creation still requires every source and technique review.

A conflict occurs when contributions to the same target technique and scope contain different explicit values for a scalar/extension field, such as Score, Color, Enabled or an imported extension object. An absent field contributes no value. A global default row and a tactic-specific override remain distinct Navigator scopes; they do not automatically become an exact-scope conflict.

For each conflicting field, inspect the source labels and complete candidate values, then choose:

| Choice | Effect |
| --- | --- |
| A source candidate | Use that candidate's exact value. |
| Custom JSON value | Enter a finite, valid JSON value of the field's required type. Example score `6.75`, enabled `true`, color `"#aabbcc"`. |
| Clear field | Remove the field from the combined annotation. |

Mark **Reviewed** for each choice and Save. Missing choices, unchecked rows, invalid JSON, NaN/infinity and invalid field types are rejected. JSON `null` is a value, not the removal action; use Clear field to remove a score/color. Changing a choice/value clears its acknowledgement. With no conflicts, the interface displays an explicit empty state.

Distinct nonempty comments combine once, with labels for later source comments. Identical comments are not repeated even with three or more sources. Links and metadata merge by full entry equality, retaining extension properties. Internal selection markers are stripped during migration and regenerated from the actual output selection at export, at most once per row. Compatible scalar fields copy without a conflict dialog.

## Prevent stale decisions

Mapping and annotation edits invalidate current field resolutions. The backend independently binds each resolution to a SHA-256 fingerprint of the complete contributing rows and their origins for that destination. It rejects stale, unrelated, duplicate or unreviewed decisions, even if submitted programmatically. Independent target-draft edits also participate in this check.

Reopening unchanged conflicts restores the saved choices and acknowledgements; Cancel leaves them intact. If candidates change, review the current plan again. Resolving conflicts does not auto-review source mappings or technique identities. Source changes, candidate validation and final resolution validation all complete before a new document is installed. A failure or cancellation preserves the source and leaves no partial migrated document.

## Save and exchange

The result retains the original source under Studio `migration_archives`. `x_ttp_studio_upgrade.review_schema` is now `2`; source decisions retain their legacy fields and record normalized `targets`, including branch patches. `conflict_resolutions` records target/scope/field, candidate fingerprint, explicit action and effective value. Legacy single-target inputs and old saved audit records remain readable.

Studio Save/reopen and session recovery preserve annotations, partial selection and the full audit/archive. Navigator JSON preserves expanded standard technique annotations, selection extensions and review provenance. Other Navigator applications may ignore Studio-specific audit extensions; complete source archives belong to Studio JSON. Current unsubmitted upgrade-dialog drafts are discarded on target reload or closing; save the resulting document after creation.

## Workflow and verification

Before any computation, the operation reports in-memory inputs/no output files; file loading and Save/Export announce their absolute paths separately. **Upgrade 1/3** compares snapshots → **2/3** validates/expands destinations, validates every candidate and plans conflicts → **3/3** installs the fully reviewed result. Destination editing reports **Upgrade targets 1/2 → 2/2**; conflict resolution reports **Upgrade conflicts 1/2 → 2/2**. Annotation editing retains its two-stage progress. Preview and dialogs do not write files.

From the project root with installed dependencies:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_upgrade_mapping.py'
```

The seven-stage offline audit announces absolute inputs/output directory, then prepares a three-tactic fixture → validates explicit expansion/selection → exercises field/stale decisions and three-way deduplication → tests native destination/branch editing and cancellation → tests native resolution/JSON/reopening/invalidation and bilingual controls → verifies Studio/session/Navigator and legacy behavior → publishes `artifacts/upgrade-mapping/audit.json`. Screenshots include `mapping-en.png`, `mapping-zh.png` and `conflicts-en.png`; cache and generated files stay inside that artifact directory. It is registered in `scripts/audit_linux.py`. See the [final-summary and skip-reason guide](upgrade_summary_en.md) for NAV-024 submission and return controls.

[Guide index](README.md).
