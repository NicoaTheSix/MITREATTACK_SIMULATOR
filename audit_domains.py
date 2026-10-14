"""Verify three-domain document workflows against local STIX data. Flow: README.md."""
from pathlib import Path
import csv
import json
import sys
import time
import uuid
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets
from attack_catalog import DOMAIN_LABELS, DOMAIN_KILL_CHAINS, external_id, load_catalog
from attack_matrix import matrix_columns
from attack_versions import snapshot_pointer
from main import MainWindow, configure_application
from navigator_dialogs import VersionCompareDialog, AnnotationDialog
from navigator_integration import document_layer, read_layers, imported_document, compare_documents, update_annotation
from ttp_documents import TTPDocument, document_payload
from version_dialog import VersionDialog, VersionWorker

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "attack"
OUTPUT = ROOT / "artifacts" / ("domain-audit-" + uuid.uuid4().hex)
REPORT = ROOT / "artifacts" / "domain-audit.json"
checks = []


def log(message, current=0, total=0):
    print(message + (f" ({current}/{total})" if total else ""), flush=True)


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def wait(condition, description):
    end = time.monotonic() + 180
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError(description)
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def main():
    log(f"Input file: {DATA / 'latest.json'}")
    log(f"Input file: {DATA / 'active.json'}")
    log(f"Output report: {REPORT}")
    log(f"Output directory: {OUTPUT}")
    for domain in DOMAIN_LABELS:
        for suffix in ("json", "csv", "navigator.json", "png"):
            log(f"Output file: {OUTPUT / (domain + '.' + suffix)}")
    log(f"Output file: {OUTPUT / 'domain-menu.png'}")
    OUTPUT.mkdir(parents=True)
    pointers = {path: path.read_bytes() for path in (DATA / "latest.json", DATA / "active.json") if path.exists()}
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / "latest.json")
    window.show()
    wait(lambda: window.loaded_ok, "startup")
    catalog = window.catalog
    original = window.current_document
    selections = {}
    log("[Domain audit 1/6] Independent STIX projections and matrix mappings", 0, 3)
    pointer = snapshot_pointer(DATA, catalog.version)
    for number, domain in enumerate(DOMAIN_LABELS, 1):
        projected = catalog.for_domain(domain)
        path = DATA / pointer[domain.split('-')[0] + '_bundle']
        log(f"Input file: {path.resolve()}")
        raw = json.loads(path.read_text(encoding="utf-8"))["objects"]
        records = {obj["id"]: obj for obj in raw if obj.get("type") == "attack-pattern"
                   and not obj.get("revoked") and not obj.get("x_mitre_deprecated")
                   and domain in obj.get("x_mitre_domains", [])}
        check(projected.records == records, f"{domain}: exact active source records")
        expected = set()
        for key, obj in records.items():
            for platform in obj.get("x_mitre_platforms", []) or ["Unspecified Platform"]:
                for phase in obj.get("kill_chain_phases", []):
                    if phase.get("kill_chain_name") == DOMAIN_KILL_CHAINS[domain]:
                        expected.add((platform, phase["phase_name"], key))
        actual = {(platform, slug, key) for platform, tactics in projected.groups.items()
                  for slug, keys in tactics.items() for key in keys}
        check(actual == expected, f"{domain}: platform/tactic mappings match source kill chain")
        matrix = {(slug, row["key"]) for slug, rows in matrix_columns(projected) for row in rows if row["selectable"]}
        matrix |= {(slug, key) for slug, rows in matrix_columns(projected) for row in rows for key in row["children"]}
        check(matrix == {(slug, key) for _, slug, key in expected}, f"{domain}: all-platform matrix matches raw mappings")
        check(projected.for_domain("enterprise-attack").records == catalog.records, f"{domain}: Enterprise projection recoverable")
        log("[Domain audit 1/6] Source projection verified", number, 3)
    log("[Domain audit 2/6] Native right-click switching, selection, search and exports", 0, 3)
    for number, domain in enumerate(DOMAIN_LABELS, 1):
        window.show_document_context_menu(window.document_tabs.tabRect(0).center())
        menu = window.document_context_menu
        domain_menu = next(action.menu() for action in menu.actions() if action.text() == "ATT&CK Domain")
        action = next(action for action in domain_menu.actions() if action.text() == DOMAIN_LABELS[domain])
        check(action.isEnabled() and action.isChecked() == (window.catalog.domain == domain), f"{domain}: menu availability/current mark")
        action.trigger()
        menu.close()
        wait(lambda: window.loaded_ok, "domain tree")
        check(window.catalog.domain == domain and original.catalog.domain == domain, f"{domain}: right-click changes target domain")
        check(set(window.items_by_id) == set(window.catalog.records), f"{domain}: every active TTP selectable in actual tree")
        key = next(iter(window.catalog.parents), next(iter(window.catalog.records)))
        selections[domain] = key
        window.items_by_id[key][0].setCheckState(QtCore.Qt.CheckState.Checked)
        check(window.selected == {key} and original.selected == {key}, f"{domain}: isolated checked selection")
        window.show_record(key)
        obj = window.catalog.records[key]
        check(obj["name"] in window.details.toPlainText() and DOMAIN_LABELS[domain] in window.crumb.text(), f"{domain}: detail source and breadcrumb")
        slug = next(iter({p["phase_name"] for p in obj["kill_chain_phases"] if p["kill_chain_name"] == DOMAIN_KILL_CHAINS[domain]}))
        update_annotation(original, key, slug, f"{domain} research", 1.25, "#123456")
        annotation = AnnotationDialog(original, key, window)
        check(annotation.scope.findData(slug) > 0 and annotation.scope.currentData() == slug,
              f"{domain}: native annotation editor exposes source-domain tactic scope")
        check(annotation.comment.toPlainText() == f"{domain} research" and annotation.score.text() == '1.25',
              f"{domain}: native editor restores decimal score/comment")
        before = original.fingerprint()
        annotation.reject()
        check(original.fingerprint() == before, f"{domain}: cancelling annotation preserves document")
        window.refresh_selection()
        window.ttp_search.setText(external_id(obj))
        window.apply_ttp_search()
        check(window.proxy.rowCount() > 0, f"{domain}: ID search matches active domain")
        window.ttp_search.clear()
        window.open_matrix()
        wait(lambda: not window.matrix_view.building, "matrix")
        check(set(window.matrix_view.items_by_id) == set(window.catalog.records), f"{domain}: native matrix covers every active TTP")
        check(DOMAIN_LABELS[domain] in window.matrix_view.summary.text(), f"{domain}: matrix domain visible")
        check(all(item.checkState(0) == QtCore.Qt.CheckState.Checked for item in window.matrix_view.items_by_id[key]), f"{domain}: matrix selection synchronized")
        window.matrix_view.search.setText(obj["name"])
        check(window.matrix_view.search.text() == obj["name"], f"{domain}: name spaces preserved")
        check(window.grab().save(str(OUTPUT / (domain + '.png'))), f"{domain}: preview saved")
        for file_format in ("json", "csv", "navigator"):
            suffix = "navigator.json" if file_format == "navigator" else file_format
            path = window.export_current_document(OUTPUT / (domain + '.' + suffix), file_format)
            check(path is not None, f"{domain}: {file_format} export successful")
            log(f"Input file: {path}")
            if file_format == "csv":
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                check(len(rows) == 1 and rows[0]["attack_domain"] == domain and rows[0]["tactic_ids"], f"{domain}: CSV IDs/domain/tactics")
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
                if file_format == "json":
                    check(data["attack"]["domain"] == domain and data["selected_count"] == 1 and data["selected_ttps"][0]["tactics"], f"{domain}: JSON domain/count/tactics")
                    check(data.get('domain_snapshots', {}) == original.domain_snapshots, f"{domain}: Studio JSON preserves other-domain archives")
                    if key in window.catalog.parents:
                        check(bool(data["selected_ttps"][0]["parent_technique_name"]), f"{domain}: child has parent name")
                else:
                    imported = imported_document(read_layers(path, log)[0], window.catalog)
                    check(imported.catalog.domain == domain and imported.selected == {key}, f"{domain}: Navigator lossless domain/selection round trip")
                    check(imported.navigator_layer["techniques"][0]["score"] == 1.25, f"{domain}: scoped decimal annotation preserved")
        log("[Domain audit 2/6] Domain controls and exports verified", number, 3)
    log("[Domain audit 3/6] Restored domain archives and independent default documents", 0, 3)
    for number, domain in enumerate(DOMAIN_LABELS, 1):
        window.change_document_domain(0, domain)
        wait(lambda: window.loaded_ok, "restore domain")
        check(window.selected == {selections[domain]}, f"{domain}: prior selection restored")
        check(original.navigator_layer["domain"] == domain and original.navigator_layer["techniques"][0]["comment"] == f"{domain} research", f"{domain}: prior annotations restored")
        log("[Domain audit 3/6] Domain restored", number, 3)
    window.change_document_domain(0, "mobile-attack")
    wait(lambda: window.loaded_ok, "mobile before new file")
    window.new_action.trigger()
    wait(lambda: window.loaded_ok, "new Enterprise file")
    check(window.current_document.catalog.domain == "enterprise-attack" and not window.selected, "New File from Mobile defaults to empty Enterprise")
    active = window.current_document
    window.show_document_context_menu(window.document_tabs.tabRect(0).center())
    domain_menu = next(action.menu() for action in window.document_context_menu.actions() if action.text() == "ATT&CK Domain")
    next(action for action in domain_menu.actions() if action.text() == "ICS").trigger()
    check(window.current_document is active and window.catalog.domain == "enterprise-attack", "right-click inactive file does not switch active file")
    check(original.catalog.domain == "ics-attack" and original.selected == {selections['ics-attack']}, "inactive file restores its own domain")
    window.document_context_menu.close()
    window.activate_document(0)
    wait(lambda: window.loaded_ok, "activate ICS file")
    check(window.selected == {selections['ics-attack']}, "tab activation restores ICS independently")
    window.show_document_context_menu(window.document_tabs.tabRect(0).center())
    window.document_context_menu.grab().save(str(OUTPUT / "domain-menu.png"))
    window.document_context_menu.close()
    log("[Domain audit 4/6] Bulk source additions and domain boundaries", 0, 3)
    for number, domain in enumerate(DOMAIN_LABELS, 1):
        window.change_document_domain(0, domain)
        wait(lambda: window.loaded_ok, "bulk domain")
        window.clear_selection()
        source = next(key for key, rows in window.catalog.techniques_by_source[domain].items() if rows and
                      window.catalog.objects_by_domain[domain][key]["type"] in {"intrusion-set", "malware", "tool", "campaign"})
        window.configure_bulk_action(domain, source)
        check(window.bulk_add_button.isEnabled(), f"{domain}: matching source bulk action enabled")
        window.add_current_source_ttps()
        expected = {row["target_ref"] for row in window.catalog.techniques_by_source[domain][source]}
        check(window.selected == expected, f"{domain}: bulk adds exact direct TTPs")
        other = next(value for value in DOMAIN_LABELS if value != domain)
        other_source = next(key for key in window.catalog.objects_by_domain[other]
                            if window.catalog.objects_by_domain[other][key]["type"] in {"malware", "tool", "intrusion-set", "campaign"})
        window.configure_bulk_action(other, other_source)
        check(not window.bulk_add_button.isEnabled(), f"{domain}: foreign-domain source cannot add TTPs")
        window.add_source_ttps(other, other_source)
        check(window.selected == expected, f"{domain}: foreign bulk call leaves selections intact")
        log("[Domain audit 4/6] Bulk domain verified", number, 3)
    log("[Domain audit 5/6] Historical availability, version switching and SDK comparisons", 0, 3)
    historical = load_catalog(DATA, log, snapshot_pointer(DATA, "1.0"))
    window.new_document()
    wait(lambda: window.loaded_ok, "new file for historical test")
    window.apply_version((historical, None))
    wait(lambda: window.loaded_ok, "historical tree")
    window.show_document_context_menu(window.document_tabs.tabRect(window.active_document_index).center())
    domain_menu = next(action.menu() for action in window.document_context_menu.actions() if action.text() == "ATT&CK Domain")
    check(all(action.isEnabled() == bool(historical.objects_by_domain[domain])
              for action, domain in zip(domain_menu.actions(), DOMAIN_LABELS)), "historical domain menu respects exact snapshot availability")
    window.document_context_menu.close()
    before = window.current_document.fingerprint()
    check(not window.change_document_domain(window.active_document_index, "ics-attack") and window.current_document.fingerprint() == before, "unavailable domain failure preserves document")
    picker = VersionDialog(DATA, catalog.version, window, auto_refresh=False, domain="ics-attack")
    row = next(number for number in range(picker.table.rowCount()) if picker.table.item(number, 0).text() == "v1.0")
    picker.table.selectRow(row)
    check(not picker.switch_button.isEnabled(), "ICS version picker prevents selecting absent historical domain")
    picker.reject()
    failures, completed = [], []
    worker = VersionWorker(DATA, "1.0", parent=window, domain="ics-attack")
    worker.failed.connect(failures.append)
    worker.completed.connect(completed.append)
    worker.start()
    wait(lambda: not worker.isRunning() and bool(failures), "unsupported domain worker")
    check(not completed and all(path.read_bytes() == content for path, content in pointers.items()), "worker validates domain before publishing active pointer")
    window.activate_document(0)
    wait(lambda: window.loaded_ok, "restore document")
    for number, domain in enumerate(("mobile-attack", "ics-attack"), 1):
        window.change_document_domain(0, domain)
        wait(lambda: window.loaded_ok, "SDK domain")
        window.apply_version((catalog, pointer))
        wait(lambda: window.loaded_ok, "same release switch")
        check(window.catalog.domain == domain, f"{domain}: release switch retains document domain")
        dialog = VersionCompareDialog(DATA, window.current_document, window)
        dialog.old.setCurrentText(catalog.version)
        dialog.new.setCurrentText("11.3" if domain == "mobile-attack" else "11.2")
        dialog.compare()
        wait(lambda: dialog.result_report is not None or (dialog.worker and not dialog.worker.isRunning() and dialog.status.text().startswith('Failed:')), "actual SDK comparison")
        check(dialog.result_report is not None and dialog.result_report['domain'] == domain and domain in dialog.result_report['changes'], f"{domain}: real SDK version diff uses correct domain")
        check(dialog.table.rowCount() > 0, f"{domain}: native version result table populated")
        wait(lambda: not dialog.worker.isRunning(), "SDK shutdown")
        dialog.reject()
        log("[Domain audit 5/6] SDK domain verified", number, 2)
    log("[Domain audit 6/6] Native Navigator import and comparison constraints", 0, 3)
    for number, domain in enumerate(("mobile-attack", "ics-attack"), 1):
        window.import_navigator_layer(OUTPUT / (domain + ".navigator.json"))
        dialog = window.integration_dialog
        wait(lambda: dialog.import_button.isEnabled(), "native domain import preview")
        check(dialog.catalog.domain == domain and dialog.preview['selected'] == {selections[domain]}, f"{domain}: import preview resolves layer domain")
        count = len(window.documents)
        dialog.import_button.click()
        wait(lambda: window.loaded_ok, "import tree")
        check(len(window.documents) == count + 1 and window.current_document.catalog.domain == domain and window.selected == {selections[domain]}, f"{domain}: import creates independent domain file")
        left = window.current_document
        right = TTPDocument("same-domain", left.catalog, selected=set(left.selected))
        result, counts = compare_documents(left, right)
        check(result['domain'] == domain and counts['Both'] == 1, f"{domain}: same-domain comparison layer")
        try:
            compare_documents(left, active)
        except ValueError:
            check(True, f"{domain}: mixed-domain comparison explicitly rejected")
        else:
            raise AssertionError("mixed domains accepted")
        log("[Domain audit 6/6] Native import verified", number, 2)
    check(all(path.read_bytes() == content for path, content in pointers.items()), "audit leaves active/latest pointers unchanged")
    window.close()
    report = {"status": "PASS", "checks": checks, "outputs": str(OUTPUT),
              "domain_technique_counts": {domain: len(catalog.for_domain(domain).records) for domain in DOMAIN_LABELS}}
    log(f"Output file: {REPORT}")
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log(f"[Domain audit] PASS: {len(checks)} checks", 6, 6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
