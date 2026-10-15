"""Audit matrix mappings, expansion and shared document selection. Workflow: README.md."""
from pathlib import Path
import csv
import json
import sys
import time

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from attack_catalog import external_id, load_catalog, local_path
from attack_matrix import ALL_PLATFORMS, MATRIX_ID, matrix_columns
from attack_versions import snapshot_pointer
from main import MainWindow, configure_application
from scripts.download_attack_data import write_json

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts'
REPORT = OUT / 'matrix-audit.json'
SCREEN = OUT / 'matrix-preview.png'
JSON_EXPORT = OUT / 'matrix-selection-example.json'
CSV_EXPORT = OUT / 'matrix-selection-example.csv'
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


def column_for(matrix, slug):
    return next(column for column in matrix.columns if column['slug'] == slug)


def root_for(column, key):
    tree = column['tree']
    return next(tree.topLevelItem(number) for number in range(tree.topLevelItemCount())
                if tree.topLevelItem(number).data(0, MATRIX_ID) == key)


def click_checkbox(tree, item):
    tree.scrollToItem(item, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
    QtWidgets.QApplication.processEvents()
    option = QtWidgets.QStyleOptionViewItem()
    option.initFrom(tree)
    option.rect = tree.visualItemRect(item)
    option.features = QtWidgets.QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
    option.checkState = item.checkState(0)
    rect = tree.style().subElementRect(QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator, option, tree)
    QtTest.QTest.mouseClick(tree.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=rect.center())


def main():
    pointer_path = DATA / 'latest.json'
    print(f'Input file: {pointer_path}', flush=True)
    for path in (REPORT, SCREEN, JSON_EXPORT, CSV_EXPORT):
        print(f'Output file: {path}', flush=True)
    log('[Matrix audit 1/7] Reading independent source records and parent mappings')
    pointer = json.loads(pointer_path.read_text(encoding='utf-8-sig'))
    bundle_path = local_path(DATA, pointer['enterprise_bundle'])
    print(f'Input file: {bundle_path}', flush=True)
    raw = json.loads(bundle_path.read_text(encoding='utf-8-sig'))['objects']
    records = {obj['id']: obj for obj in raw if obj.get('type') == 'attack-pattern'
               and not obj.get('revoked') and not obj.get('x_mitre_deprecated')}
    parents = {obj['source_ref']: obj['target_ref'] for obj in raw
               if obj.get('type') == 'relationship' and obj.get('relationship_type') == 'subtechnique-of'
               and not obj.get('revoked') and not obj.get('x_mitre_deprecated')
               and obj.get('source_ref') in records and obj.get('target_ref') in records}
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, pointer_path)
    window.resize(1920, 1080)
    window.show()
    wait(lambda: window.loaded_ok, 'initial catalog')
    catalog = window.catalog
    by_id = {external_id(obj): key for key, obj in catalog.records.items()}
    scheduled_parent, at, task, cron = (by_id[value] for value in ('T1053', 'T1053.002', 'T1053.005', 'T1053.003'))
    log('[Matrix audit 2/7] Comparing every platform/tactic matrix projection with raw source')
    total_rows = 0
    for platform in (ALL_PLATFORMS, *catalog.groups):
        actual = dict(matrix_columns(catalog, platform))
        for slug in catalog.tactic_order:
            expected = {key for key, obj in records.items() if obj.get('x_mitre_platforms')
                        and (platform == ALL_PLATFORMS or platform in obj['x_mitre_platforms'])
                        and any(phase.get('kill_chain_name') == 'mitre-attack' and phase.get('phase_name') == slug
                                for phase in obj.get('kill_chain_phases', []))}
            rows = actual.get(slug, [])
            roots = {row['key'] for row in rows}
            check(roots == {parents.get(key, key) for key in expected}, f'{platform}/{slug}: exact parent families')
            mapped = {row['key'] for row in rows if row['selectable']}
            for row in rows:
                children = set(row['children'])
                check(children == {key for key in expected if parents.get(key) == row['key']}, f'{platform}/{slug}/{external_id(records[row["key"]])}: exact children')
                check(row['selectable'] == (row['key'] in expected), f'{platform}/{slug}/{external_id(records[row["key"]])}: parent checkbox mapping')
                mapped.update(children)
            check(mapped == expected, f'{platform}/{slug}: all selectable IDs mapped')
            total_rows += len(rows)
    log('[Matrix audit 3/7] Opening right-side matrix from the TTP sidebar')
    window.matrix_button.click()
    matrix = window.matrix_view
    wait(lambda: not matrix.building and bool(matrix.columns), 'matrix build')
    check(window.tabs.currentIndex() == window.matrix_tab_index, 'sidebar opens right-side matrix page')
    check([column['slug'] for column in matrix.columns] == [slug for slug, _ in matrix_columns(catalog)], 'official tactic column order')
    check(set(matrix.items_by_id) == set(catalog.records), 'All Platforms includes every selectable technique')
    expected_columns = dict(matrix_columns(catalog))
    for column in matrix.columns:
        tree = column['tree']
        check(tree.topLevelItemCount() == len(expected_columns[column['slug']]), column['slug'] + ': UI header count')
        for row in expected_columns[column['slug']]:
            parent = root_for(column, row['key'])
            check(parent.childCount() == len(row['children']), 'UI children ' + column['slug'] + '/' + external_id(records[row['key']]))
    execution = column_for(matrix, 'execution')
    parent = root_for(execution, scheduled_parent)
    check(parent.childCount() == 5 and parent.text(0).endswith('(5)'), 'all-platform Scheduled Task/Job family count')
    execution['tree'].scrollToItem(parent, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
    QtWidgets.QApplication.processEvents()
    rect = execution['tree'].visualItemRect(parent)
    QtTest.QTest.mouseClick(execution['tree'].viewport(), QtCore.Qt.MouseButton.LeftButton,
                           pos=QtCore.QPoint(max(2, rect.left() - 7), rect.center().y()))
    check(parent.isExpanded(), 'native parent arrow opens sub-techniques')
    log('[Matrix audit 4/7] Native checks synchronize matrix, sidebar and exports')
    child = next(parent.child(number) for number in range(parent.childCount()) if parent.child(number).data(0, MATRIX_ID) == at)
    click_checkbox(execution['tree'], child)
    check(window.selected == {at} and window.tabs.currentIndex() == window.matrix_tab_index, 'matrix checkbox selects child without leaving matrix')
    check(all(item.checkState(0) == QtCore.Qt.CheckState.Checked for item in matrix.items_by_id[at]), 'matrix duplicate checkbox synchronization')
    check(all(item.checkState() == QtCore.Qt.CheckState.Checked for item in window.items_by_id[at]), 'matrix selection reaches sidebar tree')
    check(parent.checkState(0) == QtCore.Qt.CheckState.Unchecked and scheduled_parent not in window.selected, 'child does not implicitly select parent')
    window.clear_selection()
    check(all(item.checkState(0) == QtCore.Qt.CheckState.Unchecked for item in matrix.items_by_id[at]), 'clear selection updates matrix')
    matrix.platform.setCurrentText('Windows')
    wait(lambda: not matrix.building, 'Windows columns')
    parent = root_for(column_for(matrix, 'execution'), scheduled_parent)
    check({parent.child(number).data(0, MATRIX_ID) for number in range(parent.childCount())} == {at, task}, 'Windows family shows only At and Scheduled Task')
    check(parent.text(0).endswith('(2)'), 'Windows family count matches scope')
    window.items_by_id[task][0].setCheckState(QtCore.Qt.CheckState.Checked)
    check(all(item.checkState(0) == QtCore.Qt.CheckState.Checked for item in matrix.items_by_id[task]), 'sidebar selection reaches matrix')
    window.export_current_document(JSON_EXPORT)
    window.export_current_document(CSV_EXPORT)
    check(json.loads(JSON_EXPORT.read_text(encoding='utf-8'))['selected_technique_ids'] == ['T1053.005'], 'matrix selection exports JSON')
    with CSV_EXPORT.open(encoding='utf-8-sig', newline='') as stream:
        check([row['technique_id'] for row in csv.DictReader(stream)] == ['T1053.005'], 'matrix selection exports CSV')
    log('[Matrix audit 5/7] Search, expand/collapse and platform filters')
    matrix.search.setText('T1053.002')
    check(all(root_for(column, scheduled_parent).isExpanded() for column in matrix.columns if column['frame'].isVisible()), 'child search opens matching parent families')
    check(all(column['count'].text().startswith('1/') for column in matrix.columns if column['frame'].isVisible()), 'search counts retain ancestor context')
    matrix.search.setText('nonexistent-matrix-zzzz')
    check(matrix.empty.isVisible(), 'unmatched matrix search empty state')
    matrix.search.clear()
    matrix.collapse_button.click()
    check(not root_for(column_for(matrix, 'execution'), scheduled_parent).isExpanded(), 'Collapse all closes parent families')
    matrix.expand_button.click()
    check(root_for(column_for(matrix, 'execution'), scheduled_parent).isExpanded(), 'Expand all opens parent families')
    matrix.platform.setCurrentText('Linux')
    wait(lambda: not matrix.building, 'Linux columns')
    check(task not in matrix.items_by_id and window.selected == {task}, 'filtering does not remove document selection')
    check(all(not root_for(column, family['key']).flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable
              for column in matrix.columns for family in dict(matrix_columns(catalog, 'Linux'))[column['slug']]
              if not family['selectable']), 'structural-only parents have no checkbox')
    log('[Matrix audit 6/7] Independent documents and historical snapshot restoration')
    first = window.current_document
    window.new_document()
    wait(lambda: not matrix.building, 'new document presentation restored')
    check(not window.selected and first.selected == {task} and not matrix.selected, 'new document clears matrix selection independently')
    matrix.items_by_id[cron][0].setCheckState(0, QtCore.Qt.CheckState.Checked)
    check(window.selected == {cron}, 'new document accepts matrix selection')
    second = window.current_document
    window.document_tabs.setCurrentIndex(0)
    check(window.selected == {task} and matrix.selected == {task} and second.selected == {cron}, 'document tabs restore independent matrix selection')
    old = load_catalog(DATA, log, snapshot_pointer(DATA, '1.0'))
    window.apply_version((old, None))
    wait(lambda: window.loaded_ok and not matrix.building and matrix.catalog is old, 'historical matrix')
    check(window.tabs.currentIndex() == window.matrix_tab_index and matrix.catalog.version == '1.0', 'visible matrix restores with selected historical release')
    check(all(column['tree'].topLevelItem(number).childCount() == 0 for column in matrix.columns
              for number in range(column['tree'].topLevelItemCount())), 'historical release without sub-techniques renders correctly')
    check(second.catalog.version == '19.2', 'other document snapshot preserved')
    window.document_tabs.setCurrentIndex(1)
    wait(lambda: window.loaded_ok and not matrix.building and matrix.catalog is catalog, 'modern matrix restoration')
    matrix.platform.setCurrentText('Linux')
    wait(lambda: not matrix.building, 'restored Linux columns')
    check(window.selected == {cron} and all(item.checkState(0) == QtCore.Qt.CheckState.Checked for item in matrix.items_by_id[cron]), 'document restores original matrix checkboxes and catalog')
    item = matrix.items_by_id[cron][0]
    column_for(matrix, item.data(0, MATRIX_ID + 1))['tree'].itemActivated.emit(item, 0)
    check(window.workspace.currentWidget() is window.details_page and 'Cron' in window.details.toPlainText(), 'matrix activation opens independent technique details')
    window.switch_category('Software')
    check(not window.matrix_button.isVisible(), 'matrix sidebar entry limited to TTP category')
    window.open_matrix()
    check(window.active_category == 'TTP' and window.matrix_button.isVisible(), 'matrix tab returns from library category to TTP context')
    log('[Matrix audit 7/7] Capturing tactic columns with expanded child families')
    window.output_panel.hide()
    window.sidebar.hide()
    matrix.platform.setCurrentText(ALL_PLATFORMS)
    wait(lambda: not matrix.building, 'preview columns')
    matrix.collapse_button.click()
    for slug in ('execution', 'persistence', 'privilege-escalation'):
        column = column_for(matrix, slug)
        parent = root_for(column, scheduled_parent)
        parent.setExpanded(True)
        column['tree'].scrollToItem(parent, QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter)
    matrix.scroll.horizontalScrollBar().setValue(0)
    QtTest.QTest.qWait(180)
    check(window.grab().save(str(SCREEN)), 'matrix screenshot saved')
    window.close()
    write_json(REPORT, {'status': 'PASS', 'checks': checks, 'projection_family_rows': total_rows,
                        'platform_scopes': len(catalog.groups) + 1, 'screenshot': str(SCREEN),
                        'exports': [str(JSON_EXPORT), str(CSV_EXPORT)]})
    log(f'[Matrix audit] PASS: {len(checks)} checks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
