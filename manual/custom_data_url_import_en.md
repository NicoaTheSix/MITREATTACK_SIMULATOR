# Resolve a Layer's customDataURL

## Acquire a source inside the import preview

1. Choose **File → Import Navigator Layer… / Ctrl+Alt+O** and select a Navigator JSON object or array. Click the custom layer in the layer list.
2. Press **Resolve custom data…**. This opens a source review for that layer, showing its name, domain, recorded release, `customDataURL` and expected dataset SHA-256. Opening the review does not initiate a request.
3. Use the editable source field and **Fetch / Validate source** to request the declared HTTP(S) URL. Alternatively, **Browse Bundle…** chooses a local JSON Bundle. **Choose a cached Bundle…** fills the field with a cached absolute path; press Fetch / Validate to inspect it. Cache choices list up to 1,000 digest-named JSON files and do not imply valid Bundles.
4. If the source is a Collection Index, choose a listed version and press Fetch / Validate again. No referenced Bundle is chosen or fetched automatically. The final Bundle must match the layer's recorded release and requested domain, regardless of the index label.
5. Review the requested/resolved and final source, expected and actual SHA-256, absolute cache output, domain, release, selected TTP count and unresolved annotation count. **Use verified Bundle** accepts the source for this layer and returns to the same multi-layer preview. It does not open a document yet.
6. Resolve other checked layers as needed, then **Open selected layers**. Every checked layer must be ready; the whole group opens together in JSON order. Existing documents remain in place.

Exact verified loaded datasets and Bundle caches still resolve automatically without a network request. A URL-only layer can initially resolve to a unique loaded source with matching URL/release/domain. Multiple hashes at one URL require a source choice. The source review uses the currently resolved dataset as its expected hash when the original URL-only layer lacks one.

## Relative references and redirects

For a local Navigator file, relative `customDataURL` paths resolve against that file's directory. Browse always supplies an absolute local path. For a layer loaded through **File → Load layer URL / custom STIX…**, relative web references resolve against the final Navigator URL after redirects, rather than the local cached JSON directory. A Collection Index's relative Bundle URLs similarly use its final URL.

Only HTTP(S) URLs and explicit local paths are supported. Other URL schemes, embedded credentials, malformed ports and control characters are rejected. HTTP redirects must remain HTTP(S); redirect loops fail. Local path sources preserve the declared source as provenance when using an alternate Bundle file; the actual acquired file and final URL/path are recorded separately.

## Changed source content

The dataset identity is SHA-256 over the exact acquired bytes. Reformatting JSON can change this hash even when the objects mean the same thing.

When the actual hash differs from the recorded/resolved dataset, **Use verified Bundle** stays disabled. Either choose the original Bundle, or check **I approve replacing the recorded dataset with this changed Bundle** after reviewing the source and unresolved techniques. Then accept. Editing or retrying the source clears the earlier candidate and approval; a failed request cannot reuse stale validation.

Replacement applies only to the reviewed layer. Another layer referencing the same URL keeps its own dataset. The new hash receives a separate cache file; the old hash is not overwritten. Missing techniques remain unresolved annotation rows, are counted, and are not silently selected or mapped to other IDs. This is source replacement within the same domain/release; use the reviewed upgrade workflow for a different release.

Example: a layer records dataset hash A at `https://example.org/bundle.json`. The URL now returns hash B at the same release. The preview displays both hashes. Cancel keeps A. Explicit replacement binds B to this imported layer and retains A's cache for other layers. A wrong release/domain cannot be accepted even with replacement approval.

## Validation, files and cancellation

The existing ATT&CK-compatible Bundle checks validate STIX object IDs/types, latest versions, fields, active techniques, tactics, matrices and parent relationships. Source reads are limited to **128 MiB**, Bundle contents to **200,000 objects**, Collection Index choices to **1,000**, and HTTP socket waits to **20 seconds**. Oversized Content-Length is rejected before reading; a streaming byte limit also applies. A digest-named cache whose bytes do not match its filename is rejected. URL/hash identity is never substituted with same-version official data.

Before work, Output announces absolute local inputs or URLs and no output files for inspection. Progress follows **1/5 acquire → 2/5 parse/index → 3/5 validate/review → 4/5 cache accepted bytes → 5/5 bind preview**, with the reader's nested read/parse/catalog/cache progress. The exact output and temporary paths are announced before cache writes. Source inspection alone writes nothing. Acceptance atomically caches valid bytes at `<project-root>/data/attack/custom/<sha256>.json` and updates only an in-memory import draft. Official `active.json` / `latest.json` and the input Navigator file remain unchanged.

Cancel before acceptance changes no binding. Cancel during reading/validation/cache requests interruption at worker checkpoints; late results do not bind or open documents. A completed verified cache may remain after cancellation, but no partial document group is installed. A blocking HTTP read can take up to its socket timeout to return before cancellation finishes.

Accepted drafts record canonical `customDataURL`, exact `x_ttp_studio_dataset`, and `x_ttp_studio_source_review` provenance: declared/resolved/acquired/final locations, previous/current hashes and explicit replacement consent. Studio Save/Open, Navigator re-export and session recovery preserve this binding. Carry the exact Bundle cache with Studio files to another machine; the recorded source may also be a local path.

## Verification

Set `QT_QPA_PLATFORM=offscreen` and run `python -B audit_custom_data_url.py` with the project environment. The audit announces absolute inputs/outputs, uses an isolated local HTTP server and fixture cache, and writes screenshots, round-trip files and `audit.json` under `<project-root>/artifacts/custom-data-url`. It exercises redirects, relative references, missing/invalid/oversized content, domain/release/hash failures, changed-source consent, explicit Collection choices, cache validation, cancellation, complete batch installation and Studio/Navigator/session persistence. It requires no public network download.

[All guides](README.md) · [Custom domains and ID mappings](custom_domains_en.md) · [Multiple layer opening](navigator_bundle_import_en.md) · [Custom catalogs and upgrades](advanced_navigator_en.md)
