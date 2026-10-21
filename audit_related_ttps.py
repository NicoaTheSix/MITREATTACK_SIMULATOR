"""Audit library relationship tables and global TTP search. Workflow: README.md."""
from collections import defaultdict
from pathlib import Path
import json
import csv
import sys
import time

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from attack_catalog import DOMAIN_LABELS, external_id, local_path, index_source_techniques
from main import MainWindow, ROLE_ID, configure_application
from scripts.download_attack_data import write_json

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "attack"
OUT = ROOT / "artifacts"
REPORT = OUT / "related-ttp-audit.json"
JSON_EXPORT = OUT / "bulk-ttps-example.json"
CSV_EXPORT = OUT / "bulk-ttps-example.csv"
SCREENS = {name: OUT / f"{name.lower()}-techniques-preview.png"
           for name in ("Mitigations", "Software", "Campaigns")}
checks = []


def log(message, current=0, total=0):
    print(message + (f" ({current}/{total})" if total else ""), flush=True)


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def wait(condition, label):
    deadline = time.monotonic() + 60
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError(label)
        QtTest.QTest.qWait(20)


def visible_ids(window):
    keys = set()
    def visit(parent=QtCore.QModelIndex()):
        for row in range(window.proxy.rowCount(parent)):
            index = window.proxy.index(row, 0, parent)
            key = index.data(ROLE_ID)
            if key:
                keys.add(key)
            visit(index)
    visit()
    return keys


def hrefs(browser):
    links = []
    block = browser.document().begin()
    while block.isValid():
        fragment = block.begin()
        while not fragment.atEnd():
            fmt = fragment.fragment().charFormat()
            if fmt.isAnchor():
                links.append(fmt.anchorHref())
            fragment += 1
        block = block.next()
    return links


