# Not Implemented Yet

This document contains the remaining requirements and future proposals for the MITRE ATT&CK Behavior Structure Simulator. These features are not available in the current application unless a section explicitly describes an existing foundation. Implemented behavior and operation flows are documented in [README.md](README.md).

## Remaining Work at a Glance

| Area | Current foundation | Remaining work |
| --- | --- | --- |
| Search | Literal, case-insensitive ID/name matching | Search descriptions |
| Filtering | Platform/tactic tree navigation | Dedicated platform/tactic filters and simulation-support filters |
| Scenario editing | Deduplicated in-memory technique selections | Create/open/save scenarios, parameters, prerequisites, editable execution order |
| Environment detection | The application runs in an existing Python environment | Discover local runtimes, SDKs, and compilers; manual executable paths; rescan/status page |
| Compatibility validation | Dataset integrity and catalog mappings are checked | Validate scenario modules, runtimes, platforms, parameters, and dependencies |
| Preview and simulation | Catalog descriptions and source Procedure Examples | Dry-run plans, behavior modules, synthetic events, and an event timeline |
| Research exports | Developer audit reports and screenshots | Scenario JSON, environment inventory, validation reports, simulation events, and research summaries |
| Domain technique views | Enterprise TTP tree; cross-domain library categories and procedure indexes | Mobile and ICS TTP trees and their technique Procedure Examples views |

Existing developer audits verify implemented catalog/UI behavior. They do not implement scenario validation or research-result export. Saving the selected ATT&CK version also does not persist a scenario or its selected techniques.

## Local Programming Environment Detection

Build a detector and an Environment page for locally available interpreters, runtimes, SDKs, and compilers. Display each discovered executable's absolute path, reported version, and status; provide a rescan action and a manual executable-path option.

| Environment | Information to distinguish |
| --- | --- |
| Python | Interpreter, version, active environment, and discovered installations |
| PowerShell | Windows PowerShell and PowerShell installations and versions |
| JavaScript / Node.js | Node.js runtime and package manager availability |
| Java | Java runtime and Java compiler availability |
| .NET / C# | Installed runtimes and SDKs; a runtime alone does not imply build support |
| Go | Toolchain executable and version |
| Rust | Compiler and Cargo availability |
| C / C++ | Discovered compiler toolchains and configuration requirements |

Detection should check PATH and explicitly supported installation locations. Use bounded version probes in background work and report failures without freezing the interface. Do not install packages or alter the machine during detection.

Distinguish available, not discovered, probe failed, and configuration required. An environment not discovered may exist outside the detector's search scope. A discovered runtime does not prove that a scenario module's dependencies are satisfied. The application language and languages supported by scenario modules are separate choices; detecting several languages does not require rewriting the interface in each language.

## Search, Filtering, and Domain Technique Views

- Extend existing ID/name search to technique descriptions.
- Add explicit tactic and target-platform filters beyond navigating the current tree.
- Add filters for simulation support and local compatibility once those states exist.
- Add Mobile and ICS TTP views using their own domain mappings and parent relationships.
- Display the already-indexed Mobile/ICS Procedure Examples in their corresponding technique views.

The Enterprise tree, sub-technique families, six library categories, source links, copy actions, and version switching are already implemented and are documented in README.md.

## Scenario Model and Editing

Create a reproducible scenario definition and an editor that builds on the current technique selections.

- Create, open, save, and reload a scenario rather than losing selected techniques at exit.
- Add or remove selected techniques from the persisted scenario.
- Record the ATT&CK dataset version, selected technique IDs, behavior-module versions, parameters, execution ordering, and simulation mode.
- Provide an editable execution order; the current Selected Techniques tab is sorted by ATT&CK ID. ATT&CK tactics do not impose one universal chronological sequence.
- Add parameter controls, prerequisites, and compatibility information to technique/module details.
- Review the assembled behavior structure before validation or simulation.

An ordered list is the proposed first builder. A graph editor remains an optional later design if branching or dependencies justify the added complexity.

