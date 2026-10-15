"""Verify native Navigator layers, color precedence and lossless exchange. Flow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

from PySide6 import QtCore, QtGui, QtWidgets
from attack_catalog import external_id
from attack_matrix import MATRIX_STYLE, MATRIX_SLUG
from main import MainWindow, configure_application
from navigator_dialogs import LayerSettingsDialog, AnnotationDialog
from navigator_integration import (validate_layer, document_layer, update_technique_fields, export_layers,
                                   read_layers, imported_document)
from navigator_visuals import LayerAppearance, gradient_color, DEFAULT_GRADIENT, foreground_color

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts'
REPORT = OUT / 'layers-audit.json'
SCREEN = OUT / 'navigator-layers-preview.png'
SETTINGS_SCREEN = OUT / 'navigator-layer-settings-preview.png'
BUNDLE = OUT / 'navigator-layers-example.json'
SINGLE = OUT / 'native-colored-layer.navigator.json'
STUDIO = OUT / 'native-colored-layer.studio.json'
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


def expect_error(task, label):
    try:
        task()
    except (ValueError, TypeError):
        check(True, label)
    else:
        raise AssertionError(label)


def cell(matrix, key, slug):
    return next(item for item in matrix.items_by_id[key] if item.data(0, MATRIX_SLUG) == slug)


def main():
    log(f'Input file: {DATA / "latest.json"}')
    for path in (REPORT, SCREEN, SETTINGS_SCREEN, BUNDLE, SINGLE, STUDIO):
        log(f'Output file: {path}')
    pointer_bytes = {path: path.read_bytes() for path in (DATA / 'latest.json', DATA / 'active.json') if path.exists()}
    log('[Layers audit 1/7] Color model, gradients and validation', 0, 7)
    gradient = {'colors': ['#ff0000', '#00ff00'], 'minValue': 0, 'maxValue': 100}
    check(gradient_color(-5, gradient) == '#ff0000' and gradient_color(110, gradient) == '#00ff00', 'scores clamp at gradient bounds')
    check(gradient_color(50, gradient) == '#808000', 'RGB midpoint interpolation')
    check(gradient_color(0.5, {'colors': ['#000000', '#ffffff'], 'minValue': 0.25, 'maxValue': 0.75}) == '#808080', 'fractional score/bounds interpolation')
    check(foreground_color('#ffffff') == '#000000' and foreground_color('#000000') == '#ffffff', 'readable foreground contrast')
    probe = {'name': 'Color study', 'domain': 'enterprise-attack', 'versions': {'attack': '19.2', 'layer': '4.5', 'navigator': '5.2.0'},
             'gradient': gradient, 'legendItems': [{'label': '<Research>', 'color': '#ffffff'}],
             'techniques': [{'techniqueID': 'T1053.005', 'score': 50, 'comment': 'global'},
                            {'techniqueID': 'T1053.005', 'tactic': 'execution', 'color': '#123456', 'score': 75},
                            {'techniqueID': 'T1053.005', 'tactic': 'persistence', 'enabled': False}]}
    appearance = LayerAppearance(probe)
    check(appearance.cell('T1053.005', 'execution')['background'] == '#123456', 'explicit tactic color overrides score and global row')
    check(appearance.cell('T1053.005', 'privilege-escalation')['background'] == '#808000', 'global score applies to other tactics')
    check(appearance.cell('T1053.005', 'persistence')['background'] == '#303436', 'disabled rows are grey')
    probe['hideDisabled'] = True
    check(LayerAppearance(probe).cell('T1053.005', 'persistence')['hidden'], 'hideDisabled is separate from color visibility')
    fractional = deepcopy(probe)
    fractional['gradient'] = {'colors': ['#00000000', '#ffffffff'], 'minValue': 0.25, 'maxValue': 0.75}
    check(validate_layer(fractional)['gradient'] == fractional['gradient'], 'SDK validation preserves fractional bounds and alpha stops')
    check(LayerAppearance(fractional).cell('T1053.005', 'discovery')['background'] == '#ffffff', 'RGBA gradient composites correctly')
    for replacement in ({'colors': ['#ffffff'], 'minValue': 0, 'maxValue': 100},
                        {'colors': ['#000000', '#ffffff'], 'minValue': 5, 'maxValue': 5},
                        {'colors': ['#000000', '#ffffff'], 'minValue': 0, 'maxValue': float('inf')}):
        bad = deepcopy(probe)
        bad['gradient'] = replacement
        expect_error(lambda: validate_layer(bad), 'reject malformed gradient ' + str(replacement))
    bad = deepcopy(probe)
    bad['legendItems'] = [{'label': 'bad', 'color': 'red'}]
    expect_error(lambda: validate_layer(bad), 'reject invalid legend without changing input')
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / 'latest.json')
    window.show()
    wait(lambda: window.loaded_ok and not window.loader.isRunning(), 'startup')
    catalog = window.catalog
    first = window.current_document
    lookup = {external_id(obj): key for key, obj in catalog.records.items()}
    task, parent, at = lookup['T1053.005'], lookup['T1053'], lookup['T1053.002']
    log('[Layers audit 2/7] Native row colors and tactic-specific scopes', 1, 7)
    first.name = 'Detection coverage'
    first.navigator_layer = deepcopy(probe)
    first.navigator_layer['hideDisabled'] = False
    first.selected = {task}
    first.navigator_import_selected = {'T1053.005'}
    window.selected = {task}
    window.refresh_selection()
    window.open_matrix()
    matrix = window.matrix_view
    wait(lambda: not matrix.building, 'matrix')
    execution = cell(matrix, task, 'execution')
    persistence = cell(matrix, task, 'persistence')
    privilege = cell(matrix, task, 'privilege-escalation')
    check(execution.background(0).color().name() == '#123456', 'native explicit tactic background visible')
    check(privilege.background(0).color().name() == '#808000', 'native score background visible')
    check(persistence.background(0).color().name() == '#303436', 'imported disabled tactic row remains grey despite document selection')
    check('Score: 50' in privilege.toolTip(0) and 'Comment: global' in privilege.toolTip(0), 'native tooltip includes score/comment')
    check('&lt;Research&gt;' in matrix.legend.text(), 'legend labels escaped before rich-text rendering')
    before = first.fingerprint()
    matrix.show_colors.setChecked(False)
    check(not execution.data(0, MATRIX_STYLE)['background'] and first.fingerprint() == before, 'view-only color toggle leaves annotation data unchanged')
    matrix.show_colors.setChecked(True)
    check(execution.background(0).color().name() == '#123456', 'color toggle restores layer fill')
    first.navigator_layer['hideDisabled'] = True
    window.refresh_selection()
    check(persistence.isHidden() and not execution.isHidden(), 'disabled tactic hidden independently from enabled occurrences')
    first.navigator_layer['hideDisabled'] = False
    window.refresh_selection()
    check(not persistence.isHidden(), 'disabled tactic reappears when hideDisabled cleared')
    column = next(column for column in matrix.columns if column['slug'] == 'execution')
    tree = column['tree']
    matrix.search.setText('Scheduled Task/Job')
    tree.expandAll()
    tree.scrollToItem(execution)
    tree.setCurrentItem(execution)
    QtWidgets.QApplication.processEvents()
    rect = tree.visualItemRect(execution)
    pixel = tree.viewport().grab().toImage().pixelColor(rect.right() - 3, rect.top() + 3).name()
    check(pixel == '#123456', 'actual selected-row painting retains annotation fill over stylesheet')
    log('[Layers audit 3/7] Native color/score editing and layer settings', 2, 7)
    before = first.fingerprint()
    with patch.object(QtWidgets.QColorDialog, 'getColor', return_value=QtGui.QColor()):
        matrix.color_button.click()
    check(first.fingerprint() == before, 'cancel color picker preserves complete document state')
    with patch.object(QtWidgets.QColorDialog, 'getColor', return_value=QtGui.QColor('#ffcc00')):
        matrix.color_button.click()
    check(all(item.background(0).color().name() == '#ffcc00' or not item.data(0, MATRIX_STYLE)['enabled'] for item in matrix.items_by_id[task]), 'bulk color updates all enabled selected occurrences')
    check(first.navigator_layer['techniques'][0]['comment'] == 'global' and first.navigator_layer['techniques'][0]['score'] == 50, 'bulk color preserves score/comments')
    matrix.clear_color_button.click()
    with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('25.5', True)):
        matrix.score_button.click()
    check(privilege.background(0).color().name() == gradient_color(25.5, gradient), 'clearing explicit color exposes fractional score gradient')
    before = first.fingerprint()
    with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('nan', True)), patch.object(QtWidgets.QMessageBox, 'warning'):
        matrix.score_button.click()
    check(first.fingerprint() == before, 'invalid score preserves layer and selection')
    original = deepcopy(first.navigator_layer)
    expect_error(lambda: update_technique_fields(first, {task}, {'color': '#bad'}), 'invalid color update rejected atomically')
    check(first.navigator_layer == original, 'failed color update preserves raw annotations')
    with patch.object(QtWidgets.QColorDialog, 'getColor', return_value=QtGui.QColor('#abcdef')):
        annotation = AnnotationDialog(first, task, window)
        annotation.pick_color.click()
        check(annotation.color.text() == '#abcdef', 'annotation editor native picker populates color field')
        annotation.clear_color.click()
        check(annotation.color.text() == '', 'annotation editor clear button')
        annotation.reject()
    settings = LayerSettingsDialog(first, window)
    settings.minimum.setText('7')
    settings.maximum.setText('7')
    settings.save()
    check(settings.result_layer is None and settings.error.text() and first.navigator_layer == original, 'invalid layer settings remain a draft')
    settings.reject()
    def save_settings(dialog):
        dialog.name.setText('Coverage layer')
        dialog.description.setPlainText('Native matrix research annotations')
        dialog.minimum.setText('0.25')
        dialog.maximum.setText('100.25')
        dialog.colors.setText('#ff6666, #ffe766, #8ec843')
        dialog.add_legend('Covered', '#8ec843')
        dialog.save()
        return dialog.result()
    with patch.object(LayerSettingsDialog, 'exec', save_settings):
        matrix.layer_settings_button.click()
    check(first.name == 'Coverage layer' and first.navigator_layer['description'] == 'Native matrix research annotations', 'layer settings update document name/description')
    check(first.navigator_layer['gradient']['minValue'] == 0.25 and first.navigator_layer['legendItems'][-1]['label'] == 'Covered', 'gradient and legend saved without truncation')
    check('Coverage layer' in matrix.layer_selector.currentText() and 'Covered' in matrix.legend.text(), 'native layer selector and legend refresh immediately')
    check(first.dirty, 'layer settings affect changed-state tracking')
    log('[Layers audit 4/7] New, duplicate and layer switch controls', 3, 7)
    matrix.duplicate_layer_button.click()
    wait(lambda: window.loaded_ok and not matrix.building, 'duplicated layer')
    second = window.current_document
    check(second is not first and second.document_id != first.document_id and second.selected == first.selected, 'duplicate creates independent layer/document identity')
    check(second.navigator_layer['gradient'] == first.navigator_layer['gradient'] and second.export_path is None, 'duplicate preserves layer style with fresh export state')
    window.apply_technique_fields({task}, {'color': '#42a5f5'})
    check(first.navigator_layer != second.navigator_layer and first.navigator_layer['techniques'][0].get('color') != '#42a5f5', 'duplicated annotation data does not alias original')
    matrix.layer_selector.setCurrentIndex(matrix.layer_selector.findData(first.document_id))
    wait(lambda: window.loaded_ok and not matrix.building, 'layer selector')
    check(window.current_document is first and matrix.appearance.layer['name'] == first.name, 'layer dropdown restores active document styles')
    check(window.workspace.currentWidget() is window.tabs and window.tabs.currentIndex() == window.matrix_tab_index, 'layer switch remains in native matrix')
    matrix.new_layer_button.click()
    wait(lambda: window.loaded_ok and not matrix.building, 'new layer')
    third = window.current_document
    check(third.catalog.domain == 'enterprise-attack' and not third.selected and third.navigator_layer['gradient'] == DEFAULT_GRADIENT, 'new layer defaults to Enterprise with empty selections and default gradient')
    check(matrix.layer_selector.count() == len(window.documents), 'layer list excludes independent reference tab')
    matrix.layer_selector.setCurrentIndex(matrix.layer_selector.findData(second.document_id))
    wait(lambda: window.loaded_ok and not matrix.building, 'duplicate restore')
    check(cell(matrix, task, 'execution').background(0).color().name() == '#42a5f5', 'switching layers restores duplicate explicit colors')
    window.close_details_page()
    check(matrix.layer_selector.count() == len(window.documents), 'closing reference does not remove a layer')
    log('[Layers audit 5/7] Lossless single-layer and layer-array exports', 4, 7)
    source_state = [(doc.name, doc.fingerprint(), doc.export_path, doc.exported_fingerprint) for doc in window.documents]
    check(window.export_all_layers(BUNDLE) == BUNDLE, 'export all layers writes Navigator JSON array')
    log(f'Input file: {BUNDLE}')
    layers = read_layers(BUNDLE, log)
    check(len(layers) == len(window.documents) and all(layer['domain'] == 'enterprise-attack' for layer in layers), 'all open layers retained in array with domain/version')
    check(source_state == [(doc.name, doc.fingerprint(), doc.export_path, doc.exported_fingerprint) for doc in window.documents], 'bundle export preserves per-document names/save states')
    check(window.export_current_document(SINGLE, 'navigator') is not None, 'active colored layer exports')
    imported = imported_document(read_layers(SINGLE, log)[0], catalog)
    check(imported.selected == second.selected and imported.navigator_layer['gradient'] == second.navigator_layer['gradient'], 'single layer round trip retains selections and decimal gradient')
    check(imported.navigator_layer['techniques'][0]['color'] == '#42a5f5', 'explicit colors survive export/import')
    window.export_current_document(STUDIO, 'json')
    log(f'Input file: {STUDIO}')
    studio = json.loads(STUDIO.read_text(encoding='utf-8'))
    check(studio['navigator_layer']['legendItems'] == second.navigator_layer['legendItems'], 'Studio JSON preserves legend')
    protected = BUNDLE.read_bytes()
    with patch.object(Path, 'replace', side_effect=PermissionError('audit blocked publication')), patch.object(QtWidgets.QMessageBox, 'critical'):
        check(window.export_all_layers(BUNDLE) is None, 'failed bundle publication reported')
    check(BUNDLE.read_bytes() == protected, 'failed bundle publication preserves previous output')
    check(not list(OUT.glob(BUNDLE.name + '.*.tmp')), 'bundle temporary file cleaned after failure')
    window.import_navigator_layer(BUNDLE)
    dialog = window.integration_dialog
    wait(lambda: dialog.import_button.isEnabled(), 'layer array preview')
    check(dialog.layer.count() == len(layers), 'native import preview lists bundle layers')
    dialog.layer.setCurrentIndex(0)
    dialog.import_button.click()
    wait(lambda: window.loaded_ok, 'layer array commit')
    check(window.current_document.navigator_layer['gradient'] == layers[0]['gradient'], 'bundle layer import restores exact style settings')
    log('[Layers audit 6/7] Technique context menu and all-domain color isolation', 5, 7)
    window.open_matrix()
    wait(lambda: not matrix.building, 'context matrix')
    item = cell(matrix, task, 'execution')
    column = next(column for column in matrix.columns if column['slug'] == 'execution')
    tree = column['tree']
    tree.expandAll()
    tree.scrollToItem(item)
    QtWidgets.QApplication.processEvents()
    matrix.open_cell_menu(tree, tree.visualItemRect(item).center())
    with patch.object(QtWidgets.QColorDialog, 'getColor', return_value=QtGui.QColor('#ffffff')):
        matrix.cell_menu.actions()[0].trigger()
    matrix.cell_menu.close()
    check(cell(matrix, task, 'execution').background(0).color().name() == '#ffffff', 'native context color edits chosen technique')
    check(cell(matrix, task, 'privilege-escalation').background(0).color().name() == '#ffffff', 'technique color applies across tactic columns')
    for domain in ('mobile-attack', 'ics-attack'):
        window.change_document_domain(window.active_document_index, domain)
        wait(lambda: window.loaded_ok, 'domain switch')
        key = next(iter(window.catalog.records))
        window.apply_technique_fields({key}, {'color': '#11aa77', 'score': 10.5})
        window.open_matrix()
        wait(lambda: not matrix.building, 'domain colored matrix')
        check(all(item.background(0).color().name() == '#11aa77' for item in matrix.items_by_id[key]), domain + ': native technique colors')
        check(document_layer(window.current_document)['domain'] == domain, domain + ': colored layer export domain')
    window.change_document_domain(window.active_document_index, 'enterprise-attack')
    wait(lambda: window.loaded_ok, 'Enterprise style restore')
    window.open_matrix()
    wait(lambda: not matrix.building, 'preview matrix')
    check(cell(matrix, task, 'execution').background(0).color().name() == '#ffffff', 'domain round trip restores scoped colors')
    log('[Layers audit 7/7] Visible previews and final report', 6, 7)
    window.apply_technique_fields({parent}, {'score': 10})
    window.apply_technique_fields({at}, {'color': '#42a5f5'})
    matrix.search.setText('Scheduled Task/Job')
    matrix.expand_button.click()
    for column in matrix.columns:
        for item in matrix.items_by_id.get(task, []):
            if item.treeWidget() is column['tree']:
                column['tree'].scrollToItem(item)
    window.sidebar.hide()
    window.output_panel.hide()
    QtWidgets.QApplication.processEvents()
    check(window.grab().save(str(SCREEN)), 'colored-layer matrix screenshot')
    settings = LayerSettingsDialog(window.current_document, window)
    settings.show()
    QtWidgets.QApplication.processEvents()
    check(settings.grab().save(str(SETTINGS_SCREEN)), 'layer settings screenshot')
    settings.reject()
    check(all(path.read_bytes() == content for path, content in pointer_bytes.items()), 'layer audit leaves dataset pointers unchanged')
    window.close()
    REPORT.write_text(json.dumps({'status': 'PASS', 'checks': checks, 'preview': str(SCREEN), 'bundle': str(BUNDLE)}, indent=2) + '\n', encoding='utf-8')
    log(f'[Layers audit] PASS: {len(checks)} checks', 7, 7)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
