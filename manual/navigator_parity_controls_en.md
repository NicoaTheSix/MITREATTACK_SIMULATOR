# Navigator Search, Display and Context Controls

This guide covers the native desktop controls added after comparing official Navigator. The complete evidence-based roadmap is in [NOTIMPLEMENTYET.md](../NOTIMPLEMENTYET.md). [繁體中文](navigator_parity_controls+_zh.md)

## Source Search Fields

Open Groups, Software, Campaigns, Mitigations, Assets or Detections in the sidebar, then **Source search fields…**. Name, ATT&CK ID and Description have independent switches; at least one must remain enabled. Existing files default to all three fields. These are per-layer preferences, separate from TTP search fields.

The identically named matrix button controls all eight **TTPs from** kinds: Campaign / Software / Group / Mitigation / Asset / Detection Strategy / Data Component / Data Source. Changing fields clears the pending source choice: choose an exact result again for single-entry Add/Remove, or use Add all results / Remove all results. Searching does not change included TTPs. See [source batches](source_relationship_selection_en.md); Analytics remain browse-only.

**Example:** turn off Name and ID, leaving Description. Enter a phrase from the description, including spaces. Matching ignores case; a title-only match is excluded. If a name or ID also occurs inside Description, it can still match as description text.

Library categories show source controls and hide TTP-only controls. Returning to TTP reverses that visibility.

## Independent Fills and Indicators

Open **Layer settings… → Colors / indicators**:

| Control | Purpose |
| --- | --- |
| Show manually assigned technique colors | Display stored explicit colors |
| Show original score gradient colors | Display original-score gradients |
| Show aggregate score gradient colors | Display parent/family aggregate gradients |
| Show comment / source Note indicators | Comment and active source Note markers |
| Show metadata indicators | User metadata markers |
| Show link indicators | Link markers |
| Show matrix legend | Hide/show the legend while retaining cell colors |

Priority is manual fill, then enabled aggregate fill, then enabled original-score fill, then an ordinary cell. Aggregates must first be enabled and have a valid result. Turning a switch off retains scores and explicit colors; disabled techniques retain their muted state. **Show layer colors** still hides matrix fills as a group.

Each indicator accepts `#RRGGBB`. Existing visuals are preserved by default: yellow for comments/metadata and blue for links. Identical marker colors share one line; three different colors produce three lines. Flat/Side/Mini and SVG share this projection; Excel uses bottom/right/top borders. All-layer overlays use the active layer's indicator preferences, while background contributions follow each source layer's own fill switches.

**Example:** a technique has an explicit red fill and score 50. Hide manual colors to reveal the score gradient. Hide original-score colors as well to return to an ordinary background if no aggregate applies. The score and explicit red remain stored; re-enable their switches to restore the display. This differs from clearing the actual manual color.

**Legend → Clear all legend items** clears only the draft. Save applies; Cancel discards. SVG's export-specific Show legend option remains independent of matrix legend visibility.

## Annotated Child Counts

Collapsed Flat/Side parents display, for example, `Parent [2 annotated] (5)`. Expanded labels retain the total only; tooltips retain `2 annotated / 5`. Mini stays compact and exposes counts through tooltips.

Counts use deduplicated mapped children in the current platform/tactic family, including hidden disabled children. Scores including zero, comments, user metadata, links, explicit colors, disabled state and active source Notes count. Dividers, internal selection metadata and expansion flags alone do not. Hiding indicators does not change these counts. Totals describe mappings, not included TTPs. These are matrix UI hints; they add no exported TTPs and do not change SVG/Excel label formats.

## Technique Context Menus and URL Templates

Right-click a technique for add/remove/replace/invert, tactic batches and matrix selection commands. They use the existing across-tactic, family and visible-only preferences. Opening the menu does not change selection. View technique details opens the native page. Open technique/tactic reference appears when that exact source object provides a valid reference URL.

Open **Layer settings… → Context actions** to edit Label, URL template and optional Sub-technique URL:

```text
Label: Internal reference
URL: https://example.org/techniques/{{technique_attackID}}?tactic={{tactic_attackID}}
Sub-technique URL: https://example.org/techniques/{{parent_technique_attackID}}/{{subtechnique_attackID_suffix}}
```

Supported prefixes are `technique_*`, `tactic_*`, `parent_technique_*` and `subtechnique_*`, each with `attackID`, `stixID` and `name`, plus `subtechnique_attackID_suffix`. Names are lowercased with spaces replaced by hyphens; substituted values are URL encoded. Missing parent, tactic or identifier data disables the corresponding action. After Save, inspect **Custom actions** in a technique's context menu: its tooltip shows the resolved URL. Only clicking the action opens the system browser.

Templates require fixed-host HTTP(S) URLs. Unknown placeholders, unbalanced braces, embedded credentials and other protocols prevent Save while retaining the draft. Templates execute no code. These are native per-layer preferences rather than changes to official Navigator's deployment config.json.

## Persistence, Progress and Verification

In-memory operations announce no input/output files, then report indexing, validation, application and completion stages. Only Save commits a settings draft; cancellation and errors preserve the document. File Save/Save As uses existing resolved absolute-path announcements, staged validation and atomic publication.

Source fields, display preferences and URL templates persist in Studio saves, duplication, recovery and Navigator JSON through `x_ttp_studio_*` extensions. Official Navigator does not implement these native extensions and may discard them on re-export. CSV remains a selected-TTP/annotation exchange format and does not restore display preferences.

From the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_navigator_parity.py'
```

The seven-stage audit announces absolute paths for `<project-root>/data/attack` and `<project-root>/artifacts/navigator-parity` before producing an isolated fixture, Studio/recovery examples, SVG, Excel, screenshots and `audit.json`. It checks all fill/indicator switch combinations, field isolation, collapsed counts, context dispatch, malformed-input/cancellation preservation, reopening/recovery and exports. It makes no network requests and leaves official snapshot pointers unchanged.
