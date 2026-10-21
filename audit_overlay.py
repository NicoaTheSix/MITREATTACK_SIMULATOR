"""Verify read-only all-layer overlays and deterministic color mixing. Flow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id, load_catalog
from attack_matrix import MATRIX_STYLE, MATRIX_SLUG
from attack_versions import snapshot_pointer
from main import MainWindow, configure_application
from navigator_integration import document_layer
from navigator_visuals import LayerAppearance, OverlayAppearance, blend_colors, DEFAULT_GRADIENT
from ttp_documents import TTPDocument, export_document_json

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts'
REPORT = OUT / 'overlay-audit.json'
SCREEN = OUT / 'navigator-all-layers-preview.png'
EXPORT = OUT / 'overlay-source-example.json'
checks = []


def log(message, current=0, total=0):
    print(message + (f' ({current}/{total})' if total else ''), flush=True)


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def wait(condition, name):
    end = time.monotonic() + 60
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError(name)
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def payload(name, rows, domain='enterprise-attack', version='19.2', **fields):
    return {'name': name, 'domain': domain, 'versions': {'attack': version, 'layer': '4.5', 'navigator': '5.2.0'},
            'techniques': rows, **fields}


def states(documents):
    return [(doc.document_id, doc.fingerprint(), doc.export_path, doc.export_format, doc.exported_fingerprint)
            for doc in documents]


def cell(matrix, key, slug):
    return next(item for item in matrix.items_by_id[key] if item.data(0, MATRIX_SLUG) == slug)


def main():
    log(f'Input file: {DATA / "latest.json"}')
    for path in (REPORT, SCREEN, EXPORT):
        log(f'Output file: {path}')
    pointers = {path: path.read_bytes() for path in (DATA / 'latest.json', DATA / 'active.json') if path.exists()}
    log('[Overlay audit 1/6] Mixing, scopes, disabled and transparent colors', 0, 6)
    red = payload('Red', [{'techniqueID': 'T1053.005', 'color': '#ff0000', 'comment': 'red note'}])
    blue = payload('Blue', [{'techniqueID': 'T1053.005', 'color': '#0000ff'},
                            {'techniqueID': 'T1053.002', 'color': '#00ff00'}])
    empty = payload('Empty', [])
    disabled = payload('Disabled', [{'techniqueID': 'T1053.005', 'color': '#00ff00', 'enabled': False}], hideDisabled=True)
    check(blend_colors(['#ff0000', '#0000ff']) == '#800080', 'red plus blue yields equal-weight purple')
    check(blend_colors(['#ff0000', '#00ff00', '#0000ff']) == '#555555', 'three-layer RGB average')
    check(blend_colors(['#ff0000', '#ff0000']) == '#ff0000', 'same colors retain their original color')
    overlay = OverlayAppearance([('Red', red), ('Blue', blue), ('Empty', empty), ('Disabled', disabled)], disabled)
    result = overlay.cell('T1053.005', 'execution')
    check(result['background'] == '#800080' and len(result['sources']) == 2, 'empty/disabled layers do not dilute overlap')
    check(not result['hidden'] and result['enabled'], 'visible source defeats active disabled/hide setting')
    check(overlay.cell('T1053.002', 'execution')['background'] == '#00ff00', 'single-source cell keeps its original color')
    check(not overlay.cell('T1053', 'execution')['background'], 'parent does not inherit child overlap')
    reversed_overlay = OverlayAppearance([('Blue', blue), ('Red', red)], red)
    check(reversed_overlay.cell('T1053.005', 'execution')['background'] == result['background'], 'blend independent of layer order')
    scoped = deepcopy(blue)
    scoped['techniques'].append({'techniqueID': 'T1053.005', 'tactic': 'execution', 'color': '#00ff00'})
    scoped_overlay = OverlayAppearance([('Red', red), ('Blue', scoped)], red)
    check(scoped_overlay.cell('T1053.005', 'execution')['background'] == '#808000', 'tactic-specific color used before blending')
    check(scoped_overlay.cell('T1053.005', 'persistence')['background'] == '#800080', 'tactic color cannot leak into another column')
    scored = payload('Scored', [{'techniqueID': 'T1053.005', 'score': 50}],
                     gradient={'colors': ['#000000', '#ffffff'], 'minValue': 0, 'maxValue': 100})
    check(OverlayAppearance([('Red', red), ('Score', scored)], red).cell('T1053.005', 'execution')['background'] == '#c04040', 'score gradient contributes its rendered color')
    transparent = payload('Transparent', [{'techniqueID': 'T1053.005', 'score': 0}],
                          gradient={'colors': ['#ff000000', '#ff0000ff'], 'minValue': 0, 'maxValue': 100})
    check(OverlayAppearance([('Blue', blue), ('Transparent', transparent)], blue).cell('T1053.005', 'execution')['background'] == '#0000ff', 'fully transparent gradient does not dilute colors')
    no_contributors = OverlayAppearance([('Disabled', disabled)], disabled)
    check(no_contributors.cell('T1053.005', 'execution')['hidden'], 'no colored sources preserve active disabled view')
    cached = overlay.cell('T1053.005', 'execution')
    cached['background'] = ''
    check(overlay.cell('T1053.005', 'execution')['background'] == '#800080', 'view-only paint changes cannot corrupt cached blend')
    legend = payload('Legend', [], legendItems=[{'label': '<tag>', 'color': '#ff0000'}] * 100)
    many = OverlayAppearance([('Many', legend)], legend)
    check(len(many.layer['legendItems']) == 64 and many.legend_truncated, 'combined legend bounded without discarding source data')
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / 'latest.json')
    window.show()
    wait(lambda: window.loaded_ok and not window.loader.isRunning(), 'startup')
    catalog = window.catalog
    for layer in (red, blue, empty, disabled):
        layer['versions']['attack'] = catalog.version
    lookup = {external_id(obj): key for key, obj in catalog.records.items()}
    task, at, parent = lookup['T1053.005'], lookup['T1053.002'], lookup['T1053']
    first = window.current_document
    first.name = 'Red layer'
    first.navigator_layer = deepcopy(red)
    first.selected = {task}
    window.selected = {task}
    window.refresh_selection()
    second = TTPDocument('Blue layer', catalog, selected={task, at}, navigator_layer=deepcopy(blue))
    window.install_imported_document(second)
    third = TTPDocument('Empty layer', catalog)
    window.install_imported_document(third)
    disabled_layer = deepcopy(disabled)
    disabled_layer['techniques'].append({'techniqueID': 'T1053.005', 'tactic': 'privilege-escalation', 'enabled': True})
    fourth = TTPDocument('Disabled layer', catalog, selected={task}, navigator_layer=disabled_layer,
                         navigator_import_selected={'T1053.005'})
    window.install_imported_document(fourth)
    mobile = catalog.for_domain('mobile-attack')
    fifth = TTPDocument('Mobile layer', mobile)
    window.install_imported_document(fifth)
    wait(lambda: window.loaded_ok, 'Mobile layer install')
    old = load_catalog(DATA, log, snapshot_pointer(DATA, '11.3'))
    old_key = next(key for key, obj in old.records.items() if external_id(obj) == 'T1053.005')
    sixth = TTPDocument('Other release', old, selected={old_key},
                        navigator_layer=payload('Other release', [{'techniqueID': 'T1053.005', 'color': '#00ff00'}], version='11.3'))
    window.install_imported_document(sixth)
    wait(lambda: window.loaded_ok, 'historical layer install')
    window.activate_document(0)
    wait(lambda: window.loaded_ok, 'Red layer activation')
    window.open_matrix()
    matrix = window.matrix_view
    wait(lambda: not matrix.building, 'native matrix')
    log('[Overlay audit 2/6] Native all-layer toggle, painting and source provenance', 1, 6)
    before = states(window.documents)
    matrix.show_all_layers.setChecked(True)
    item = cell(matrix, task, 'execution')
    check(item.background(0).color().name() == '#800080', 'native matrix shows blended overlap')
    check('4/6' in matrix.overlay_info.text() and '2 other-domain/version' in matrix.overlay_info.text(), 'overlay reports exact compatible/excluded counts')
    check('Editing: Red layer' in matrix.overlay_info.text(), 'active edit target explicit in overlay view')
    check('Red layer: #ff0000' in item.toolTip(0) and 'Blue layer: #0000ff' in item.toolTip(0), 'tooltip lists source names and colors')
    check('Overlay: 2 layer(s)' in item.toolTip(0) and 'red note' in item.toolTip(0), 'tooltip includes overlap count and source comment')
    check(cell(matrix, at, 'execution').background(0).color().name() == '#00ff00', 'other-file-only technique visible')
    check(cell(matrix, at, 'execution').checkState(0) == QtCore.Qt.CheckState.Unchecked and window.selected == {task}, 'overlay never unions source selections into active document')
    check(states(window.documents) == before, 'toggle leaves all document fingerprints/save state unchanged')
    matrix.search.setText('Scheduled Task/Job')
    matrix.expand_button.click()
    column = next(column for column in matrix.columns if column['slug'] == 'execution')
    tree = column['tree']
    tree.scrollToItem(item)
    tree.setCurrentItem(item)
    QtWidgets.QApplication.processEvents()
    rect = tree.visualItemRect(item)
    check(tree.viewport().grab().toImage().pixelColor(rect.right() - 3, rect.top() + 3).name() == '#800080', 'actual selected-row painted pixel retains blended fill')
    # Expanding families is now a saved layer preference; compare color-only
    # view changes against the state after that deliberate edit.
    before = states(window.documents)
    matrix.show_colors.setChecked(False)
    check(not item.data(0, MATRIX_STYLE)['background'], 'color hiding works in overlay view')
    matrix.show_colors.setChecked(True)
    check(item.background(0).color().name() == '#800080' and states(window.documents) == before, 'restoring colors uses intact cached blend without edits')
    matrix.show_all_layers.setChecked(False)
    check(item.background(0).color().name() == '#ff0000' and matrix.overlay_info.isHidden(), 'leaving overlay restores active colors and hides scope label')
    check(states(window.documents) == before, 'leaving overlay preserves every source document')
    log('[Overlay audit 3/6] Edit routing and layer switching', 2, 6)
    matrix.show_all_layers.setChecked(True)
    blue_before = second.fingerprint()
    window.apply_technique_fields({task}, {'color': '#00ff00'})
    check(item.background(0).color().name() == '#008080', 'active color edit immediately recomputes overlay')
    check(second.fingerprint() == blue_before, 'editing overlay does not modify another file')
    window.apply_technique_fields({task}, {'color': '#ff0000'})
    matrix.layer_selector.setCurrentIndex(matrix.layer_selector.findData(second.document_id))
    wait(lambda: window.loaded_ok and not matrix.building, 'Blue layer switch')
    check(matrix.show_all_layers.isChecked() and cell(matrix, task, 'execution').background(0).color().name() == '#800080', 'layer switch preserves overlay and order-independent colors')
    check('Editing: Blue layer' in matrix.overlay_info.text() and window.current_document is second, 'layer switch updates edit target')
    matrix.platform.setCurrentText('Windows')
    wait(lambda: not matrix.building, 'platform rebuild')
    check(cell(matrix, task, 'execution').background(0).color().name() == '#800080', 'platform rebuild retains combined colors')
    with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('Renamed Red', True)):
        window.rename_document(0)
    check('Renamed Red: #ff0000' in cell(matrix, task, 'execution').toolTip(0), 'inactive rename refreshes source provenance')
    window.show_record(task)
    window.close_details_page()
    check(matrix.show_all_layers.isChecked() and matrix.overlay_info.text().startswith('All layers: 4/6'), 'reference close does not change overlay layer membership')
    log('[Overlay audit 4/6] Membership changes, duplicates and domain isolation', 3, 6)
    window.change_document_domain(0, 'mobile-attack')
    check('3/6' in matrix.overlay_info.text() and cell(matrix, task, 'execution').background(0).color().name() == '#0000ff', 'inactive domain change immediately removes foreign layer contribution')
    window.change_document_domain(0, 'enterprise-attack')
    check('4/6' in matrix.overlay_info.text() and cell(matrix, task, 'execution').background(0).color().name() == '#800080', 'inactive domain restore recomputes original blend')
    matrix.duplicate_layer_button.click()
    wait(lambda: window.loaded_ok and not matrix.building, 'duplicate while overlay')
    duplicate = window.current_document
    check('5/7' in matrix.overlay_info.text() and cell(matrix, task, 'execution').background(0).color().name() == '#5500aa', 'new duplicate participates as independent colored source')
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Discard):
        window.close_document(window.document_index(duplicate.document_id))
    wait(lambda: window.loaded_ok and not matrix.building, 'close duplicate')
    window.select_navigator_layer(second.document_id)
    wait(lambda: window.loaded_ok and not matrix.building, 'restore Blue target')
    check('4/6' in matrix.overlay_info.text() and cell(matrix, task, 'execution').background(0).color().name() == '#800080', 'closing a layer removes it from composite')
    window.select_navigator_layer(fifth.document_id)
    wait(lambda: window.loaded_ok and not matrix.building, 'Mobile overlay')
    check('1/6 matching Mobile' in matrix.overlay_info.text(), 'active domain determines overlay membership')
    mobile_key = next(iter(window.catalog.records))
    window.apply_technique_fields({mobile_key}, {'color': '#11aa77'})
    check(all(row.background(0).color().name() == '#11aa77' for row in matrix.items_by_id[mobile_key]), 'single Mobile source retains exact color')
    window.select_navigator_layer(sixth.document_id)
    wait(lambda: window.loaded_ok and not matrix.building, 'old release overlay')
    check('1/6 matching Enterprise v11.3' in matrix.overlay_info.text(), 'active release determines overlay membership')
    check(all(row.background(0).color().name() == '#00ff00' for row in matrix.items_by_id[old_key]), 'other release color never mixed with current release')
    window.select_navigator_layer(fourth.document_id)
    wait(lambda: window.loaded_ok and not matrix.building, 'disabled target overlay')
    check(cell(matrix, task, 'execution').background(0).color().name() == '#800080' and not cell(matrix, task, 'execution').isHidden(), 'colored sources visible despite active hideDisabled setting')
    matrix.show_all_layers.setChecked(False)
    check(cell(matrix, task, 'execution').isHidden(), 'leaving overlay restores active hideDisabled behavior')
    matrix.show_all_layers.setChecked(True)
    check(not cell(matrix, task, 'execution').isHidden(), 'returning to overlay restores other visible contributors')
    log('[Overlay audit 5/6] Export remains original active layer', 4, 6)
    window.select_navigator_layer(first.document_id)
    wait(lambda: window.loaded_ok and not matrix.building, 'source export target')
    before = states(window.documents)
    exported_layer = document_layer(first)
    row = next(row for row in exported_layer['techniques'] if row['techniqueID'] == 'T1053.005')
    check(row['color'] == '#ff0000', 'Navigator export projection contains source red rather than mixed purple')
    check(states(window.documents) == before, 'generating export projection does not mutate documents')
    export_document_json(first, EXPORT, log)
    log(f'Input file: {EXPORT}')
    data = json.loads(EXPORT.read_text(encoding='utf-8'))
    check(data['navigator_layer']['techniques'][0]['color'] == '#ff0000' and data['selected_count'] == 1, 'Studio JSON preserves original annotations and selection only')
    window.update_document_labels()
    check(cell(matrix, task, 'execution').background(0).color().name() == '#800080', 'export/rename does not replace combined view with source color')
    log('[Overlay audit 6/6] Preview and pointer preservation', 5, 6)
    matrix.platform.setCurrentText('All Platforms')
    wait(lambda: not matrix.building, 'preview matrix')
    matrix.search.setText('Scheduled Task/Job')
    matrix.expand_button.click()
    window.sidebar.hide()
    window.output_panel.hide()
    for column in matrix.columns:
        for row in matrix.items_by_id[task]:
            if row.treeWidget() is column['tree']:
                column['tree'].scrollToItem(row)
    QtWidgets.QApplication.processEvents()
    check(window.grab().save(str(SCREEN)), 'all-layer color preview saved')
    check(all(path.read_bytes() == content for path, content in pointers.items()), 'overlay workflow leaves dataset pointers unchanged')
    window.confirm_studio_changes = lambda *_: "discard"
    window.close()
    REPORT.write_text(json.dumps({'status': 'PASS', 'checks': checks, 'preview': str(SCREEN)}, indent=2) + '\n', encoding='utf-8')
    log(f'[Overlay audit] PASS: {len(checks)} checks', 6, 6)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
