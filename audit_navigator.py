"""Audit Navigator/SDK IO, native dialogs and local STIX 2.1 comparisons. Workflow: README.md."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch
import uuid

from PySide6 import QtCore, QtTest, QtWidgets

from attack_catalog import external_id, load_catalog, local_path
from attack_versions import snapshot_pointer
from main import MainWindow, configure_application
from navigator_integration import (read_layers, validate_layer, import_preview, document_layer, export_layer,
                                   update_annotation, compare_documents, sdk_version, write_json_atomic, imported_document)
from navigator_dialogs import AnnotationDialog, VersionCompareDialog
from ttp_documents import TTPDocument

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "attack"
OUT = ROOT / "artifacts"
TEST = OUT / ("navigator-audit-" + uuid.uuid4().hex)
REPORT = OUT / "navigator-audit.json"
SCREEN = OUT / "navigator-import-preview.png"
COMPARISON_SCREEN = OUT / "navigator-version-comparison-preview.png"
checks = []


def log(message, current=0, total=0):
    print(message + (f" ({current}/{total})" if total else ""), flush=True)


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def wait(condition, label, seconds=90):
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError(label)
        # Python-heavy SDK workers need a real GIL release while we pump Qt.
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def expect_error(task, label):
    try:
        task()
    except (ValueError, OSError, TypeError):
        checks.append(label)
    else:
        raise AssertionError(label)


def main():
    log(f"Input file: {DATA / 'latest.json'}")
    filenames = ("fixture.json", "fixture-utf16.json", "roundtrip.json", "plain.json", "list.csv", "annotated.json",
                 "selection-comparison.json", "version-comparison.json", "invalid.json", "multi.json", "old-layer.json")
    for path in (REPORT, SCREEN, COMPARISON_SCREEN, TEST, *(TEST / name for name in filenames)):
        log(f"Output file: {path}")
    TEST.mkdir()
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / "latest.json")
    window.resize(1700, 1000)
    window.show()
    wait(lambda: window.loaded_ok, "catalog loading")
    catalog = window.catalog
    lookup = {external_id(record): key for key, record in catalog.records.items()}
    task, shell = lookup["T1053.005"], lookup["T1059.001"]
    first = window.current_document
    log("[Navigator audit 1/7] Official SDK validation and fractional/Unicode annotation preservation")
    check(sdk_version() == "6.2.1", "pinned SDK installed")
    check(window.import_layer_action.shortcut().toString() == "Ctrl+Alt+O", "native Navigator import shortcut remains distinct from Studio Open")
    layer = {"name": "Research Layer", "domain": "enterprise-attack",
             "versions": {"attack": catalog.version, "navigator": "5.2.0", "layer": "4.5"},
             "description": "Unicode research 藍隊", "customDataURL": "https://example.invalid/do-not-fetch.json",
             "filters": {"platforms": ["Windows"]}, "hideDisabled": True,
             "legendItems": [{"label": "Research", "color": "#ff7700"}],
             "techniques": [
                 {"techniqueID": "T1053.005", "tactic": "execution", "score": 2.5, "color": "#ff7700",
                  "comment": "研究\nquoted \"example\"", "enabled": True, "links": [{"label": "Ref", "url": "https://example.com"}]},
                 {"techniqueID": "T1053.005", "tactic": "persistence", "score": -3.75, "comment": "disabled scope", "enabled": False},
                 {"techniqueID": "T1059.001", "score": 0, "comment": "unselected annotation", "enabled": False},
                 {"techniqueID": "T9999", "comment": "unresolved annotation", "enabled": True},
                 {"techniqueID": "T1053.002", "tactic": "collection", "comment": "tactic mismatch", "enabled": True}]}
    write_json_atomic(layer, TEST / "fixture.json", log, "Audit fixture")
    (TEST / "fixture-utf16.json").write_text(json.dumps(layer, ensure_ascii=False), encoding="utf-16")
    check(read_layers(TEST / "fixture.json", log)[0] == layer, "lossless UTF-8 read including decimal scores")
    check(read_layers(TEST / "fixture-utf16.json", log)[0] == layer, "UTF-16 SDK-exported input supported")
    preview = import_preview(layer, catalog)
    check(preview["selected"] == {task} and preview["unresolved"] == 2, "enabled policy excludes unknown ID and mismatched tactic")
    check(import_preview(layer, catalog, "all")["selected"] == {task, shell}, "all-row policy")
    check(import_preview(layer, catalog, "annotated")["selected"] == {task, shell}, "scored policy includes score zero")
    expect_error(lambda: imported_document(layer, catalog, 'all'), 'customDataURL cannot silently resolve against official data')
    check(validate_layer(layer)['customDataURL'] == layer['customDataURL'], 'custom URL retained during validation without fetching')
    # Remaining cases exercise an official catalog layer. Custom catalog imports
    # and their complete URL round trips are covered in audit_advanced_navigator.
    layer = deepcopy(layer)
    layer.pop('customDataURL')
    write_json_atomic(layer, TEST / 'fixture.json', log, 'Official audit fixture')
    all_document = imported_document(layer, catalog, "all")
    all_output = document_layer(all_document)
    check(shell in all_document.selected and not next(row for row in all_output["techniques"] if row["techniqueID"] == "T1059.001")["enabled"],
          "all-row import includes a disabled TTP without enabling it")
    all_document.selected.add(lookup["T1053.002"])
    scopes_output = document_layer(all_document)
    check(any(row["techniqueID"] == "T1053.002" and not row.get("tactic") and row.get("enabled", True)
              for row in scopes_output["techniques"]), "selected ID with only mismatched annotations gains a valid global row")
    check(not next(row for row in scopes_output["techniques"] if row["techniqueID"] == "T1053.002" and row.get("tactic"))["enabled"],
          "mismatched scope remains preserved but disabled")
    for replacement in (float("nan"), float("inf"), True, "5"):
        invalid = deepcopy(layer)
        invalid["techniques"][0]["score"] = replacement
        expect_error(lambda: validate_layer(invalid), f"reject invalid score {replacement}")
    invalid = deepcopy(layer)
    invalid["techniques"][0]["color"] = "not-a-color"
    expect_error(lambda: validate_layer(invalid), "reject invalid color")
    modern = deepcopy(layer)
    modern["versions"]["layer"] = "9.0"
    expect_error(lambda: validate_layer(modern), "reject unsupported future layer schema")
    log("[Navigator audit 2/7] Native import preview, cancellation and independent documents")
    with patch.object(QtWidgets.QFileDialog, "getOpenFileName", return_value=("", "Navigator Layer files (*.json)")):
        window.import_layer_action.trigger()
    check(len(window.documents) == 1, "cancelled file dialog leaves documents intact")
    window.import_navigator_layer(TEST / "fixture.json")
    dialog = window.integration_dialog
    wait(lambda: dialog.preview is not None and not dialog.worker.isRunning(), "import preview")
    check(dialog.table.rowCount() == 5 and dialog.import_button.isEnabled(), "native preview lists every layer row")
    check(window.current_document is first and not window.selected, "preview does not mutate current document")
    QtTest.QTest.qWait(100)
    check(dialog.grab().save(str(SCREEN)), "import preview screenshot")
    dialog.reject()
    check(len(window.documents) == 1, "cancelled preview creates no document")
    window.import_navigator_layer(TEST / "fixture.json")
    dialog = window.integration_dialog
    wait(lambda: dialog.preview is not None and not dialog.worker.isRunning(), "second import preview")
    QtTest.QTest.mouseClick(dialog.import_button, QtCore.Qt.MouseButton.LeftButton)
    wait(lambda: window.current_document is not first and window.loaded_ok, "import installation")
    document = window.current_document
    check(window.selected == {task} and not first.selected, "import creates independent document selection")
    check(document.navigator_layer == layer and document.dirty, "raw annotations retained and new document marked changed")
    check(all(item.checkState() == QtCore.Qt.CheckState.Checked for item in window.items_by_id[task]), "import synchronizes sidebar duplicates")
    window.export_current_document(TEST / "roundtrip.json", "navigator")
    log(f"Input file: {TEST / 'roundtrip.json'}")
    exported = read_layers(TEST / "roundtrip.json", log)[0]
    check(exported["filters"] == layer["filters"] and exported['description'] == layer['description'], "layout/filter/description preservation")
    check(exported["techniques"][0]["score"] == 2.5 and exported["techniques"][1]["score"] == -3.75,
          "SDK validation does not truncate fractional scores")
    check(exported["techniques"][1]["enabled"] is False, "disabled tactic row preserved")
    check(import_preview(exported, catalog)["selected"] == {task}, "own layer round trip restores exact selection")
    check(document.export_format == "navigator" and document.dirty, "Navigator exchange does not replace a complete Studio save")
    window.export_current_document(TEST / "plain.json", "json")
    log(f"Input file: {TEST / 'plain.json'}")
    check(json.loads((TEST / "plain.json").read_text(encoding="utf-8"))["navigator_layer"] == layer, "Studio JSON preserves complete annotations")
    window.export_current_document(TEST / "list.csv", "csv")
    check(document.dirty, "CSV list export cannot mark annotations saved")
    with patch.object(QtWidgets.QMessageBox, "question", return_value=QtWidgets.QMessageBox.StandardButton.Save), \
         patch.object(window, 'save_studio_document', return_value=None):
        closed = window.close_document(window.active_document_index)
    check(not closed and document in window.documents and document.navigator_layer == layer,
          "cancelled complete Studio save retains the document and annotations")
    blocked = TEST / "blocked.json"
    log(f"Output directory: {blocked}")
    blocked.mkdir()
    state = (document.name, document.export_path, document.exported_fingerprint)
    expect_error(lambda: export_layer(document, blocked, log), "failed atomic publishing")
    check((document.name, document.export_path, document.exported_fingerprint) == state and not list(TEST.glob("*.tmp")),
          "failed export preserves document state and cleans temporary file")
    log("[Navigator audit 3/7] Native annotation editor and saved-format default")
    window.switch_category("TTP")
    window.show_record(task)
    check(window.annotation_button.isVisible(), "technique detail exposes annotation action")
    def fill_annotation():
        editor = app.activeModalWidget()
        check(isinstance(editor, AnnotationDialog), "native annotation dialog")
        editor.scope.setCurrentIndex(0)
        editor.comment.setPlainText("Edited annotation 改寫")
        editor.score.setText("9.25")
        editor.color.setText("#112233")
        editor.include.setChecked(True)
        editor.save()
    QtCore.QTimer.singleShot(80, fill_annotation)
    QtTest.QTest.mouseClick(window.annotation_button, QtCore.Qt.MouseButton.LeftButton)
    row = next(row for row in document.navigator_layer["techniques"] if row["techniqueID"] == "T1053.005" and not row.get("tactic"))
    check(row["score"] == 9.25 and row["comment"] == "Edited annotation 改寫" and document.dirty, "annotation editor stores decimals/Unicode and marks changed")
    original = deepcopy(document.navigator_layer)
    expect_error(lambda: update_annotation(document, task, "", "bad", float("nan"), "#112233"), "annotation validation rejects nonfinite score")
    check(document.navigator_layer == original, "invalid annotation does not mutate document")
    with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(TEST / "annotated.json"), "Navigator Layer files (*.json)")):
        QtCore.QTimer.singleShot(80, lambda: app.activeModalWidget().export_button.click())
        window.export_layer_action.trigger()
    with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=("", "")) as choose:
        window.export_action.trigger()
    check(choose.call_args.args[4] == "Navigator Layer files (*.json)", "general/pre-close export remembers Navigator format")
    log("[Navigator audit 4/7] Selection comparison and exact version isolation")
    window.new_document()
    window.items_by_id[shell][0].setCheckState(QtCore.Qt.CheckState.Checked)
    window.items_by_id[task][0].setCheckState(QtCore.Qt.CheckState.Checked)
    second = window.current_document
    comparison, counts = compare_documents(document, second)
    check(counts == {"Both": 1, "Left only": 0, "Right only": 1}, "comparison intersection and differences")
    write_json_atomic(comparison, TEST / "selection-comparison.json", log)
    window.open_selection_comparison()
    selection_dialog = window.integration_dialog
    selection_dialog.left.setCurrentIndex(1)
    selection_dialog.right.setCurrentIndex(2)
    check(selection_dialog.table.rowCount() == 2 and selection_dialog.export_button.isEnabled(), "native selection comparison")
    selection_dialog.reject()
    old = load_catalog(DATA, log, snapshot_pointer(DATA, "11.2"))
    previous_layer = deepcopy(document.navigator_layer)
    document.set_catalog(old)
    check(not document.navigator_layer and catalog.version in document.navigator_snapshots, "different version archives annotations independently")
    document.set_catalog(catalog)
    check(document.navigator_layer == previous_layer, "restoring a version restores its exact annotations")
    historical = TTPDocument("Historical", load_catalog(DATA, log, snapshot_pointer(DATA, "1.0")))
    expect_error(lambda: document_layer(historical), "historical versions below v4 reject Navigator export")
    expect_error(lambda: compare_documents(document, historical), "comparison refuses mixed versions")
    old_fixture = deepcopy(layer)
    old_fixture["versions"]["attack"] = "11.2"
    write_json_atomic(old_fixture, TEST / "old-layer.json", log)
    window.import_navigator_layer(TEST / "old-layer.json")
    old_dialog = window.integration_dialog
    wait(lambda: bool(old_dialog.layers) and not old_dialog.busy and not old_dialog.pending_resolve and old_dialog.catalog is not None, "historical layer file")
    check(old_dialog.import_button.isEnabled(), "cached recorded version is automatically resolved before opening")
    old_dialog.load_button.click()
    wait(lambda: old_dialog.catalog is not None and not old_dialog.worker.isRunning(), "historical import catalog")
    check(old_dialog.catalog.version == "11.2" and window.catalog is catalog, "historical preview does not switch active document")
    old_dialog.reject()
    log("[Navigator audit 5/7] Official SDK STIX 2.1 version comparison in background")
    latest_only = next(key for key in catalog.records if external_id(catalog.records[key]) not in {external_id(obj) for obj in old.records.values()})
    window.items_by_id[latest_only][0].setCheckState(QtCore.Qt.CheckState.Checked)
    baseline = (window.current_document.fingerprint(), set(window.selected))
    window.open_version_comparison()
    version_dialog = window.integration_dialog
    check(isinstance(version_dialog, VersionCompareDialog), "version menu opens correct comparison dialog")
    check(version_dialog.compare_button.isEnabled(), "version comparison button enabled")
    version_dialog.old.setCurrentText(catalog.version)
    version_dialog.new.setCurrentText("11.2")
    version_dialog.compare_button.click()
    check(version_dialog.worker is not None, "version comparison starts worker")
    wait(lambda: version_dialog.result_report is not None or version_dialog.status.text().startswith("Failed:"), "version comparison", 150)
    if version_dialog.result_report is None:
        raise AssertionError(version_dialog.status.text())
    report = version_dialog.result_report
    check(report["sdk_version"] == "6.2.1" and report["stix_format"] == "2.1", "actual SDK compares verified STIX 2.1 snapshots")
    check(external_id(catalog.records[latest_only]) in report["unavailable_selected_ids"], "selection migration impact identifies unavailable IDs")
    check(version_dialog.table.rowCount() > 0, "version comparison populates native table")
    check((window.current_document.fingerprint(), set(window.selected)) == baseline, "version comparison is read-only for open documents")
    check(not list(OUT.glob("sdk-diff-*")), "SDK staging files removed")
    with patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(str(TEST / "version-comparison.json"), "JSON files (*.json)")):
        version_dialog.export_button.click()
    check((TEST / "version-comparison.json").is_file(), "version comparison report exports JSON")
    QtTest.QTest.qWait(120)
    check(version_dialog.grab().save(str(COMPARISON_SCREEN)), "version comparison screenshot")
    wait(lambda: not version_dialog.worker.isRunning(), "SDK worker shutdown")
    version_dialog.reject()
    log("[Navigator audit 6/7] Invalid and multiple-layer inputs")
    bad = {"name": "Bad", "domain": "unknown-attack", "versions": {"attack": "19.2", "layer": "4.5", "navigator": "5.2.0"}}
    write_json_atomic(bad, TEST / "invalid.json", log)
    expect_error(lambda: read_layers(TEST / "invalid.json", log), "unknown domain import rejected")
    before = len(window.documents)
    window.import_navigator_layer(TEST / "invalid.json")
    invalid_dialog = window.integration_dialog
    wait(lambda: invalid_dialog.worker and not invalid_dialog.worker.isRunning(), "invalid dialog")
    check(not invalid_dialog.import_button.isEnabled() and len(window.documents) == before, "invalid UI import leaves documents intact")
    invalid_dialog.reject()
    write_json_atomic([layer, old_fixture], TEST / "multi.json", log)
    check(len(read_layers(TEST / "multi.json", log)) == 2, "multi-layer array supported")
    window.import_navigator_layer(TEST / "multi.json")
    multi = window.integration_dialog
    wait(lambda: multi.layer.count() == 2 and not multi.busy and not multi.pending_resolve and len(multi.results) == 2, "multiple-layer preview")
    multi.layer.setCurrentIndex(1)
    check(multi.version.currentText() == "11.2" and multi.catalog.version == '11.2' and multi.import_button.isEnabled(),
          "layer picker restores each resolved snapshot while retaining the complete batch")
    multi.reject()
    window.confirm_studio_changes = lambda *_: "discard"
    window.close()
    log("[Navigator audit 7/7] Publishing report")
    write_json_atomic({"status": "PASS", "checks": checks, "sdk_version": sdk_version(), "outputs": str(TEST)}, REPORT, log, "Navigator Audit Report")
    log(f"[Navigator audit] PASS: {len(checks)} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
