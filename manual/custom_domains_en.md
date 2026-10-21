# Custom Domains and Catalog Models

## Load the worked example

1. Choose **File → Load layer URL / custom STIX…**, then **Custom STIX Bundle / Collection**.
2. Browse to `manual/examples/custom_domain_bundle.json` under the project root ([example notes](examples/README.md)). Use fallback release **1.0**, then **Load and validate preview**.
3. Choose **Research Lab**. The preview shows its source/hash, technique/tactic/platform counts and both Matrix names. Click **Open as a new document**.
4. Open the matrix from the TTP sidebar. The custom domain has **Observe** and **Review** columns. Expand the structural parent and select `LAB-001.child`; its parent ID is `LAB-001`.
5. Add a comment, color or score using the existing technique editor or batch controls. Save Studio JSON for a complete editable document, or export selected TTP JSON/CSV, Navigator JSON, SVG or Excel.

The example describes catalog entries; it does not execute them. The normal Ctrl+N/new layer behavior still creates an official Enterprise document. Load a custom Bundle to create a custom-domain document.

If a Bundle contains several domains, the source preview offers each domain with active techniques. Right-click a file tab → **ATT&CK Domain** to switch within that verified dataset. Each domain retains its own selections, annotations and archives. Unavailable official domains remain disabled; switching does not borrow official data or another custom Bundle.

## Define a domain in a Bundle

Put `x_ttp_studio_domains` at the Bundle's top level, alongside `objects`:

```json
"x_ttp_studio_domains": [
  {
    "id": "research-lab",
    "name": "Research Lab",
    "kill_chain_name": "research-chain",
    "reference_source": "research-kb"
  }
]
```

These are independent values:

| Field | Meaning |
| --- | --- |
| `id` | Canonical domain identifier used by `x_mitre_domains` and Navigator `domain`. |
| `name` | Display name in the source chooser, file context menu, sidebar, matrix and exports. |
| `kill_chain_name` | The exact `kill_chain_phases[].kill_chain_name` whose phase names map techniques to tactics. |
| `reference_source` | The exact `external_references[].source_name` used to resolve external IDs. Other references stay original but do not override identity. |

Domain IDs contain 1–64 lowercase ASCII letters/digits/hyphens and start with a letter. `mitre-enterprise` and `mitre-mobile` are reserved legacy layer aliases. Definition names, chains and reference sources are non-empty plain text of at most 128 characters; controls and angle brackets are rejected. Definitions are unique and limited to 32, with at most 32 declared/defined domain identities combined.

An unregistered domain can be inferred only when its active techniques identify exactly one kill chain and one external-ID source. Its display name defaults to its identifier. Missing or ambiguous mappings require an explicit definition; the loader does not guess among unrelated references. The official defaults remain available for Enterprise/Mobile/ICS; custom definitions belong only to their Bundle and do not alter the global official registry.

## Techniques, tactics and relationships

Use the domain identifier on relevant objects' `x_mitre_domains`. Supply `x-mitre-tactic` objects with unique short names, `x-mitre-matrix` objects with resolvable `tactic_refs`, and active `attack-pattern` objects with names and valid domain kill-chain mappings. Tactic short names start with a letter and use at most 128 letters/digits/underscores/hyphens.

With an explicitly configured or unambiguously inferred reference source, external technique IDs can be tokens such as `LAB-001`, `LAB-001.child` or `RESEARCH_A`. They must start with an ASCII letter, contain only ASCII letters/digits/underscore/hyphen/dot, and be at most 128 characters. Unconfigured official-domain Bundles retain their conventional `T####` / `T####.###` checks. Official Navigator layers without a custom source/dataset retain the strict official ID format.

An active technique must have one unambiguous external ID from its configured source. Different STIX technique objects cannot reuse that ID within a domain. The same external ID may appear in another domain or another dataset without merging the objects. A shared STIX object can expose different IDs and kill-chain mappings in two domains through their respective definitions. Other reference fields and custom object properties remain intact.

