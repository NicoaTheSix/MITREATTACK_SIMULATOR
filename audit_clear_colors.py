"""Reproduce color-switch/clear residue using real matrix row pixels. Workflow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import time

from PySide6 import QtCore, QtWidgets, QtTest
from attack_catalog import external_id
from attack_matrix import MATRIX_SLUG, MATRIX_STYLE
from main import MainWindow, configure_application
from navigator_integration import document_layer, SELECTION_MARKER

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts'
REPORT = OUT / 'clear-colors-audit.json'
PREVIEWS = {name: OUT / f'clear-colors-{name}.png'
            for name in ('original', 'yellow', 'cleared-unchecked', 'cleared-checked')}
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


def cell(matrix, key, slug='initial-access'):
    return next(item for item in matrix.items_by_id[key] if item.data(0, MATRIX_SLUG) == slug)


def painted_row(window, item):
    tree = item.treeWidget()
    tree.setCurrentItem(item)
    tree.setFocus()
    tree.scrollToItem(item)
    QtTest.QTest.mouseMove(window.matrix_view.search, QtCore.QPoint(8, 8))
    QtTest.QTest.qWait(30)
    return tree.viewport().grab().toImage().copy(tree.visualItemRect(item))


def clear_context(matrix, item):
    tree = item.treeWidget()
    tree.setCurrentItem(item)
    tree.scrollToItem(item)
    QtWidgets.QApplication.processEvents()
    matrix.open_cell_menu(tree, tree.visualItemRect(item).center())
    next(action for action in matrix.cell_menu.actions() if action.text() == 'Clear technique color').trigger()
    matrix.cell_menu.close()


def main():
    log(f'Input file: {DATA / "latest.json"}')
    log(f'Output file: {REPORT}')
    for path in PREVIEWS.values():
        log(f'Output file: {path}')
    pointers = {p: p.read_bytes() for p in (DATA / 'latest.json', DATA / 'active.json') if p.exists()}
    log('[Clear colors 1/5] Opening cached catalog and native matrix', 0, 5)
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / 'latest.json')
    window.show()
    wait(lambda: window.loaded_ok and not window.loader.isRunning(), 'startup')
    document = window.current_document
    catalog = window.catalog
    lookup = {external_id(obj): key for key, obj in catalog.records.items()}
    key = lookup['T1189']
    window.open_matrix()
    matrix = window.matrix_view
    wait(lambda: not matrix.building, 'matrix')
    matrix.search.setText('T1189')
    item = cell(matrix, key)
    original_style = deepcopy(item.data(0, MATRIX_STYLE))
    original_pixels = painted_row(window, item)
    check(original_pixels.save(str(PREVIEWS['original'])), 'original row preview saved')
    window.select_matrix_ttp(key, True)
    selected_style = deepcopy(item.data(0, MATRIX_STYLE))
    selected_pixels = painted_row(window, item)
    window.select_matrix_ttp(key, False)

    log('[Clear colors 2/5] Reproducing yellow then clear on unchecked technique', 1, 5)
    for color in ('#ff0000', '#ffffff', '#ffff00'):
        window.apply_technique_fields({key}, {'color': color})
        pixels = painted_row(window, item)
        check(item.background(0).color().name() == color and pixels.pixelColor(pixels.width() - 5, 5).name() == color,
              f'{color}: real painted background follows changed color')
    check(pixels.save(str(PREVIEWS['yellow'])), 'yellow row preview saved')
    window.select_matrix_ttp(key, False)
    clear_context(matrix, item)
    cleared_pixels = painted_row(window, item)
    check(cleared_pixels.save(str(PREVIEWS['cleared-unchecked'])), 'cleared unchecked preview saved')
    check(item.data(0, MATRIX_STYLE) == original_style,
          'color-only annotation cleared while unchecked restores original neutral style')
    check(cleared_pixels == original_pixels, 'unchecked clear restores exact original row pixels including text and border')
    check(key not in document.selected and not document.navigator_layer['techniques'],
          'unchecked clear removes vacuous color-only row without selecting technique')
    check('Disabled in this layer' not in item.toolTip(0), 'cleared color-only technique has no synthetic disabled tooltip')
    before = document.fingerprint()
    clear_context(matrix, item)
    check(document.fingerprint() == before and painted_row(window, item) == original_pixels,
          'repeated unchecked clear preserves data and painted neutral row')

    log('[Clear colors 3/5] Checked/bulk clear, gradients and meaningful annotations', 2, 5)
    for color in ('#ffff00', '#000000', '#ffffff'):
        window.apply_technique_fields({key}, {'color': color})
        matrix.clear_color_button.click()
        check(document.selected == {key} and item.data(0, MATRIX_STYLE) == selected_style,
              color + ': bulk clear retains checkbox and restores normal selected style')
        check(painted_row(window, item) == selected_pixels, color + ': selected clear restores exact original selected row pixels')
    check(painted_row(window, item).save(str(PREVIEWS['cleared-checked'])), 'cleared checked preview saved')
    window.apply_technique_fields({key}, {'score': 35})
    document.navigator_layer['techniques'][0]['comment'] = 'Retain research note'
    window.refresh_selection()
    score_pixels = painted_row(window, item)
    score_layer = deepcopy(document.navigator_layer)
    window.apply_technique_fields({key}, {'color': '#ffff00'})
    matrix.clear_color_button.click()
    check(document.navigator_layer == score_layer and painted_row(window, item) == score_pixels,
          'clear explicit color restores exact score gradient and keeps comment/score')
    task = lookup['T1053.005']
    document.navigator_layer['techniques'] = [
        {'techniqueID': 'T1053.005', 'color': '#ffff00'},
        {'techniqueID': 'T1053.005', 'tactic': 'execution', 'color': '#ffffff'},
        {'techniqueID': 'T1053.005', 'tactic': 'persistence', 'enabled': False, 'color': '#ff0000', 'comment': 'Explicitly disabled'}]
    document.navigator_import_selected = {'T1053.005'}
    window.selected = {task}
    window.refresh_selection()
    matrix.search.setText('T1053.005')
    matrix.expand_button.click()
    matrix.clear_color_button.click()
    marker = [{'name': SELECTION_MARKER, 'value': 'true'}]
    check(document.navigator_layer['techniques'] == [
        {'techniqueID': 'T1053.005', 'metadata': marker},
        {'techniqueID': 'T1053.005', 'tactic': 'execution', 'metadata': marker},
        {'techniqueID': 'T1053.005', 'tactic': 'persistence', 'enabled': False,
         'comment': 'Explicitly disabled', 'metadata': marker}],
        'clear preserves inclusion markers and genuine imported disabled annotations while removing every color')
    check(cell(matrix, task, 'persistence').background(0).color().name() == '#303436', 'genuine imported disabled scope retains deliberate grey appearance')
    before = document.fingerprint()
    matrix.clear_color_button.click()
    check(document.fingerprint() == before, 'clear on disabled annotation with no color is a no-op')

    log('[Clear colors 4/5] Overlay refresh and original layer export', 3, 5)
    document.navigator_layer['techniques'] = []
    document.navigator_import_selected = set()
    window.selected = {key}
    window.refresh_selection()
    window.apply_technique_fields({key}, {'color': '#ff0000'})
    window.new_document()
    wait(lambda: window.loaded_ok, 'second document')
    window.open_matrix()
    wait(lambda: not matrix.building, 'second matrix')
    second = window.current_document
    window.apply_technique_fields({key}, {'color': '#0000ff'})
    protected = document.fingerprint()
    matrix.show_all_layers.setChecked(True)
    check(cell(matrix, key).background(0).color().name() == '#800080', 'initial red/blue overlap displayed')
    window.select_matrix_ttp(key, False)
    window.apply_technique_fields({key}, {'color': ''}, include=False)
    check(cell(matrix, key).background(0).color().name() == '#ff0000', 'cleared unchecked source leaves only other layer red without residual blend')
    check(document.fingerprint() == protected and not second.selected and not second.navigator_layer['techniques'],
          'overlay clear changes only active source and preserves other document')
    matrix.show_all_layers.setChecked(False)
    check(not cell(matrix, key).data(0, MATRIX_STYLE)['background'], 'turning overlay off restores neutral cleared source')
    projection = document_layer(second)
    check(not projection['techniques'], 'export projection contains no synthetic cleared/disabled technique')
    check(all(path.read_bytes() == data for path, data in pointers.items()), 'dataset pointers unchanged')
    window.confirm_studio_changes = lambda *_: "discard"
    window.close()
    log('[Clear colors 5/5] Publishing successful report', 4, 5)
    REPORT.write_text(json.dumps({'status': 'PASS', 'checks': checks,
                                 'previews': {name: str(path) for name, path in PREVIEWS.items()}}, indent=2) + '\n', encoding='utf-8')
    log(f'[Clear colors] PASS: {len(checks)} checks', 5, 5)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
