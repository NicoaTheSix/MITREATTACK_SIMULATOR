"""Audit downloaded ATT&CK data and every actual Enterprise UI tree mapping."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from attack_catalog import BROWSE_CATEGORIES, DOMAIN_LABELS, external_id, local_path
from main import MainWindow, ROLE_CONTEXT, ROLE_ID, configure_application
from scripts.download_attack_data import validate_bundle


class Audit:
    def __init__(self, root, output):
        self.root = root
        self.output = output
        self.result = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                       "scope": "All downloaded snapshot artifacts and all Enterprise UI mappings/active records",
                       "checks": {}, "statistics": {}, "scheduled_task_job": [], "errors": []}
        self.expected = set()
        self.source_records = {}
        self.source_parents = {}
        self.source_tactics = {}
        self.source_order = []
        self.source_library = {}
        self.source_procedures = {}
        self.window = None

    def report(self, stage, message, current=0, total=0):
        print(f"[{stage}] {message}" + (f" ({current}/{total})" if total else ""), flush=True)
        if self.window:
            self.window.report(f"[Audit {stage}] {message}", current, total)
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)

    def check(self, condition, code, message):
        if not condition:
            self.result["errors"].append({"check": code, "message": message})
        return condition

    def read_sources(self):
        pointer_path = self.root / "latest.json"
        print(f"Input file: {pointer_path}", flush=True)
        for name in ("catalog-audit.json", "catalog-audit.md", "scheduled-job-preview.png", "navigation-preview.png", "procedure-preview.png"):
            print(f"Output file: {self.output / name}", flush=True)
        self.report("1/7 Files", "Resolving input paths")
        pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
        manifest_path = local_path(self.root, pointer["manifest"])
        print(f"Input file: {manifest_path}", flush=True)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        snapshot = manifest_path.parent
        self.result["attack_version"] = pointer["attack_version"]
        self.result["commit_sha"] = manifest["commit_sha"]
        self.result["inputs"] = [str(pointer_path), str(manifest_path)]
        self.check(manifest["attack_version"] == pointer["attack_version"], "version", "Pointer/manifest version differs")
        bundles = {}
        for number, entry in enumerate(manifest["files"], 1):
            path = local_path(snapshot, entry["filename"])
            print(f"Input file: {path}", flush=True)
            self.result["inputs"].append(str(path))
            self.report("1/7 Files", f"Checking hash and size: {path.name}", number, len(manifest["files"]))
            raw = path.read_bytes()
            self.check(hashlib.sha256(raw).hexdigest() == entry["sha256"], "hash", f"SHA-256 mismatch: {path.name}")
            self.check(len(raw) == entry["bytes"], "size", f"Size mismatch: {path.name}")
            if "domain" in entry:
                bundle = json.loads(raw)
                self.result["statistics"][entry["domain"]] = validate_bundle(bundle, pointer["attack_version"], entry["domain"])
                bundles[entry["domain"]] = bundle
        self.source_library = {domain: {obj["id"]: obj for obj in bundle["objects"]
                                       if not obj.get("revoked") and not obj.get("x_mitre_deprecated")
                                       and obj.get("type") != "relationship"}
                               for domain, bundle in bundles.items()}
        for domain, bundle in bundles.items():
            active_records = self.source_library[domain]
            expected_procedures = defaultdict(dict)
            for obj in bundle["objects"]:
                if (obj.get("type") != "relationship" or obj.get("relationship_type") != "uses"
                        or obj.get("revoked") or obj.get("x_mitre_deprecated")):
                    continue
                source = active_records.get(obj.get("source_ref"), {})
                target = active_records.get(obj.get("target_ref"), {})
                if target.get("type") == "attack-pattern" and source.get("type") in {"intrusion-set", "malware", "tool", "campaign"}:
                    expected_procedures[target["id"]][obj["id"]] = {
                        "relationship_id": obj["id"], "source_ref": source["id"],
                        "source_id": external_id(source), "source_name": source.get("name", source["id"]),
                        "source_type": source["type"], "description": obj.get("description", ""),
                        "references": obj.get("external_references", []),
                    }
            self.source_procedures[domain] = dict(expected_procedures)
        self.check(set(bundles) == {"enterprise-attack", "mobile-attack", "ics-attack"}, "domains", "Missing domain bundle")
        self.result["checks"]["snapshot_artifacts_verified"] = len(manifest["files"])
        enterprise_path = local_path(self.root, pointer["enterprise_bundle"])
        self.check(enterprise_path == snapshot / next(entry["filename"] for entry in manifest["files"]
                   if entry.get("domain") == "enterprise-attack"), "pointer", "Enterprise pointer does not match manifest file")
        self.report("2/7 Reference", "Building independent reference from raw STIX objects")
        objects = bundles["enterprise-attack"]["objects"]
        active = [obj for obj in objects if not obj.get("revoked") and not obj.get("x_mitre_deprecated")]
        self.source_records = {obj["id"]: obj for obj in active if obj.get("type") == "attack-pattern"
                               and "enterprise-attack" in obj.get("x_mitre_domains", [])}
        self.source_tactics = {obj["x_mitre_shortname"]: obj for obj in active if obj.get("type") == "x-mitre-tactic"}
        matrix = next(obj for obj in active if obj.get("type") == "x-mitre-matrix")
        tactics_by_id = {obj["id"]: slug for slug, obj in self.source_tactics.items()}
        self.source_order = [tactics_by_id[ref] for ref in matrix["tactic_refs"]]
        parent_lists = defaultdict(list)
        for obj in active:
            if obj.get("type") == "relationship" and obj.get("relationship_type") == "subtechnique-of":
                parent_lists[obj["source_ref"]].append(obj["target_ref"])
        ids_seen = set()
        for number, (key, obj) in enumerate(self.source_records.items(), 1):
            if number % 100 == 0:
                self.report("2/7 Reference", "Checking record metadata and relationships", number, len(self.source_records))
            technique_id = external_id(obj)
            self.check(bool(technique_id) and technique_id not in ids_seen, "external_id", f"Missing/duplicate ID: {key}")
            ids_seen.add(technique_id)
            self.check(bool(obj.get("name")) and bool(obj.get("description")), "content", f"Missing name/description: {technique_id}")
            refs = [ref for ref in obj.get("external_references", []) if ref.get("source_name") == "mitre-attack"]
            self.check(any(ref.get("url", "").startswith("https://attack.mitre.org/") for ref in refs),
                       "reference_url", f"Missing official reference URL: {technique_id}")
            platforms = obj.get("x_mitre_platforms", [])
            phases = [phase["phase_name"] for phase in obj.get("kill_chain_phases", [])
                      if phase.get("kill_chain_name") == "mitre-attack"]
            self.check(bool(platforms) and bool(phases), "mapping_metadata", f"No platform/tactic: {technique_id}")
            self.check(all(phase in self.source_tactics for phase in phases), "tactic_reference", f"Unknown tactic: {technique_id}")
            for platform in platforms:
                for phase in phases:
                    self.expected.add((platform, phase, key))
            if obj.get("x_mitre_is_subtechnique"):
                parents = parent_lists[key]
                valid = self.check(len(parents) == 1 and parents[0] in self.source_records,
                                   "parent_relation", f"Invalid/missing parent relation: {technique_id}")
                if valid:
                    self.source_parents[key] = parents[0]
                    self.check(not self.source_records[parents[0]].get("x_mitre_is_subtechnique"),
                               "parent_type", f"Parent is another sub-technique: {technique_id}")
            else:
                self.check(not parent_lists[key], "unexpected_parent", f"Top-level technique has a parent: {technique_id}")
        self.result["checks"]["source_active_records"] = len(self.source_records)
        self.result["checks"]["source_parent_relationships"] = len(self.source_parents)
        self.result["checks"]["expected_platform_tactic_technique_mappings"] = len(self.expected)

    def run_ui(self, window):
        self.window = window
        try:
            self.report("3/7 Tree", "Comparing every actual UI row to independent source mappings")
            catalog = window.catalog
            procedure_counts = {}
            for domain, expected in self.source_procedures.items():
                actual_procedures = {key: {row["relationship_id"]: row for row in rows}
                                     for key, rows in catalog.procedures_by_domain[domain].items()}
                self.check(actual_procedures == expected, "procedure_index", f"Missing/extra/incorrect procedure examples: {domain}")
                self.check(all(len(rows) == len(actual_procedures[key]) for key, rows in catalog.procedures_by_domain[domain].items()),
                           "procedure_duplicates", f"Duplicate procedure relationship IDs: {domain}")
                procedure_counts[domain] = sum(len(rows) for rows in actual_procedures.values())
            self.result["checks"]["procedure_example_counts"] = procedure_counts
            self.check(set(catalog.records) == set(self.source_records), "records", "Loaded active records differ from raw STIX")
            self.check(catalog.parents == self.source_parents, "parents", "Loaded parent links differ from raw STIX")
            self.check(catalog.tactic_order == self.source_order, "tactic_order", "Matrix tactic order differs")
            actual = Counter()
            scaffolds = 0
            for row in range(window.model.rowCount()):
                platform_item = window.model.item(row)
                platform = platform_item.text()
                self.check(not platform_item.isCheckable(), "group_checkbox", f"Platform has checkbox: {platform}")
                seen_tactics = []
                def inspect(item):
                    nonlocal scaffolds
                    key = item.data(ROLE_ID)
                    if key:
                        scope_platform, slug, scope_key = item.data(ROLE_CONTEXT)
                        self.check(scope_platform == platform and scope_key == key, "context", f"Incorrect row context: {item.text()}")
                        obj = self.source_records[key]
                        self.check(item.text() == f"{external_id(obj)}  {obj['name']}", "label", f"Incorrect label: {item.text()}")
                        if item.isCheckable():
                            actual[(scope_platform, slug, key)] += 1
                        else:
                            scaffolds += 1
                            self.check((scope_platform, slug, key) not in self.expected and item.rowCount() > 0,
                                       "grouping_parent", f"Incorrect parent grouping: {item.text()}")
                        parent_key = item.parent().data(ROLE_ID) if item.parent() else None
                        self.check(parent_key == self.source_parents.get(key), "nesting", f"Incorrect nesting: {item.text()}")
                    for child_row in range(item.rowCount()):
                        inspect(item.child(child_row))
                for tactic_row in range(platform_item.rowCount()):
                    tactic_item = platform_item.child(tactic_row)
                    slug = tactic_item.data(ROLE_CONTEXT)[1]
                    seen_tactics.append(slug)
                    self.check(not tactic_item.isCheckable(), "group_checkbox", f"Tactic has checkbox: {tactic_item.text()}")
                    tactic = self.source_tactics[slug]
                    self.check(tactic_item.text() == f"{external_id(tactic)}  {tactic['name']}", "tactic_label", f"Incorrect tactic label: {slug}")
                    inspect(tactic_item)
                expected_order = [slug for slug in self.source_order if any(p == platform and s == slug for p, s, _ in self.expected)]
                self.check(seen_tactics == expected_order, "branch_tactics", f"Missing/extra/misordered tactics: {platform}")
            missing = self.expected - set(actual)
            extra = set(actual) - self.expected
            self.check(not missing, "missing_mapping", f"Missing UI mappings: {len(missing)}; sample: {sorted(missing)[:5]}")
            self.check(not extra, "extra_mapping", f"Extra UI mappings: {len(extra)}; sample: {sorted(extra)[:5]}")
            self.check(all(value == 1 for value in actual.values()), "duplicate_mapping", "Duplicate rows in a single platform/tactic branch")
            self.result["checks"].update({"ui_mappings": sum(actual.values()), "missing_mappings": len(missing),
                                         "extra_mappings": len(extra), "structural_parent_rows": scaffolds,
                                         "platforms": window.model.rowCount(), "tactic_branches": len(window.build_queue)})

            self.report("4/7 Interaction", "Checking ID search, descriptions and selection for every active record")
            for number, (key, obj) in enumerate(self.source_records.items(), 1):
                if number % 50 == 0:
                    self.report("4/7 Interaction", "Checking all active entries", number, len(self.source_records))
                items = window.items_by_id.get(key, [])
                if not self.check(bool(items), "selectable_record", f"No selectable row: {external_id(obj)}"):
                    continue
                window.proxy.setFilterFixedString(external_id(obj))
                self.check(all(window.proxy.mapFromSource(item.index()).isValid() for item in items),
                           "search", f"Search hides mapped rows: {external_id(obj)}")
                item = items[0]
                platform, slug, _ = item.data(ROLE_CONTEXT)
                window.show_record(key, platform, slug)
                text = window.details.toPlainText()
                normalized_text = " ".join(text.split())
                self.check(external_id(obj) in text and obj["name"] in text, "detail_identity", f"Missing detail identity: {external_id(obj)}")
                description = " ".join(obj["description"].split())
                self.check(description in normalized_text, "description", f"Missing/truncated description: {external_id(obj)}")
                examples = self.source_procedures["enterprise-attack"].get(key, {})
                self.check(f"Procedure Examples ({len(examples)})" in text, "procedure_heading", f"Wrong procedure count: {external_id(obj)}")
                for row in examples.values():
                    self.check(row["source_id"] in text and row["source_name"] in text,
                               "procedure_identity", f"Missing procedure source: {external_id(obj)}/{row['relationship_id']}")
                    if row["description"]:
                        self.check(" ".join(row["description"].split()) in normalized_text,
                                   "procedure_description", f"Truncated procedure text: {external_id(obj)}/{row['relationship_id']}")
                children = [child for child, parent in self.source_parents.items() if parent == self.source_parents.get(key, key)]
                self.check(all(external_id(self.source_records[child]) in text for child in children),
                           "related_details", f"Missing related sub-technique: {external_id(obj)}")
                item.setCheckState(QtCore.Qt.CheckState.Checked)
                self.check(window.selected == {key} and window.selection_list.count() == 1,
                           "selection_dedup", f"Selection not deduplicated: {external_id(obj)}")
                self.check(all(other.checkState() == QtCore.Qt.CheckState.Checked for other in items),
                           "selection_sync", f"Checkboxes not synchronized: {external_id(obj)}")
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
                self.check(not window.selected and all(other.checkState() == QtCore.Qt.CheckState.Unchecked for other in items),
                           "deselection_sync", f"Unchecked state not synchronized: {external_id(obj)}")
            window.proxy.setFilterFixedString("no-such-technique-zzzz")
            self.check(window.proxy.rowCount() == 0, "empty_search", "Unmatched search shows rows")
            window.proxy.setFilterFixedString("")
            self.result["checks"]["active_record_interactions_verified"] = len(self.source_records)

            self.report("5/7 Navigation", "Checking all six new category lists against raw source objects")
            category_counts = {}
            preserved_selection_key = next(iter(window.items_by_id))
            window.items_by_id[preserved_selection_key][0].setCheckState(QtCore.Qt.CheckState.Checked)
            for category, kinds in BROWSE_CATEGORIES.items():
                window.navigation_buttons[category].click()
                self.check(window.active_category == category and window.explorer_stack.currentWidget() == window.library_tree,
                           "category_navigation", f"Category button does not switch: {category}")
                expected_library = {(domain, key) for domain, records in self.source_library.items()
                                    for key, obj in records.items() if obj.get("type") in kinds}
                actual_library = {(item.data(ROLE_CONTEXT)[0], item.data(ROLE_ID)) for item in window.library_items[category]}
                self.check(actual_library == expected_library, "category_coverage", f"Missing/extra category records: {category}")
                self.check(len(actual_library) == len(window.library_items[category]), "category_duplicates", f"Duplicate category rows: {category}")
                self.check(window.selected == {preserved_selection_key}, "category_selection_preservation", f"TTP selection lost in {category}")
                category_counts[category] = len(actual_library)
                for item in window.library_items[category]:
                    domain, kind, key = item.data(ROLE_CONTEXT)
                    obj = self.source_library[domain][key]
                    self.check(not item.isCheckable(), "library_checkbox", f"Library record has scenario checkbox: {category}/{key}")
                    self.check(item.text() == f"{external_id(obj)}  {obj.get('name', key)}".strip(),
                               "library_label", f"Incorrect library label: {category}/{key}")
                samples = window.library_items[category][:1] + window.library_items[category][-1:]
                for item in samples:
                    domain, kind, key = item.data(ROLE_CONTEXT)
                    obj = self.source_library[domain][key]
                    window.library_proxy.setFilterFixedString(external_id(obj) or obj.get("name", key))
                    index = window.library_proxy.mapFromSource(item.index())
                    self.check(index.isValid(), "library_search", f"Search does not find {category}/{key}")
                    window.library_tree.setCurrentIndex(index)
                    self.check(obj.get("name", key) in window.details.toPlainText() and DOMAIN_LABELS[domain] in window.crumb.text(),
                               "library_details", f"Incorrect category details: {category}/{key}")
                    if obj.get("description"):
                        self.check(" ".join(obj["description"].split()) in " ".join(window.details.toPlainText().split()),
                                   "library_description", f"Truncated library description: {category}/{key}")
                window.library_proxy.setFilterFixedString("no-such-library-record-zzzz")
                self.check(window.library_proxy.rowCount() == 0, "library_empty_search", f"Unmatched library search shows rows: {category}")
                window.library_proxy.setFilterFixedString("")
            self.result["checks"]["navigation_category_counts"] = category_counts
            self.check(category_counts["Assets"] == 18, "ics_assets", "Current snapshot should expose 18 ICS assets")
            window.navigation_buttons["TTP"].click()
            self.check(window.active_category == "TTP" and window.selected == {preserved_selection_key},
                       "ttp_navigation", "Returning to TTP loses the active view or selection")
            window.clear_selection()
            window.proxy.setFilterFixedString("")
            self.report("5/7 Scheduled Job", "Checking full T1053 family and all platform/tactic branches")
            by_external = {external_id(obj): key for key, obj in self.source_records.items()}
            parent_key = by_external["T1053"]
            children = sorted((key for key, parent in self.source_parents.items() if parent == parent_key),
                              key=lambda key: external_id(self.source_records[key]))
            self.check({external_id(self.source_records[key]) for key in children} ==
                       {"T1053.002", "T1053.003", "T1053.005", "T1053.006", "T1053.007"},
                       "scheduled_family", "Unexpected active T1053 family for the current snapshot")
            windows_children = {external_id(self.source_records[key]) for key in children
                                if ("Windows", "execution", key) in self.expected}
            self.check(windows_children == {"T1053.002", "T1053.005"}, "scheduled_windows", "Wrong Windows T1053 children")
            for key in children:
                obj = self.source_records[key]
                self.result["scheduled_task_job"].append({"id": external_id(obj), "name": obj["name"],
                    "platforms": obj["x_mitre_platforms"], "windows_execution": ("Windows", "execution", key) in self.expected,
                    "actual_ui_occurrences": len(window.items_by_id[key])})
            parent_item = next(item for item in window.items_by_id[parent_key]
                               if tuple(item.data(ROLE_CONTEXT)[:2]) == ("Windows", "execution"))
            parent_item.setCheckState(QtCore.Qt.CheckState.Checked)
            self.check(window.selected == {parent_key}, "parent_selection", "Checking parent auto-selects children")
            window.clear_selection()
            window.show_record(parent_key, "Windows", "execution")
            self.check("2 of 5" in window.details.toPlainText(), "branch_summary", "Missing Windows sub-technique completeness explanation")
            cron_key = by_external["T1053.003"]
            window.open_detail_link(QtCore.QUrl(f"attack:{cron_key}"))
            self.check(window.detail_context[0] != "Windows" and window.tree.currentIndex().data(ROLE_ID) == cron_key,
                       "cross_platform_link", "Related Cron link navigates to incorrect platform")
            at_key = by_external["T1053.002"]
            at_item = next(item for item in window.items_by_id[at_key]
                           if tuple(item.data(ROLE_CONTEXT)[:2]) == ("Windows", "execution"))
            index = window.proxy.mapFromSource(at_item.index())
            window.tree.collapseAll()
            parent_index = index.parent()
            while parent_index.isValid():
                window.tree.expand(parent_index)
                parent_index = parent_index.parent()
            window.tree.setCurrentIndex(index)
            window.tree.scrollTo(index)
            window.show_record(at_key, "Windows", "execution")
            self.report("5/7 Clipboard", "Checking copy buttons and procedure-source navigation")
            clipboard = QtWidgets.QApplication.clipboard()
            previous_mime = QtCore.QMimeData()
            original = clipboard.mimeData()
            if original is not None:
                for mime_type in original.formats():
                    previous_mime.setData(mime_type, original.data(mime_type))
            try:
                sample_key = by_external["T1047"]
                obj = self.source_records[sample_key]
                window.show_record(sample_key, "Windows", "execution")
                window.details.copy_title_button.click()
                self.check(clipboard.text() == obj["name"], "copy_title", "Title button copied wrong content")
                window.details.copy_description_button.click()
                self.check(clipboard.text() == obj["description"], "copy_description", "Description button copied wrong or partial content")
                window.details.verticalScrollBar().setValue(0)
                window.details.position_copy_buttons()
                self.check(window.details.copy_title_button.isVisible(), "copy_title_position", "Title copy button is not visible beside heading")
                cursor = window.details.document().find("Description")
                rect = window.details.cursorRect(cursor)
                window.details.verticalScrollBar().setValue(window.details.verticalScrollBar().value() + rect.top() - 80)
                window.details.position_copy_buttons()
                self.check(window.details.copy_description_button.isVisible(), "copy_description_position", "Description copy button is not visible beside heading")
                old_size = window.size()
                window.resize(1000, 920)
                longest = max(window.catalog.records, key=lambda key: len(window.catalog.records[key]["name"]))
                window.show_record(longest)
                QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                window.details.verticalScrollBar().setValue(0)
                window.details.position_copy_buttons()
                self.check(window.details.copy_title_button.isVisible(), "copy_narrow_view", "Long title loses its copy button at narrow width")
                window.resize(old_size)
                row = catalog.procedures_by_domain["enterprise-attack"][sample_key][0]
                window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{row['source_ref']}"))
                self.check(row["source_name"] in window.details.toPlainText() and window.active_category != "TTP",
                           "procedure_navigation", "Procedure source link does not open its record")
                domain, kind, key = window.library_tree.currentIndex().data(ROLE_CONTEXT)
                library_obj = catalog.objects_by_domain[domain][key]
                window.details.copy_title_button.click()
                self.check(clipboard.text() == library_obj["name"], "library_copy_title", "Library title copy is stale")
                if library_obj.get("description"):
                    window.details.copy_description_button.click()
                    self.check(clipboard.text() == library_obj["description"], "library_copy_description", "Library description copy is stale")
                window.switch_category("TTP")
                window.tree.setCurrentIndex(window.proxy.mapFromSource(window.platform_items["Windows"].index()))
                self.check(not window.details.copy_content, "copy_group_reset", "Navigation heading retains stale copy contents")
            finally:
                if previous_mime.formats():
                    clipboard.setMimeData(previous_mime)
                else:
                    clipboard.clear()
            self.result["checks"]["title_description_clipboard_verified"] = True
            window.tree.setCurrentIndex(index)
            window.show_record(at_key, "Windows", "execution")
            self.report("6/7 Display", "Checking explicit selected-text contrast and taking preview")
            for group in (QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorGroup.Inactive):
                self.check(window.tree.palette().color(group, QtGui.QPalette.ColorRole.HighlightedText).name() == "#ffffff",
                           "selected_contrast", "Selected text is not white")
            self.output.mkdir(parents=True, exist_ok=True)
            QtCore.QTimer.singleShot(200, self.finish)
        except Exception as error:
            self.result["errors"].append({"check": "audit_exception", "message": f"{type(error).__name__}: {error}"})
            self.finish()

    def finish(self):
        try:
            if self.window:
                saved = self.window.grab().save(str(self.output / "scheduled-job-preview.png"))
                self.check(saved, "screenshot", "Could not save preview image")
                if self.window.loaded_ok:
                    self.window.switch_category("TTP")
                    candidates = [key for key, obj in self.window.catalog.records.items()
                                  if not obj.get("x_mitre_is_subtechnique") and key not in self.window.children_by_parent
                                  and self.window.catalog.procedures_by_domain["enterprise-attack"].get(key)]
                    technique = min(candidates, key=lambda key: len(self.window.catalog.records[key].get("description", "")))
                    item = self.window.items_by_id[technique][0]
                    index = self.window.proxy.mapFromSource(item.index())
                    parent_index = index.parent()
                    while parent_index.isValid():
                        self.window.tree.expand(parent_index)
                        parent_index = parent_index.parent()
                    self.window.tree.setCurrentIndex(index)
                    self.window.tree.scrollTo(index)
                    platform, slug, _ = item.data(ROLE_CONTEXT)
                    self.window.show_record(technique, platform, slug)
                    self.window.output_panel.hide()
                    self.window.details.verticalScrollBar().setValue(0)
                    QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                    self.window.details.position_copy_buttons()
                    saved = self.window.grab().save(str(self.output / "procedure-preview.png"))
                    self.check(saved, "procedure_screenshot", "Could not save procedure/copy preview")
                    self.window.output_panel.show()
                    self.window.navigation_buttons["Assets"].click()
                    asset = self.window.library_items["Assets"][0]
                    index = self.window.library_proxy.mapFromSource(asset.index())
                    self.window.library_tree.setCurrentIndex(index)
                    self.window.library_tree.expandAll()
                    self.window.library_tree.scrollTo(index)
                    self.window.report("Audit complete: navigation and catalog checks finished", 1, 1)
                    QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                    saved = self.window.grab().save(str(self.output / "navigation-preview.png"))
                    self.check(saved, "navigation_screenshot", "Could not save navigation preview image")
            self.result["status"] = "PASS" if not self.result["errors"] else "FAIL"
            self.result["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
            self.report("7/7 Report", f"Writing audit reports: {self.result['status']}")
            self.output.mkdir(parents=True, exist_ok=True)
            (self.output / "catalog-audit.json").write_text(json.dumps(self.result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            checks = self.result["checks"]
            rows = ["| ID | Name | Platforms | Windows / Execution |", "| --- | --- | --- | --- |"]
            for entry in self.result["scheduled_task_job"]:
                rows.append(f"| {entry['id']} | {entry['name']} | {', '.join(entry['platforms'])} | "
                            f"{'Mapped' if entry['windows_execution'] else 'Other platform'} |")
            md = (f"# ATT&CK Catalog Audit: {self.result['status']}\n\n"
                  f"Snapshot: v{self.result.get('attack_version', 'unknown')}\n\n"
                  "Scope: downloaded artifact integrity and structural validation for Enterprise, Mobile, and ICS; "
                  "full UI mapping, metadata, search, detail rendering, parent relationships, and checkbox interactions for Enterprise. "
                  "All six library sections are checked across Enterprise, Mobile, and ICS; Mobile/ICS TTP matrix views are not implemented.\n\n"
                  "## Results\n\n" + "\n".join(f"- {key}: {value}" for key, value in checks.items())
                  + "\n\n## Scheduled Task/Job\n\n" + "\n".join(rows)
                  + "\n\nThe Windows branch correctly shows At and Scheduled Task. Other children are available "
                  "under their own mapped platforms. The detail panel lists the full active family. "
                  "Revoked/deprecated records are excluded by design.\n\n"
                  "## Findings\n\n" + ("\n".join(f"- {error['check']}: {error['message']}" for error in self.result["errors"])
                                        or "No missing or extra mappings, parent links, or descriptions were found by these checks.")
                  + "\n\nSelected text uses explicit white foreground colors and a dark Qt palette. "
                  "See `scheduled-job-preview.png` for the rendered At selection and all five active sibling sub-techniques. See `navigation-preview.png` for the rail and ICS asset browser; `procedure-preview.png` shows Procedure Examples and native copy buttons.\n")
            (self.output / "catalog-audit.md").write_text(md, encoding="utf-8")
            print(f"[Audit] {self.result['status']}: {len(self.result['errors'])} errors", flush=True)
        except Exception as error:
            self.result["status"] = "FAIL"
            print(f"[Audit] FAIL writing reports: {error}", flush=True)
        finally:
            app = QtWidgets.QApplication.instance()
            if self.window:
                self.window.close()
            if app:
                app.exit(0 if self.result["status"] == "PASS" else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data" / "attack")
    parser.add_argument("--report-dir", type=Path, default=Path(__file__).resolve().parent / "artifacts")
    args = parser.parse_args()
    audit = Audit(args.data_dir.expanduser().resolve(), args.report_dir.expanduser().resolve())
    print(f"Python executable: {Path(sys.executable).resolve()}", flush=True)
    try:
        audit.read_sources()
    except Exception as error:
        audit.result["errors"].append({"check": "source_exception", "message": f"{type(error).__name__}: {error}"})
        audit.finish()
        return 1
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(audit.root, audit.root / "latest.json")
    window.ready.connect(lambda: audit.run_ui(window))
    def load_failed(message):
        audit.window = window
        audit.result["errors"].append({"check": "ui_load", "message": message})
        audit.finish()
    window.loader.failed.connect(load_failed)
    window.show()
    exit_code = app.exec()
    if window.loader.isRunning():
        window.loader.requestInterruption()
        window.loader.wait()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())