Sub-techniques use `x_mitre_is_subtechnique: true` and an explicit `subtechnique-of` relationship to exactly one active parent in the same domain. Their ID punctuation does not establish hierarchy. Cycles, nested sub-techniques and cross-domain/missing parents are rejected. Unconfigured official-domain profiles retain their sub-technique-format consistency check. Group/software/campaign/mitigation and detection/asset relationships continue to resolve by exact STIX references, with the same supported source categories.

A relationship with `x_mitre_domains` applies only to its listed domains. A relationship without that field is considered through the endpoints available in each domain. A shared child can have different parents through explicitly scoped edges; an edge cannot point outside its chosen domain's active records.

## Multiple matrices

A domain can contain several active Matrix objects. Each must have distinct, non-empty tactic references, all resolving inside that domain. Every tactic mapped by an active technique must occur in at least one Matrix.

The document presents one **ordered union**: visit Matrix objects in original Bundle order, then each object's `tactic_refs` in order, keeping each tactic's first occurrence. Remaining unused tactic headings sort by short name. Technique mappings retain their domain kill-chain phases; overlapping matrices do not duplicate selected TTPs. This avoids silently choosing the first Matrix and dropping later columns. Original Matrix objects remain accessible in the catalog and raw source; the source preview lists their names. A separate per-Matrix filter/editor is not introduced by this feature.

## Identity and file compatibility

Dataset identity is still the exact Bundle SHA-256. Two Bundles may share a domain identifier, release and STIX IDs while having different names/chains/reference mappings. They remain isolated by dataset hash; loading one never rewrites another's definitions. Formula/overlay/selection comparisons retain their exact domain/version/dataset checks. Use reviewed migration to transfer between sources.

Studio Save/Open and session recovery reconstruct definitions from the exact cached Bundle and retain custom-domain archives. CSV records canonical domain, custom technique/parent/tactic IDs, source/hash and annotations. Navigator export retains raw custom IDs/domain, `customDataURL` and `x_ttp_studio_dataset`; non-official domains also carry the `x_ttp_studio_domain` definition. Recorded definitions must match the exact Bundle when importing/reopening. SVG and Excel use the same resolved domain and technique model.

The MITRE Python SDK accepts only official domains and T-prefixed IDs. The application validates custom identifiers/definitions itself, then validates shared Layer structure on a separate SDK probe. Probe substitutions never overwrite exported IDs or source JSON. Official browser Navigator support for a Studio-specific domain definition is not guaranteed; supply the compatible Bundle and mapping required by the receiving tool.

This remains an ATT&CK-compatible catalog workflow: STIX UUIDs, named techniques, tactics, matrices and supported relationships are required. Arbitrary STIX graph editing, new browser categories or a general ontology editor are outside this feature. Source STIX/TAXII copying preserves original object dictionaries, without derived Python record-view metadata.

## Files, progress and verification

Before processing, the application announces the absolute Bundle/cache input paths or source URL and the absolute output/cache paths, or explicitly no files for in-memory work. The existing source stages are **read → parse → validate definitions/objects/domain projections → cache verified bytes**; each domain's procedure/source relationship indexing reports progress. Domain switching reports **resolve → restore domain state → rebuild tree/matrix** and writes no exchange file. Save/import/export retain their own staged progress and atomic publication.

Run `python -B audit_custom_domains.py` in the project environment with `QT_QPA_PLATFORM=offscreen`. It announces absolute inputs/outputs, uses isolated settings/cache, and writes fixture Bundles, Studio/Navigator/session/CSV examples, SVG/XLSX exports, bilingual screenshots and `audit.json` under `<project-root>/artifacts/custom-domains`. Checks include custom/inferred/shared domains, independent same-version sources, ID conflicts, Matrix union/ref failures, parent isolation, UI switching/search, batch editing, source selection, formulas and persistence. No public network download is needed.

[Example notes](examples/README.md) · [All guides](README.md) · [customDataURL acquisition](custom_data_url_import_en.md) · [Multiple layer opening](navigator_bundle_import_en.md)