def main():
    pointer_path = DATA / "latest.json"
    log(f"Input file: {pointer_path}")
    for path in (REPORT, JSON_EXPORT, CSV_EXPORT, *SCREENS.values()):
        log(f"Output file: {path}")
    log("[Related audit 1/7] Deriving reference relationships independently from raw STIX")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
    expected, source_records, counts = {}, {}, {}
    for domain, field in (("enterprise-attack", "enterprise_bundle"),
                          ("mobile-attack", "mobile_bundle"), ("ics-attack", "ics_bundle")):
        path = local_path(DATA, pointer[field])
        log(f"Input file: {path}")
        objects = json.loads(path.read_text(encoding="utf-8-sig"))["objects"]
        records = {obj["id"]: obj for obj in objects if not obj.get("revoked")
                   and not obj.get("x_mitre_deprecated") and obj.get("type") != "relationship"}
        source_records[domain] = records
        rows = defaultdict(dict)
        for edge in objects:
            if edge.get("type") != "relationship" or edge.get("revoked") or edge.get("x_mitre_deprecated"):
                continue
            source, target = records.get(edge.get("source_ref"), {}), records.get(edge.get("target_ref"), {})
            matches = ((source.get("type") == "course-of-action" and edge.get("relationship_type") == "mitigates")
                       or (source.get("type") in {"intrusion-set", "malware", "tool", "campaign"} and edge.get("relationship_type") == "uses"))
            if matches and target.get("type") == "attack-pattern":
                rows[source["id"]][edge["id"]] = {
                    "relationship_id": edge["id"], "target_ref": target["id"],
                    "description": edge.get("description", ""), "references": edge.get("external_references", [])}
        expected[domain] = dict(rows)
        counts[domain] = sum(map(len, rows.values()))
        log(f"[Related audit 1/7] {DOMAIN_LABELS[domain]} reference complete", counts[domain], counts[domain])
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, pointer_path)
    window.resize(1700, 1000)
    window.show()
    wait(lambda: window.loaded_ok, "catalog loading")
    catalog = window.catalog
    log("[Related audit 2/7] Checking every source/target edge, description and reference")
    for domain, rows in expected.items():
        actual = catalog.techniques_by_source[domain]
        legacy = {key for key in actual if source_records[domain][key].get('type') in
                  {'course-of-action','intrusion-set','malware','tool','campaign'}}
        check(legacy == set(rows), f"{domain}: exact legacy source membership (new source kinds audited separately)")
        for key, edges in rows.items():
            check({row["relationship_id"]: row for row in actual[key]} == edges,
                  f"{domain}: complete relationships for {external_id(source_records[domain][key])}")
            ids = [external_id(source_records[domain][row["target_ref"]]) for row in actual[key]]
            check(ids == sorted(ids), f"{domain}/{key}: technique ordering")
    # Exercise edge lifecycle filtering independently of the downloaded release.
    source = {"id": "source", "type": "course-of-action"}
    target = {"id": "target", "type": "attack-pattern"}
    edge = {"id": "edge", "type": "relationship", "relationship_type": "mitigates",
            "source_ref": "source", "target_ref": "target"}
    for field in ("revoked", "x_mitre_deprecated"):
        check(not index_source_techniques([dict(edge, **{field: True})], {"source": source, "target": target}, log,
                                         "enterprise-attack")[0], f"excludes {field} edge")
    check(not index_source_techniques([edge], {"source": source}, log, "enterprise-attack")[0], "excludes absent target")
    log("[Related audit 3/7] Opening each domain/type table and following its local links")
    headings = {"course-of-action": "Techniques Addressed by Mitigation",
                "malware": "Techniques Used by Software", "tool": "Techniques Used by Software",
                "campaign": "Techniques Used by Campaign", "intrusion-set": "Techniques Used by Group"}
    preview_keys = {}
    for domain, rows in expected.items():
        for kind, heading in headings.items():
            candidates = [key for key in rows if source_records[domain][key]["type"] == kind]
            if not candidates:
                continue
            key = next((key for key in candidates if external_id(source_records[domain][key]) == "M1036"), candidates[0])
            window.open_detail_link(QtCore.QUrl(f"library:{domain}/{key}"))
            plain = window.details.toPlainText()
            check(f"{heading} ({len(rows[key])})" in plain, f"{domain}/{kind}: table count/heading")
            check(all(label in plain for label in ("Domain", "ID", "Name", "Use")), f"{domain}/{kind}: table columns")
            anchors = hrefs(window.details)
            for row in rows[key].values():
                check(f"technique:{domain}/{row['target_ref']}" in anchors, f"{domain}/{kind}/{row['relationship_id']}: local technique link")
                if row["description"]:
                    check(" ".join(row["description"][:80].split()) in " ".join(plain.split()),
                          f"{domain}/{kind}/{row['relationship_id']}: original use text")
            parent_row = next((row for row in rows[key].values() if row["target_ref"] in catalog.parents_by_domain[domain]), None)
            if parent_row:
                parent = source_records[domain][catalog.parents_by_domain[domain][parent_row["target_ref"]]]
                check(f"Parent: {external_id(parent)} {parent['name']}" in plain, f"{domain}/{kind}: parent name")
            original_clipboard = QtCore.QMimeData()
            current_clipboard = app.clipboard().mimeData()
            has_clipboard_data = current_clipboard is not None and bool(current_clipboard.formats())
            if current_clipboard is not None:
                for mime in current_clipboard.formats():
                    original_clipboard.setData(mime, current_clipboard.data(mime))
            try:
                window.details.copy_title_button.click()
                check(app.clipboard().text() == source_records[domain][key]["name"], f"{domain}/{kind}: title copy retained")
            finally:
                if has_clipboard_data:
                    app.clipboard().setMimeData(original_clipboard)
                else:
                    app.clipboard().clear()
            target_key = next(iter(rows[key].values()))["target_ref"]
            window.details.anchorClicked.emit(QtCore.QUrl(f"technique:{domain}/{target_key}"))
            check(source_records[domain][target_key]["name"] in window.details.toPlainText(), f"{domain}/{kind}: opens technique details")
            check(external_id(source_records[domain][target_key]) in window.crumb.text(), f"{domain}/{kind}: correct domain/technique")
            if domain != "enterprise-attack":
                check("Back to source entry" in window.details.toPlainText(), f"{domain}/{kind}: return link")
                window.details.anchorClicked.emit(QtCore.QUrl(f"library:{domain}/{key}"))
                check(heading in window.details.toPlainText(), f"{domain}/{kind}: returns to table")
            if domain == "enterprise-attack":
                category = ("Mitigations" if kind == "course-of-action" else "Campaigns" if kind == "campaign"
                            else "Groups" if kind == "intrusion-set" else "Software")
                if category in SCREENS:
                    preview_keys.setdefault(category, key)
    empty_key = next((key for key, obj in source_records["enterprise-attack"].items()
                      if obj.get("type") in headings and key not in expected["enterprise-attack"]), None)
    if empty_key:
        window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{empty_key}"))
        check("No active related techniques" in window.details.toPlainText(), "explicit empty relationship state")
    log("[Related audit 4/7] Checking category search visibility and native multi-word input")
    task = next(key for key, obj in catalog.records.items() if external_id(obj) == "T1053.005")
    window.items_by_id[task][0].setCheckState(QtCore.Qt.CheckState.Checked)
    for category in ("Mitigations", "Assets", "Detections", "Groups", "Software", "Campaigns"):
        window.switch_category(category)
        check(window.ttp_search.isHidden() and window.search.isVisible(), f"{category}: only category search visible")
        window.focus_search()
        check(app.focusWidget() is window.search, f"{category}: search shortcut focuses category field")
        # Even a stale/programmatic event in the hidden field must not leave this category.
        window.ttp_search.setText("t1053.005")
        window.apply_ttp_search()
        check(window.active_category == category, f"{category}: hidden TTP search cannot switch category")
        check(window.selected == {task}, f"{category}: selections preserved")
    window.switch_category("Mitigations")
    window.search.setFocus()
    QtTest.QTest.keyClicks(window.search, "Account Use ")
    QtTest.QTest.qWait(260)
    check(window.search.text() == "Account Use ", "category search retains paused trailing space")
    QtTest.QTest.keyClicks(window.search, "Policies")
    QtTest.QTest.qWait(260)
    check(window.search.text() == "Account Use Policies", "native multi-word category query")
    check(window.library_proxy.rowCount() > 0, "multi-word mitigation name matches")
    window.switch_category("TTP")
    check(window.ttp_search.isVisible() and window.search.isHidden(), "TTP: only TTP search visible")
    window.focus_search()
    check(app.focusWidget() is window.ttp_search, "TTP search shortcut focus")
    QtTest.QTest.keyClicks(window.ttp_search, "t1053.005")
    QtTest.QTest.keyClick(window.ttp_search, QtCore.Qt.Key.Key_Return)
    check(visible_ids(window) == {task, catalog.parents[task]}, "case-insensitive ID search retains parent")
    window.ttp_search.clear()
    QtTest.QTest.keyClicks(window.ttp_search, "Scheduled ")
    QtTest.QTest.qWait(260)
    check(window.ttp_search.text() == "Scheduled ", "TTP search retains paused trailing space")
    check(window.ttp_search.cursorPosition() == len("Scheduled "), "debounced search preserves cursor")
    QtTest.QTest.keyClicks(window.ttp_search, "Task")
    wait(lambda: window.proxy.filterRegularExpression().match("Scheduled Task").hasMatch(), "debounced name search")
    check(window.ttp_search.text() == "Scheduled Task", "native multi-word TTP query")
    check(task in visible_ids(window), "name search")
    window.ttp_search.setText("  Scheduled Task  ")
    window.ttp_search.setCursorPosition(7)
    QtTest.QTest.qWait(260)
    check(window.ttp_search.text() == "  Scheduled Task  ", "leading/trailing spaces remain editable")
    check(window.ttp_search.cursorPosition() == 7, "filtering preserves middle cursor position")
    check(task in visible_ids(window), "filter ignores outer spaces without rewriting input")
    window.ttp_search.setText("Scheduled  Task")
    QtTest.QTest.qWait(260)
    check(window.ttp_search.text() == "Scheduled  Task", "repeated internal spaces preserved")
    window.ttp_search.setText("missing-ttp-zzzzz")
    window.apply_ttp_search()
    check(window.proxy.rowCount() == 0, "unmatched search is empty")
    window.ttp_search.clear()
    window.apply_ttp_search()
    check(visible_ids(window) == set(catalog.records), "clearing search restores all techniques")
    window.switch_category("Software")
    window.search.setText("S0002")
    window.apply_search()
    check(window.active_category == "Software" and not window.ttp_search.text(), "category filtering remains independent")
    log("[Related audit 5/7] Adding every directly related TTP through the native button")
    window.matrix_view.set_catalog(catalog, window.selected)
    wait(lambda: not window.matrix_view.building, "matrix checkbox models")
    bulk_sources = {}
    for kind in ("malware", "tool", "campaign", "intrusion-set"):
        key = next(key for key, edges in expected["enterprise-attack"].items()
                   if source_records["enterprise-attack"][key]["type"] == kind and len(edges) > 1)
        bulk_sources[kind] = key
        targets = {row["target_ref"] for row in expected["enterprise-attack"][key].values()}
        extra = next(key for key in catalog.records if key not in targets)
        window.clear_selection()
        window.items_by_id[extra][0].setCheckState(QtCore.Qt.CheckState.Checked)
        window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{key}"))
        category = window.active_category
        check(window.bulk_action_bar.isVisible() and window.bulk_add_button.isEnabled(), f"{kind}: bulk action enabled")
        check(window.bulk_add_button.text() == f"Add all TTPs ({len(targets)})", f"{kind}: unique target count")
        QtTest.QTest.mouseClick(window.bulk_add_button, QtCore.Qt.MouseButton.LeftButton)
        wanted = targets | {extra}
        check(window.selected == wanted, f"{kind}: exact direct targets and existing selection retained")
        check(window.current_document.selected == wanted, f"{kind}: document selection synchronized")
        check(window.selection_list.count() == len(wanted), f"{kind}: unique Selected Techniques rows")
        check(window.current_document.dirty, f"{kind}: marks document changed")
        check(window.active_category == category and window.bulk_action_bar.isVisible(), f"{kind}: browsing context retained")
        check(all(item.checkState() == QtCore.Qt.CheckState.Checked for target in wanted for item in window.items_by_id[target]),
              f"{kind}: every sidebar occurrence checked")
        check(window.matrix_view.selected == wanted and all(item.checkState(0) == QtCore.Qt.CheckState.Checked
              for target in wanted for item in window.matrix_view.items_by_id[target]), f"{kind}: matrix checkboxes synchronized")
        fingerprint = window.current_document.fingerprint()
        window.current_document.exported_fingerprint = fingerprint
        QtTest.QTest.mouseClick(window.bulk_add_button, QtCore.Qt.MouseButton.LeftButton)
        check(window.selected == wanted and window.current_document.fingerprint() == fingerprint and not window.current_document.dirty,
              f"{kind}: repeated click is idempotent and retains exported state")
    window.export_current_document(JSON_EXPORT)
    window.export_current_document(CSV_EXPORT, "csv")
    expected_ids = sorted(external_id(catalog.records[key]) for key in window.selected)
    log(f"Input file: {JSON_EXPORT}")
    check(json.loads(JSON_EXPORT.read_text(encoding="utf-8"))["selected_technique_ids"] == expected_ids,
          "bulk additions export exact IDs to JSON")
    log(f"Input file: {CSV_EXPORT}")
    with CSV_EXPORT.open(encoding="utf-8-sig", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    check([row["technique_id"] for row in csv_rows] == expected_ids, "bulk additions export exact IDs to CSV")
    for row in csv_rows:
        parent = catalog.records.get(catalog.parents.get(row["stix_id"]))
        check(row["parent_technique_name"] == (parent["name"] if parent else ""), f"bulk CSV parent name {row['technique_id']}")
    first_document = window.current_document
    first_selection = set(window.selected)
    window.new_document()
    check(not window.selected, "new document is independent of bulk additions")
    key = bulk_sources["campaign"]
    window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{key}"))
    QtTest.QTest.mouseClick(window.bulk_add_button, QtCore.Qt.MouseButton.LeftButton)
    second_selection = {row["target_ref"] for row in expected["enterprise-attack"][key].values()}
    check(window.selected == second_selection and first_document.selected == first_selection,
          "bulk addition targets only the active document")
    window.document_tabs.setCurrentIndex(0)
    check(window.selected == first_selection and window.matrix_view.selected == first_selection, "document switch restores bulk selection")
    for domain in ("mobile-attack", "ics-attack"):
        key = next(key for key in expected[domain] if source_records[domain][key]["type"] in {"malware", "tool", "campaign", "intrusion-set"})
        window.open_detail_link(QtCore.QUrl(f"library:{domain}/{key}"))
        check(window.bulk_action_bar.isVisible() and not window.bulk_add_button.isEnabled(), f"{domain}: unsupported selection disabled")
        window.add_source_ttps(domain, key)
        check(window.selected == first_selection, f"{domain}: no cross-domain selection")
    key = preview_keys["Mitigations"]
    window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{key}"))
    check(window.bulk_action_bar.isVisible() and window.bulk_add_button.isEnabled() and window.bulk_remove_button.isEnabled(), "mitigations expose add/remove source actions")
    window.add_source_ttps("enterprise-attack", key)
    mitigation_targets = {row['target_ref'] for row in expected['enterprise-attack'][key].values()}
    check(window.selected == first_selection | mitigation_targets, 'mitigation addition keeps existing selections')
    window.change_source_ttps('enterprise-attack',key,'remove')
    check(window.selected == first_selection - mitigation_targets, 'mitigation removal affects only mapped targets')
    window.selected = set(first_selection)
    window.refresh_selection()
    window.add_source_ttps("enterprise-attack", "missing-entry")
    check(window.selected == first_selection, "missing sources preserve selection")
    window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{bulk_sources['campaign']}"))
    window.show_record(task)
    check(window.bulk_add_button.isHidden() and window.bulk_source_context is None, "technique navigation clears stale source action")
    window.loaded_ok = False
    window.add_source_ttps("enterprise-attack", bulk_sources["campaign"])
    window.loaded_ok = True
    check(window.selected == first_selection, "catalog rebuild blocks bulk action")
    if empty_key and source_records["enterprise-attack"][empty_key]["type"] != "course-of-action":
        window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{empty_key}"))
        check(not window.bulk_add_button.isEnabled(), "empty source action disabled")
    log("[Related audit 6/7] Capturing related technique pages")
    window.output_panel.hide()
    for category, key in preview_keys.items():
        window.open_detail_link(QtCore.QUrl(f"library:enterprise-attack/{key}"))
        window.details.scrollToAnchor("related-ttps")
        QtTest.QTest.qWait(160)
        check(window.grab().save(str(SCREENS[category])), f"{category}: screenshot saved")
    check(window.selected == first_selection, "browsing leaves bulk selection intact")
    window.confirm_studio_changes = lambda *_: "discard"
    window.close()
    log("[Related audit 7/7] Writing report")
    write_json(REPORT, {"status": "PASS", "attack_version": catalog.version, "checks": checks,
                        "relationship_counts": counts, "screenshots": {key: str(value) for key, value in SCREENS.items()}})
    log(f"[Related audit] PASS: {len(checks)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
