"""Verify individual selected-TTP annotations and JSON/CSV comment exports. Flow: README.md."""
from copy import deepcopy
from pathlib import Path
import csv
import json
import sys
import time
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets, QtTest
from shiboken6 import isValid
from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from main import MainWindow, configure_application, ROLE_ID
from navigator_dialogs import AnnotationDialog
from navigator_integration import update_annotation
from ttp_documents import document_payload, technique_comments, CSV_FIELDS, TTPDocument

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts'
REPORT = OUT / 'comments-audit.json'
JSON_SAMPLE = OUT / 'ttp-comments-example.json'
CSV_SAMPLE = OUT / 'ttp-comments-example.csv'
SCREEN = OUT / 'ttp-comments-preview.png'
DOMAIN_FILES = {domain: (OUT / f'ttp-comments-{domain}.json', OUT / f'ttp-comments-{domain}.csv')
                for domain in ('mobile-attack', 'ics-attack', 'historical')}
checks = []
COMMENT = 'Research note 資安研究, "quoted text"\nSecond line with spaces\n第三行'


def log(message, current=0, total=0):
    print(message + (f' ({current}/{total})' if total else ''), flush=True)


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def wait(condition, label):
    end = time.monotonic() + 90
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError(label)
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def selected_item(window, key):
    return next(window.selection_list.item(i) for i in range(window.selection_list.count())
                if window.selection_list.item(i).data(ROLE_ID) == key)


def edit(window, key, comment, scope='', cancel=False, context=False):
    window.show_document_page()
    window.tabs.setCurrentIndex(window.selection_tab_index)
    item = selected_item(window, key)
    window.selection_list.setCurrentItem(item)
    window.selection_list.scrollToItem(item)
    errors = []

    def fill():
        dialog = QtWidgets.QApplication.activeModalWidget()
        try:
            check(isinstance(dialog, AnnotationDialog), 'selected TTP entry opens native annotation editor')
            check(dialog.scope.currentData() == '', 'selected-list editor starts at all-tactic comment scope')
            if scope:
                dialog.scope.setCurrentIndex(dialog.scope.findData(scope))
            dialog.comment.setPlainText(comment)
            if cancel:
                dialog.reject()
            else:
                dialog.save()
                check(dialog.result() == QtWidgets.QDialog.DialogCode.Accepted, 'comment draft validated and saved')
        except Exception as error:
            errors.append(error)
            if dialog:
                dialog.reject()

    if context:
        window.show_selected_context_menu(window.selection_list.visualItemRect(item).center())
        menu = window.selected_context_menu
        check(menu.actions()[0].text() == 'Edit TTP annotation…', 'selected TTP right-click menu exposes annotation action')
        QtCore.QTimer.singleShot(60, fill)
        menu.actions()[0].trigger()
        if isValid(menu):
            menu.close()
    else:
        check(window.selection_annotation_button.isEnabled(), 'selected TTP annotation button enabled')
        QtCore.QTimer.singleShot(60, fill)
        QtTest.QTest.mouseClick(window.selection_annotation_button, QtCore.Qt.MouseButton.LeftButton)
    if errors:
        raise errors[0]


def read_exports(window, paths):
    for target, fmt in zip(paths, ('json', 'csv')):
        check(window.export_current_document(target, fmt) == target, fmt + ': comments exported')
    for path in paths:
        log(f'Input file: {path}')
    payload = json.loads(paths[0].read_text(encoding='utf-8'))
    with paths[1].open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        check(tuple(reader.fieldnames) == CSV_FIELDS, 'CSV header includes both comment fields')
        rows = list(reader)
    check(paths[1].read_bytes().startswith(b'\xef\xbb\xbf'), 'CSV retains Unicode BOM encoding')
    check({row['technique_id'] for row in rows} == set(payload['selected_technique_ids']), 'JSON/CSV selection membership agrees')
    for row in rows:
        source = next(item for item in payload['selected_ttps'] if item['technique_id'] == row['technique_id'])
        check(row['comment'] == source['comment'] and json.loads(row['tactic_comments']) == source['tactic_comments'],
              row['technique_id'] + ': global/scoped comments survive JSON and CSV readback exactly')
    return payload, rows


