"""Exercise technique context actions and searchable layer source pickers. Flow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

from PySide6 import QtCore, QtGui, QtWidgets, QtTest
from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from attack_matrix import MATRIX_SLUG, MATRIX_STYLE
from main import MainWindow, configure_application
from navigator_integration import document_layer, update_technique_fields
from ttp_documents import TTPDocument

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
REPORT = ROOT / 'artifacts' / 'matrix-actions-audit.json'
SCREEN = ROOT / 'artifacts' / 'navigator-source-picker-preview.png'
POPUP = ROOT / 'artifacts' / 'navigator-source-search-preview.png'
checks = []


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


def cell(matrix, key, slug):
    return next(item for item in matrix.items_by_id[key] if item.data(0, MATRIX_SLUG) == slug)


def context(matrix, key, slug='execution'):
    item = cell(matrix, key, slug)
    tree = item.treeWidget()
    tree.expandAll()
    tree.scrollToItem(item)
    QtWidgets.QApplication.processEvents()
    matrix.open_cell_menu(tree, tree.visualItemRect(item).center())
    return matrix.cell_menu


def main():
    log(f'Input file: {DATA / "latest.json"}')
    log(f'Input file: {DATA / "v11.3" / "manifest.json"}')
    for path in (REPORT, SCREEN, POPUP):
        log(f'Output file: {path}')
    pointers = {p: p.read_bytes() for p in (DATA / 'latest.json', DATA / 'active.json') if p.exists()}
    log('[Matrix actions 1/6] Starting native workspace', 0, 6)
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / 'latest.json')
    window.show()
    wait(lambda: window.loaded_ok and not window.loader.isRunning(), 'startup')
    catalog = window.catalog
    lookup = {external_id(obj): key for key, obj in catalog.records.items()}
    task, parent = lookup['T1053.005'], lookup['T1053']
    first = window.current_document
    window.open_matrix()
    matrix = window.matrix_view
    wait(lambda: not matrix.building, 'matrix')
    matrix.search.setText('Scheduled Task/Job')

    log('[Matrix actions 2/6] No-op clears and technique-wide actions', 1, 6)
    before = first.fingerprint()
    neutral = deepcopy(cell(matrix, task, 'execution').data(0, MATRIX_STYLE))
    menu = context(matrix, task)
    check(all('technique' in action.text().lower() and 'tactic' not in action.text().lower()
              for action in menu.actions()), 'all context menu labels describe techniques')
    menu.actions()[1].trigger()
    menu.close()
    check(first.fingerprint() == before and not first.navigator_layer, 'clear uncolored unchecked technique creates no row or dirty change')
    check(cell(matrix, task, 'execution').data(0, MATRIX_STYLE) == neutral, 'uncolored unchecked technique display stays unchanged')
    window.select_matrix_ttp(task, True)
    before = first.fingerprint()
    blue = cell(matrix, task, 'execution').background(0).color().name()
    check(blue == '#007acc', 'selected technique without stored annotation uses selection blue')
    matrix.clear_color_button.click()
    check(first.fingerprint() == before and cell(matrix, task, 'execution').background(0).color().name() == blue,
          'bulk clear without explicit color preserves default selection display')
    window.apply_technique_fields({task}, {'score': 35})
    before = first.fingerprint()
    scored = deepcopy(cell(matrix, task, 'execution').data(0, MATRIX_STYLE))
    check(not update_technique_fields(first, {task}, {'color': ''}), 'model reports absent color clear as unchanged')
    matrix.clear_color_button.click()
    check(first.fingerprint() == before and cell(matrix, task, 'execution').data(0, MATRIX_STYLE) == scored,
          'score-only technique clear preserves gradient and source data')
    first.navigator_layer['techniques'][0]['color'] = ''
    before = first.fingerprint()
    check(not update_technique_fields(first, {task}, {'color': ''}) and first.fingerprint() == before,
          'already empty stored color is a byte-equivalent no-op')
    first.navigator_layer['techniques'] = [
        {'techniqueID': 'T1053.005', 'tactic': 'execution', 'color': '#123456', 'score': 30, 'comment': 'keep'},
        {'techniqueID': 'T1053.005', 'tactic': 'persistence', 'enabled': False, 'comment': 'disabled'}]
    first.navigator_import_selected = {'T1053.005'}
    window.refresh_selection()
    menu = context(matrix, task)
    with patch.object(QtWidgets.QColorDialog, 'getColor', return_value=QtGui.QColor('#ffffff')):
        menu.actions()[0].trigger()
    menu.close()
    check(all(cell(matrix, task, slug).background(0).color().name() == '#ffffff'
              for slug in ('execution', 'privilege-escalation')), 'context assignment colors every enabled tactic occurrence')
    check(cell(matrix, task, 'persistence').background(0).color().name() == '#303436', 'context assignment preserves disabled scope')
    check(parent not in first.selected and all(not item.data(0, MATRIX_STYLE)['background'] for item in matrix.items_by_id[parent]),
          'sub-technique context color does not select or color parent')
    original = deepcopy(first.navigator_layer)
    menu = context(matrix, task)
    menu.actions()[1].trigger()
    menu.close()
    expected = deepcopy(original)
    for row in expected['techniques']:
        row.pop('color', None)
    expected['techniques'] = [row for row in expected['techniques'] if set(row) - {'techniqueID', 'tactic'}]
    check(first.navigator_layer == expected and first.selected == {task}, 'clear removes only actual colors and preserves annotations and selection')
    before = first.fingerprint()
    matrix.clear_color_button.click()
    check(first.fingerprint() == before, 'repeated clear is a no-op')
    menu = context(matrix, task)
    with patch.object(window, 'edit_navigator_annotation') as editor:
        menu.actions()[2].trigger()
        check(editor.call_args.args == (task, '', True), 'context annotation editor defaults to all-tactic technique scope')
    menu.close()

    log('[Matrix actions 3/6] Searchable source choices and exact batch membership', 2, 6)
    matrix.search.clear()
    window.clear_selection()
    source_types = {'Campaign': {'campaign'}, 'Software': {'malware', 'tool'}, 'Group': {'intrusion-set'}}
    chosen = {}
    for kind, types in source_types.items():
        matrix.source_kind.setCurrentText(kind)
        objects = [obj for obj in catalog.objects_by_domain[catalog.domain].values() if obj.get('type') in types]
        check(matrix.source_picker.count() == len(objects), kind + ': dropdown includes every active source')
        matrix.source_picker.showPopup()
        check(matrix.source_picker.view().isVisible(), kind + ': click opens source list')
        matrix.source_picker.hidePopup()
        obj = next(obj for obj in objects if ' ' in obj['name'] and catalog.techniques_by_source[catalog.domain].get(obj['id']))
        text = f"{external_id(obj)}  {obj['name']}"
        chosen[kind] = text
        line = matrix.source_picker.lineEdit()
        line.setFocus()
        line.clear()
        QtTest.QTest.keyClicks(line, obj['name'])
        check(matrix.source_picker.currentText() == obj['name'], kind + ': typed search retains spaces')
        matrix.source_completer.setCompletionPrefix(obj['name'].swapcase())
        check(matrix.source_completer.completionCount() > 0, kind + ': name substring search ignores case')
        matrix.source_completer.setCompletionPrefix(external_id(obj).lower())
        check(matrix.source_completer.completionCount() > 0, kind + ': ATT&CK ID search ignores case')
        matrix.source_completer.activated[str].emit(text)
        expected_keys = {r['target_ref'] for r in catalog.techniques_by_source[catalog.domain][obj['id']]} & catalog.records.keys()
        window.clear_selection()
        check(matrix.add_source_button.isEnabled() and str(len(expected_keys)) in matrix.add_source_button.text(), kind + ': resolved count shown')
        matrix.add_source_button.click()
        check(window.selected == expected_keys and first.selected == expected_keys, kind + ': button adds exact direct TTP relationships')
        check(window.tabs.currentIndex() == window.matrix_tab_index and window.workspace.currentWidget() is window.tabs,
              kind + ': bulk action keeps matrix open')
        check(all(item.checkState(0) == QtCore.Qt.CheckState.Checked for key in expected_keys for item in matrix.items_by_id[key]),
              kind + ': all matrix occurrences synchronized')
        before = first.fingerprint()
        matrix.add_source_button.click()
        check(first.fingerprint() == before, kind + ': repeat add deduplicates without mutations')
        matrix.source_picker.setEditText('this source does not exist')
        matrix.add_source_button.click()
        check(not matrix.add_source_button.isEnabled() and first.fingerprint() == before, kind + ': arbitrary text cannot reuse stale currentData')
    matrix.source_picker.setCurrentIndex(0)
    matrix.source_picker.setEditText('')
    check(not matrix.add_source_button.isEnabled(), 'clearing source text disables add')

    log('[Matrix actions 4/6] Layer/domain/version isolation and filter persistence', 3, 6)
    window.new_document()
    wait(lambda: window.loaded_ok, 'new document')
    window.open_matrix()
    wait(lambda: not matrix.building, 'new document matrix')
    matrix.source_kind.setCurrentText('Group')
    matrix.choose_source_completion(chosen['Group'])
    second = window.current_document
    protected = first.fingerprint()
    matrix.show_all_layers.setChecked(True)
    matrix.add_source_button.click()
    check(second.selected and first.fingerprint() == protected, 'source bulk action under overlay changes only active layer')
    query = matrix.source_picker.currentText()
    matrix.platform.setCurrentText('Windows')
    wait(lambda: not matrix.building, 'platform rebuild')
    check(matrix.source_picker.currentText() == query and matrix.add_source_button.isEnabled(), 'platform filter preserves source choice')
    matrix.platform.setCurrentText('All Platforms')
    wait(lambda: not matrix.building, 'all platforms')
    for domain in ('mobile-attack', 'ics-attack'):
        window.change_document_domain(window.active_document_index, domain)
        wait(lambda: window.loaded_ok, domain + ' startup')
        window.open_matrix()
        wait(lambda: not matrix.building, domain + ' matrix')
        check(not matrix.source_picker.currentText() and not matrix.add_source_button.isEnabled(), domain + ': stale source cleared')
        for kind, types in source_types.items():
            matrix.source_kind.setCurrentText(kind)
            objects = [o for o in window.catalog.objects_by_domain[domain].values() if o.get('type') in types]
            check(matrix.source_picker.count() == len(objects), domain + '/' + kind + ': exact active-domain entries')
            valid = next((o for o in objects if window.catalog.techniques_by_source[domain].get(o['id'])), None)
            if valid:
                matrix.choose_source_completion(f"{external_id(valid)}  {valid['name']}")
                window.clear_selection()
                matrix.add_source_button.click()
                expected_keys = {r['target_ref'] for r in window.catalog.techniques_by_source[domain][valid['id']]} & window.catalog.records.keys()
                check(window.selected == expected_keys, domain + '/' + kind + ': exact direct selection')
            elif not objects:
                check(not matrix.source_picker.isEnabled() and not matrix.add_source_button.isEnabled(), domain + '/' + kind + ': absent source kind disabled')
        check(first.fingerprint() == protected, domain + ': other layer unchanged')
    older = load_catalog(DATA, log, snapshot_pointer(DATA, '11.3'))
    matrix.set_catalog(older, set())
    wait(lambda: not matrix.building, 'historical matrix')
    matrix.source_kind.setCurrentText('Group')
    check(matrix.source_catalog.version == '11.3' and not matrix.source_picker.currentText(), 'version change clears source choice and indexes exact snapshot')
    historical = {o['id'] for o in older.objects_by_domain[older.domain].values() if o.get('type') == 'intrusion-set'}
    check(set(matrix.source_entries.values()) == historical, 'historical source list matches cached historical data')

    log('[Matrix actions 5/6] Preview and export projection', 4, 6)
    window.activate_document(window.documents.index(first))
    wait(lambda: window.loaded_ok, 'restore first')
    window.open_matrix()
    wait(lambda: not matrix.building, 'preview matrix')
    matrix.source_kind.setCurrentText('Group')
    matrix.choose_source_completion(chosen['Group'])
    window.output_panel.hide()
    QtWidgets.QApplication.processEvents()
    check(window.grab().save(str(SCREEN)), 'source-picker matrix preview saved')
    query = chosen['Group'].split('  ', 1)[1]
    matrix.source_picker.setEditText(query)
    matrix.source_completer.setCompletionPrefix(query)
    matrix.source_completer.complete()
    QtWidgets.QApplication.processEvents()
    check(matrix.source_completer.popup().grab().save(str(POPUP)), 'filtered source completion preview saved')
    matrix.source_completer.popup().hide()
    projected = document_layer(first)
    check({r['techniqueID'] for r in projected['techniques'] if r.get('enabled', True)} <=
          {external_id(first.catalog.records[k]) for k in first.selected}, 'source selection remains exportable without unrelated enabled TTPs')
    check(all(path.read_bytes() == content for path, content in pointers.items()), 'dataset pointers remain unchanged')
    window.close()
    log('[Matrix actions 6/6] Writing successful audit report', 5, 6)
    REPORT.write_text(json.dumps({'status': 'PASS', 'checks': checks, 'preview': str(SCREEN), 'search_preview': str(POPUP)}, indent=2) + '\n', encoding='utf-8')
    log(f'[Matrix actions] PASS: {len(checks)} checks', 6, 6)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
