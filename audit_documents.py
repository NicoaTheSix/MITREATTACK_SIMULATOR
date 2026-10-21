"""Verify actual multi-document UI and JSON exports. Operation flow: README.md."""
from pathlib import Path
import csv
from dataclasses import replace
import json
import sys
import time
from unittest.mock import patch
import uuid

from PySide6 import QtCore, QtGui, QtTest, QtWidgets
from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from main import MainWindow, configure_application
from ttp_documents import TTPDocument, export_document_json, export_document_csv, CSV_FIELDS
from scripts.download_attack_data import write_json

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts'
TEST = OUT / ('ttp-document-audit-' + uuid.uuid4().hex)
REPORT = OUT / 'ttp-document-audit.json'
SCREEN = OUT / 'ttp-documents-preview.png'
SAMPLE = OUT / 'selected-ttps-example.json'
CSV_SAMPLE = OUT / 'selected-ttps-example.csv'
checks = []


def log(message, current=0, total=0):
    print(message + (f' ({current}/{total})' if total else ''), flush=True)


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def wait(condition, description):
    end = time.monotonic() + 60
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError(description)
        QtTest.QTest.qWait(20)


def main():
    print(f'Input file: {DATA / "latest.json"}\nOutput report: {REPORT}\nOutput preview: {SCREEN}\nOutput sample: {SAMPLE}\nOutput CSV sample: {CSV_SAMPLE}\nOutput test directory: {TEST}', flush=True)
    for name in ('empty.json', 'empty.csv', '研究文件-A.json', '研究文件-A.csv', 'parent-only.csv',
                 'quoted-names.csv', 'research-B.json', 'older-version.json', 'closed-B.json'):
        print(f'Output file: {TEST / name}', flush=True)
    TEST.mkdir(parents=True)
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / 'latest.json')
    window.show()
    window.activateWindow()
    wait(lambda: window.loaded_ok, 'initial catalog')
    log('[Document audit 1/7] Default document and empty JSON export')
    check(len(window.documents) == 1 and window.current_document.name == 'Untitled-1', 'initial unnamed document')
    check(window.new_action.shortcut().toString() == 'Ctrl+N', 'Ctrl+N assigned to New File')
    empty = window.export_current_document(TEST / 'empty.json')
    data = json.loads(empty.read_text(encoding='utf-8'))
    check(data['selected_count'] == 0 and data['selected_ttps'] == [], 'empty document exports valid zero-selection JSON')
    initial = window.current_document
    by_id = {external_id(obj): key for key, obj in window.catalog.records.items()}
    powershell = by_id['T1059.001']
    scheduled = by_id['T1053.005']
    for key in (powershell, scheduled):
        window.items_by_id[key][0].setCheckState(QtCore.Qt.CheckState.Checked)
    check(initial.dirty and ' *' in window.document_tabs.tabText(0), 'selection changes mark file unexported')
    log('[Document audit 2/7] File menu export records exact IDs, metadata and duplicate synchronization')
    path_a = TEST / '研究文件-A.json'
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(path_a), 'JSON files (*.json)')):
        window.export_action.trigger()
    data_a = json.loads(path_a.read_text(encoding='utf-8'))
    check(data_a['selected_technique_ids'] == ['T1053.005', 'T1059.001'] and data_a['selected_count'] == 2, 'exact deduplicated selected IDs')
    check(data_a['attack']['version'] == initial.catalog.version and data_a['attack']['domain'] == 'enterprise-attack', 'dataset version and domain exported')
    check(data_a['name'] == '研究文件-A' and initial.name == '研究文件-A' and not initial.dirty, 'Unicode filename renames exported document and clears dirty mark')
    rows = {row['technique_id']: row for row in data_a['selected_ttps']}
    check(rows['T1059.001']['name'] == 'PowerShell' and rows['T1059.001']['parent_technique_id'] == 'T1059', 'technique name and official parent exported')
    check(rows['T1059.001']['parent_technique_name'] == 'Command and Scripting Interpreter'
          and rows['T1053.005']['parent_technique_name'] == 'Scheduled Task/Job', 'JSON includes parent technique names')
    check(rows['T1059.001']['is_subtechnique'] and rows['T1059.001']['stix_id'] == powershell, 'STIX identity and sub-technique flag exported')
    check(rows['T1053.005']['platforms'] == sorted(set(window.catalog.records[scheduled]['x_mitre_platforms'])), 'platform metadata from source')
    check(rows['T1059.001']['tactics'] and data_a['document_id'] == initial.document_id, 'tactic metadata and stable document identity')
    check(all(item.checkState() == QtCore.Qt.CheckState.Checked for item in window.items_by_id[powershell]), 'duplicate tree rows remain synchronized')
    check(window.selection_list.item(1).text().splitlines()[1].strip() == 'Parent: T1059  Command and Scripting Interpreter', 'parent ID/name appears below selected child')
    window.show_record(powershell)
    check('Parent technique' in window.details.toPlainText() and 'Command and Scripting Interpreter' in window.details.toPlainText(), 'sub-technique details display parent name')
    log('[Document audit CSV] CSV menu action, source names, UTF-8 and exact selection parity')
    csv_path = TEST / '研究文件-A.csv'
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(csv_path), 'CSV files (*.csv)')) as dialog:
        window.export_csv_action.trigger()
        check(dialog.call_args.args[3] == 'CSV files (*.csv)', 'File Export CSV opens CSV filter')
    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    check([row['technique_id'] for row in csv_rows] == data_a['selected_technique_ids'], 'CSV matches exact JSON selections')
    check(csv_path.read_bytes().startswith(b'\xef\xbb\xbf'), 'CSV uses UTF-8 BOM for Excel')
    check(all(row['attack_version'] == initial.catalog.version and row['document_id'] == initial.document_id for row in csv_rows), 'CSV records document identity and correct ATT&CK version')
    check(csv_rows[1]['parent_technique_id'] == 'T1059' and csv_rows[1]['parent_technique_name'] == 'Command and Scripting Interpreter', 'CSV includes child parent ID/name')
    check(csv_rows[0]['tactic_ids'] == 'TA0002; TA0003; TA0004' and csv_rows[0]['is_subtechnique'] == 'true', 'CSV preserves all tactic IDs and sub-technique flag')
    parent_document = TTPDocument('parent-only', window.catalog, {by_id['T1059']})
    parent_csv = export_document_csv(parent_document, TEST / 'parent-only.csv', log)
    with parent_csv.open(encoding='utf-8-sig', newline='') as stream:
        parent_row = next(csv.DictReader(stream))
    check(parent_row['is_subtechnique'] == 'false' and parent_row['parent_technique_name'] == ''
          and parent_row['parent_technique_id'] == '', 'parent selection has empty ancestor fields')
    empty_document = TTPDocument('empty', window.catalog)
    empty_csv = export_document_csv(empty_document, TEST / 'empty.csv', log)
    with empty_csv.open(encoding='utf-8-sig', newline='') as stream:
        empty_reader = csv.DictReader(stream)
        check(tuple(empty_reader.fieldnames) == CSV_FIELDS and list(empty_reader) == [], 'empty CSV contains headers without fabricated selections')
    fixture_records = dict(window.catalog.records)
    fixture_records[powershell] = {**fixture_records[powershell], 'name': '子技術, "多行"\n測試'}
    fixture_records[by_id['T1059']] = {**fixture_records[by_id['T1059']], 'name': '父技術, "名稱"'}
    fixture = TTPDocument('quoted-names', replace(window.catalog, records=fixture_records), {powershell})
    quoted = export_document_csv(fixture, TEST / 'quoted-names.csv', log)
    with quoted.open(encoding='utf-8-sig', newline='') as stream:
        quoted_row = next(csv.DictReader(stream))
    check(quoted_row['name'] == fixture_records[powershell]['name']
          and quoted_row['parent_technique_name'] == fixture_records[by_id['T1059']]['name'], 'CSV round-trips Unicode, commas, quotes and newlines')
    previous_csv = csv_path.read_bytes()
    with patch.object(Path, 'replace', side_effect=OSError('Simulated CSV publish failure')):
        try:
            export_document_csv(initial, csv_path, log)
        except OSError:
            pass
        else:
            raise AssertionError('CSV publish error not raised')
    check(csv_path.read_bytes() == previous_csv and not list(TEST.glob('*.tmp')), 'failed CSV publish preserves existing output and cleans temporary file')
    log('[Document audit 3/7] Real Ctrl+N and File New keep independent documents')
    QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_N, QtCore.Qt.KeyboardModifier.ControlModifier)
    wait(lambda: len(window.documents) == 2, 'Ctrl+N')
    second = window.current_document
    check(second.name == 'Untitled-2' and not window.selected, 'Ctrl+N opens empty independent document')
    check(initial.selected == {powershell, scheduled}, 'first document selection preserved')
    window.items_by_id[scheduled][0].setCheckState(QtCore.Qt.CheckState.Checked)
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(TEST / 'research-B.json'), 'JSON files (*.json)')):
        QtTest.QTest.keyClick(window, QtCore.Qt.Key.Key_E, QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier)
        wait(lambda: (TEST / 'research-B.json').exists(), 'export shortcut')
    data_b = json.loads((TEST / 'research-B.json').read_text(encoding='utf-8'))
    check(data_b['selected_technique_ids'] == ['T1053.005'], 'second document exports only its own TTP')
    check(data_b['document_id'] != data_a['document_id'], 'documents have distinct stable IDs')
    window.new_action.trigger()
    check(len(window.documents) == 3 and window.current_document.name == 'Untitled-3' and not window.selected, 'File New uses the same document workflow')
    window.document_tabs.setCurrentIndex(0)
    check(window.selected == {powershell, scheduled} and window.selection_list.count() == 2, 'tab switching restores first selection')
    window.items_by_id[powershell][0].setCheckState(QtCore.Qt.CheckState.Unchecked)
    check(initial.dirty, 'editing an exported file marks it dirty')
    window.items_by_id[powershell][0].setCheckState(QtCore.Qt.CheckState.Checked)
    check(not initial.dirty, 'returning to exported selection clears dirty mark')
    log('[Document audit 4/7] Cancellation, extension handling and atomic failure preservation')
    previous_files = set(TEST.iterdir())
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=('', '')):
        check(window.export_current_document() is None, 'cancel returns without export')
    check(set(TEST.iterdir()) == previous_files and not initial.dirty, 'cancel creates no files and preserves document state')
    before = path_a.read_bytes()
    identity = (initial.name, initial.export_path, initial.exported_fingerprint)
    with patch.object(Path, 'replace', side_effect=OSError('Simulated publish failure')):
        try:
            export_document_json(initial, path_a, log)
        except OSError:
            pass
        else:
            raise AssertionError('publish error not raised')
    check(path_a.read_bytes() == before, 'failed publish preserves previous JSON')
    check((initial.name, initial.export_path, initial.exported_fingerprint) == identity and not list(TEST.glob('*.tmp')), 'failure preserves document state and removes staging file')
    invalid = TTPDocument('invalid', window.catalog, {'attack-pattern--unknown'})
    try:
        export_document_json(invalid, path_a, log)
    except ValueError:
        pass
    else:
        raise AssertionError('missing record not rejected')
    check(path_a.read_bytes() == before, 'invalid selection rejected before overwriting export')
    log('[Document audit 5/7] Files retain separate ATT&CK snapshots across version changes')
    old_catalog = load_catalog(DATA, log, snapshot_pointer(DATA, '1.0'))
    window.document_tabs.setCurrentIndex(1)
    window.apply_version((old_catalog, None))
    wait(lambda: window.loaded_ok and window.catalog.version == '1.0', 'historical document catalog')
    check(second.catalog.version == '1.0' and initial.catalog.version == data_a['attack']['version'], 'changing version affects only active document')
    common = next(key for key in old_catalog.records if key in initial.catalog.records)
    window.items_by_id[common][0].setCheckState(QtCore.Qt.CheckState.Checked)
    older = window.export_current_document(TEST / 'older-version.json')
    data_old = json.loads(older.read_text(encoding='utf-8'))
    check(data_old['attack']['version'] == '1.0' and data_old['selected_technique_ids'] == [external_id(old_catalog.records[common])], 'older file exports its actual snapshot and selection')
    window.document_tabs.setCurrentIndex(0)
    wait(lambda: window.loaded_ok and window.catalog.version == initial.catalog.version, 'restore original snapshot')
    check(window.selected == {powershell, scheduled} and set(window.items_by_id) == set(initial.catalog.records), 'switching file restores its original catalog and tree')
    log('[Document audit 6/7] Selection-page export and visual preview')
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(SAMPLE.with_suffix('')), 'JSON files (*.json)')):
        window.selection_export_button.click()
    check(SAMPLE.exists() and json.loads(SAMPLE.read_text(encoding='utf-8'))['selected_technique_ids'] == data_a['selected_technique_ids'], 'selection-page button exports JSON and adds extension')
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(CSV_SAMPLE.with_suffix('')), 'CSV files (*.csv)')):
        window.selection_export_button.click()
    with CSV_SAMPLE.open(encoding='utf-8-sig', newline='') as stream:
        sample_csv_rows = list(csv.DictReader(stream))
    check([row['technique_id'] for row in sample_csv_rows] == data_a['selected_technique_ids'], 'selection-page export supports CSV filter and missing extension')
    with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=('', '')) as dialog:
        window.export_action.trigger()
        check(dialog.call_args.args[2].endswith('.csv') and dialog.call_args.args[4] == 'CSV files (*.csv)', 'export remembers previous CSV format and filename')
    log('[Document audit 7/7] Right-click rename and close target the clicked file')
    position = window.document_tabs.tabRect(1).center()
    event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse, position,
                                   window.document_tabs.mapToGlobal(position))
    QtWidgets.QApplication.sendEvent(window.document_tabs, event)
    menu = window.document_context_menu
    check(menu is not None and [action.text() for action in menu.actions()] == ['Close File', 'Rename…', 'ATT&CK Domain'], 'native right-click menu retains close/rename and adds domain selection')
    check(window.current_document is initial and window.selected == {powershell, scheduled}, 'right-click inactive tab preserves active selection')
    with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('Named-B.json', True)):
        menu.actions()[1].trigger()
    menu.close()
    check(second.name == 'Named-B' and second.dirty and second.document_id == data_b['document_id'], 'rename targets inactive file, normalizes extension and preserves identity')
    check(window.current_document is initial and initial.name == SAMPLE.stem, 'inactive rename leaves active name unchanged')
    check(older.exists() and json.loads(older.read_text(encoding='utf-8'))['name'] == 'older-version', 'rename keeps existing disk export unchanged')
    with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('', False)):
        check(not window.rename_document(1) and second.name == 'Named-B', 'cancelled rename preserves name')
    with patch.object(QtWidgets.QInputDialog, 'getText', side_effect=[('bad/name', True), ('CON.json', True), ('Renamed-B', True)]), \
            patch.object(QtWidgets.QMessageBox, 'warning') as warning:
        check(window.rename_document(1) and warning.call_count == 2 and second.name == 'Renamed-B', 'invalid Windows names are rejected before a valid rename')
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Cancel):
        check(not window.close_document(1) and len(window.documents) == 3, 'cancel preserves dirty document')
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Save), \
            patch.object(window, 'save_studio_document', return_value=None):
        check(not window.close_document(1) and len(window.documents) == 3, 'cancelled pre-close Studio save keeps document open')
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Save), \
            patch('studio_files.write_json_atomic', side_effect=OSError('Injected Save failure')), \
            patch.object(QtWidgets.QMessageBox, 'critical'):
        check(not window.close_document(1) and second in window.documents, 'failed pre-close Studio save keeps document open')
    closed_path = second.save_path
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Save), \
            patch.object(QtWidgets.QFileDialog, 'getSaveFileName') as dialog:
        check(window.close_document(1), 'save and close inactive file')
        check(not dialog.called, 'pre-close Save reuses the existing Studio path after rename')
    closed = json.loads(closed_path.read_text(encoding='utf-8'))
    check(closed['attack']['version'] == '1.0' and closed['selected_technique_ids'] == data_old['selected_technique_ids'], 'pre-close export uses clicked file snapshot and selections')
    check(window.current_document is initial and window.selected == {powershell, scheduled}, 'closing inactive file preserves active selection')
    window.new_document()
    last = window.current_document
    window.items_by_id[powershell][0].setCheckState(QtCore.Qt.CheckState.Checked)
    check(window.close_document(0) and window.current_document is last and window.active_document_index == 1
          and window.selected == {powershell}, 'closing earlier tab adjusts active index without changing its document')
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Discard):
        check(window.close_document(1) and len(window.documents) == 1 and not window.selected, 'discard closes active dirty file and restores adjacent selection')
    previous = window.current_document
    check(window.close_document(0) and len(window.documents) == 1 and window.current_document is not previous
          and not window.selected, 'closing last file creates fresh empty Untitled document')
    window.apply_version((old_catalog, None))
    wait(lambda: window.loaded_ok and window.catalog.version == '1.0', 'old replacement document')
    window.new_document()
    window.apply_version((initial.catalog, None))
    wait(lambda: window.loaded_ok and window.catalog.version == initial.catalog.version, 'different adjacent snapshot')
    check(window.close_document(1), 'close active file beside different snapshot')
    wait(lambda: window.loaded_ok and window.catalog.version == '1.0', 'adjacent snapshot after close')
    check(window.current_document.catalog.version == '1.0' and not window.selected, 'close restores adjacent file ATT&CK snapshot')
    window.apply_version((initial.catalog, None))
    wait(lambda: window.loaded_ok and window.catalog.version == initial.catalog.version, 'preview snapshot')
    with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('Research-Profile', True)):
        window.rename_document(0)
    window.items_by_id[powershell][0].setCheckState(QtCore.Qt.CheckState.Checked)
    window.new_document()
    window.document_tabs.setCurrentIndex(0)
    window.tabs.setCurrentIndex(window.selection_tab_index)
    window.output_panel.hide()
    QtTest.QTest.qWait(180)
    position = window.document_tabs.tabRect(0).center()
    window.show_document_context_menu(position)
    QtTest.QTest.qWait(80)
    preview = window.grab()
    painter = QtGui.QPainter(preview)
    menu = window.document_context_menu
    painter.drawPixmap(menu.mapToGlobal(QtCore.QPoint(0, 0)) - window.mapToGlobal(QtCore.QPoint(0, 0)), menu.grab())
    painter.end()
    check(preview.save(str(SCREEN)), 'multi-document right-click preview saved')
    menu.close()
    window.confirm_studio_changes = lambda *_: 'discard'
    window.close()
    write_json(REPORT, {'status': 'PASS', 'checks': checks, 'test_output_directory': str(TEST),
                       'sample_export': str(SAMPLE), 'csv_sample_export': str(CSV_SAMPLE), 'screenshot': str(SCREEN)})
    log(f'[Document audit] PASS: {len(checks)} checks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