def main():
    log(f'Input file: {DATA / "latest.json"}')
    log(f'Input file: {DATA / "v1.0" / "manifest.json"}')
    for path in (REPORT, JSON_SAMPLE, CSV_SAMPLE, SCREEN, *(p for paths in DOMAIN_FILES.values() for p in paths)):
        log(f'Output file: {path}')
    pointers = {p: p.read_bytes() for p in (DATA / 'latest.json', DATA / 'active.json') if p.exists()}
    log('[Comments 1/6] Starting native selected-TTP workspace', 0, 6)
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / 'latest.json')
    window.show()
    wait(lambda: window.loaded_ok and not window.loader.isRunning(), 'startup')
    catalog = window.catalog
    lookup = {external_id(obj): key for key, obj in catalog.records.items()}
    task, parent, sibling = lookup['T1053.005'], lookup['T1053'], lookup['T1053.002']
    first = window.current_document
    check(not window.selection_annotation_button.isEnabled(), 'empty selection disables annotation button')
    window.select_matrix_ttp(task, True)
    window.select_matrix_ttp(parent, True)
    window.apply_technique_fields({task}, {'score': 5.25, 'color': '#123456'})

    log('[Comments 2/6] Button/right-click edits, previews and cancellation', 1, 6)
    edit(window, task, COMMENT, context=True)
    check(first.selected == {task, parent}, 'comment edit preserves existing selections')
    row = next(row for row in first.navigator_layer['techniques'] if row['techniqueID'] == 'T1053.005')
    check(row['comment'] == COMMENT and row['score'] == 5.25 and row['color'] == '#123456', 'individual comment edit preserves score/color')
    check(window.workspace.currentWidget() is window.tabs and window.tabs.currentIndex() == window.selection_tab_index,
          'saving selected annotation keeps Selected Techniques visible')
    check('Comment: Research note' in selected_item(window, task).text() and COMMENT in selected_item(window, task).toolTip(),
          'selected row displays preview and complete multiline tooltip')
    check(technique_comments(first, parent) == ('', []) and technique_comments(first, sibling) == ('', []),
          'child comment is not inherited by parent or sibling')
    before = first.fingerprint()
    edit(window, task, 'Discard this text', cancel=True)
    check(first.fingerprint() == before, 'cancelled annotation preserves complete document state')
    scoped = 'Execution-specific note, "引號"\n保留換行'
    edit(window, task, scoped, scope='execution')
    check(technique_comments(first, task) == (COMMENT, [{'tactic': 'execution', 'comment': scoped}]), 'global and tactic-specific comments remain separate')
    check('Tactic comments: 1' in selected_item(window, task).text() and scoped in selected_item(window, task).toolTip(),
          'selected list exposes scoped comment count and full text')
    edit(window, parent, 'Parent-only comment')
    check(technique_comments(first, task)[0] == COMMENT, 'parent comment edit preserves child annotation')

    log('[Comments 3/6] JSON/CSV multiline comment round trips and failed publication', 2, 6)
    payload, rows = read_exports(window, (JSON_SAMPLE, CSV_SAMPLE))
    exported = next(row for row in payload['selected_ttps'] if row['technique_id'] == 'T1053.005')
    check(exported['comment'] == COMMENT and exported['parent_technique_name'] == catalog.records[parent]['name'],
          'selected JSON embeds child comment beside parent context')
    check(payload['navigator_layer']['techniques'] == first.navigator_layer['techniques'], 'Studio JSON retains complete original annotation rows too')
    check(not first.dirty and first.save_path == JSON_SAMPLE, 'CSV exchange preserves the existing complete Studio saved baseline')
    protected = CSV_SAMPLE.read_bytes()
    before = first.fingerprint(), first.export_path, first.exported_fingerprint
    with patch.object(Path, 'replace', side_effect=PermissionError('audit blocked publication')), patch.object(QtWidgets.QMessageBox, 'critical'):
        check(window.export_current_document(CSV_SAMPLE, 'csv') is None, 'failed CSV comment publication reported')
    check(CSV_SAMPLE.read_bytes() == protected and (first.fingerprint(), first.export_path, first.exported_fingerprint) == before,
          'failed CSV publication preserves existing content and save state')
    check(not list(OUT.glob(CSV_SAMPLE.name + '.*.tmp')), 'failed CSV temporary file removed')
    window.select_matrix_ttp(task, False)
    check(not any(row['technique_id'] == 'T1053.005' for row in document_payload(first)['selected_ttps']), 'unselected TTP comment excluded from selected rows')
    window.select_matrix_ttp(task, True)
    check(technique_comments(first, task)[0] == COMMENT, 'reselecting TTP restores retained comment')
    edit(window, parent, '')
    check(technique_comments(first, parent) == ('', []) and 'Comment:' not in selected_item(window, parent).text(), 'saving blank comment clears preview and export text')
    check(not any(row['techniqueID'] == 'T1053' for row in first.navigator_layer['techniques']),
          'clearing a comment-only annotation removes its empty row to preserve normal matrix styling')

    log('[Comments 4/6] File/domain/version independence', 3, 6)
    window.new_document()
    wait(lambda: window.loaded_ok, 'new document')
    second = window.current_document
    window.select_matrix_ttp(task, True)
    check(technique_comments(second, task) == ('', []), 'new file has independent comments for identical TTP')
    protected = first.fingerprint()
    edit(window, task, 'Second document only')
    check(first.fingerprint() == protected, 'editing another file preserves original comments')
    for domain in ('mobile-attack', 'ics-attack'):
        window.change_document_domain(window.active_document_index, domain)
        wait(lambda: window.loaded_ok, domain + ' tree')
        key = next(iter(window.catalog.records))
        window.select_matrix_ttp(key, True)
        edit(window, key, f'{domain} comment\n中文')
        data, _ = read_exports(window, DOMAIN_FILES[domain])
        check(data['selected_ttps'][0]['comment'] == f'{domain} comment\n中文', domain + ': selected comment exported')
    window.change_document_domain(window.active_document_index, 'enterprise-attack')
    wait(lambda: window.loaded_ok, 'restore Enterprise')
    check(technique_comments(second, task)[0] == 'Second document only', 'domain round trip restores correct comments')
    older = load_catalog(DATA, log, snapshot_pointer(DATA, '1.0'))
    history_key = next(iter(older.records))
    history = TTPDocument('Historical notes', older, selected={history_key})
    update_annotation(history, history_key, '', 'Historical note 古典\nLine two', None, '')
    window.sync_active_document()
    window.documents.append(history)
    window.document_tabs.addTab(history.name)
    window.activate_document(len(window.documents) - 1)
    wait(lambda: window.loaded_ok, 'historical document')
    edit(window, history_key, 'Historical editor note\n保留空格 and quotes "yes"')
    historical, _ = read_exports(window, DOMAIN_FILES['historical'])
    check(historical['attack']['version'] == '1.0' and historical['selected_ttps'][0]['comment'].startswith('Historical editor'),
          'historical selected comments supported in native editor and JSON/CSV')
    check(first.fingerprint() == protected, 'domain/version edits preserve other file annotations')

    log('[Comments 5/6] Preview, empty fields and dataset preservation', 4, 6)
    window.activate_document(window.documents.index(first))
    wait(lambda: window.loaded_ok, 'original document')
    window.show_document_page()
    window.tabs.setCurrentIndex(window.selection_tab_index)
    window.output_panel.hide()
    QtWidgets.QApplication.processEvents()
    check(window.grab().save(str(SCREEN)), 'selected-TTP annotation preview saved')
    check(document_payload(TTPDocument('Empty', catalog))['selected_ttps'] == [], 'empty selection remains header-only in export')
    window.clear_selection()
    check(not window.selection_annotation_button.isEnabled(), 'clearing selections disables comment editor')
    before = first.fingerprint()
    window.edit_selected_annotation(task)
    check(first.fingerprint() == before, 'stale unselected key cannot invoke selected comment edit')
    check(all(path.read_bytes() == data for path, data in pointers.items()), 'comment workflow leaves dataset pointers unchanged')
    window.confirm_studio_changes = lambda *_: 'discard'
    window.close()
    log('[Comments 6/6] Publishing successful audit report', 5, 6)
    REPORT.write_text(json.dumps({'status': 'PASS', 'checks': checks, 'preview': str(SCREEN),
                                 'json_example': str(JSON_SAMPLE), 'csv_example': str(CSV_SAMPLE)}, indent=2) + '\n', encoding='utf-8')
    log(f'[Comments] PASS: {len(checks)} checks', 6, 6)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