## Behavior Modules and Compatibility Validation

Define explicit technique-to-module mappings and implement the validator. Catalog membership, module support, and local compatibility should be separate states. The current interface labels catalog entries as having no implemented behavior module; per-module support and runtime compatibility remain to be built.

Each module should declare its version, supported platforms, runtime requirements, parameters, dependencies, expected simulated events, and output artifacts. Validation should identify unsupported selections, missing prerequisites, incompatible runtimes/platforms, and invalid parameters, then provide actionable results before a run.

Dataset integrity checks already exist. Scenario compatibility and module-dependency validation are separate pending features.

## Dry-run Preview and Simulation

The proposed initial simulation workflow models behavior through scenario definitions, dry-run previews, and synthetic event records.

- Build a Preview and Results page showing the selected scenario, planned steps, validation results, and absolute file paths.
- Generate a dry-run simulation plan from validated selections, parameters, and execution order.
- Implement the simulation engine and behavior modules that emit synthetic events.
- Display stage progress, an event timeline, completion, cancellation, and failures.
- Identify simulated behavior clearly and distinguish it from observed host activity.

Procedure Examples currently display ATT&CK source relationships; they are not simulation-generated events. Simulation depth remains a design decision. Any later laboratory execution capability requires a separate design discussion.

## Reproducible Research Artifacts and Export

Implement export and presentation of:

- A versioned JSON scenario definition.
- An environment inventory with executable paths, versions, and probe status.
- A scenario-validation report.
- Synthetic event records and an event timeline.
- A human-readable research summary.

Include the dataset version, selected techniques, module versions, parameters, ordering, simulation mode, and relevant environment information so results can be reproduced. Show final absolute output paths after export. Existing catalog/version audit JSON, Markdown, and screenshots are developer verification artifacts.

## Requirements for Future Processing Stages

Extend the existing progress/path conventions to environment probes, scenario validation, preview, simulation, and export.

Before each operation, show the absolute paths of all input files, planned output files (including logs and reports), the output directory, the selected scenario configuration, and any selected runtime's absolute executable path. Explicitly state when there are no input or output files.

Each stage must show its name, status, and completed/total count when known, or an activity indicator when the total is unknown. Report completion, cancellation, and failure in the interface and operational logs. Run lengthy work outside the UI thread and publish structured progress events.

## Proposed Complete User Workflow

The following workflow remains incomplete; catalog loading, browsing, and in-memory selection already work.

1. Launch and inspect initialization paths and operations.
2. Detect local programming environments and review paths, versions, and probe status.
3. Load/select a versioned ATT&CK catalog with source information and progress.
4. Create or open a scenario and select techniques.
5. Review behavior structure, ordering, parameters, and compatibility.
6. Validate the scenario and resolve unsupported selections or missing prerequisites.
7. Review absolute input/output paths and preview the simulation plan.
8. Run a dry-run simulation with stage progress and an event timeline.
9. Export the scenario and research reports, then display final absolute paths.

## Architecture and Remaining Milestones

The interface, catalog loader, official-data downloader, version picker, and developer audits already exist. Remaining components are the environment detector, scenario model/editor, module registry, compatibility validator, simulation engine, and research exporter. Keep their responsibilities separate and use the existing versioned snapshots and provenance records for reproducible research.

1. Build local environment discovery and the Environment page.
2. Add scenario save/load, parameters, and editable ordering.
3. Add module declarations, support/compatibility states, and scenario validation.
4. Add dry-run preview, synthetic-event simulation, and the results timeline.
5. Add reproducible research-artifact export.

Description search, dedicated filters, and Mobile/ICS technique views are additional remaining extensions. Interface localization remains open for discussion; the current interface uses English labels and original ATT&CK names. A graph editor is an optional future proposal.

When implementing any item, update the README.md in the program's own directory with its operation flow, absolute inputs/outputs, execution steps, progress, and failure handling. Remove or revise the corresponding entry here only after it is implemented and verified.
