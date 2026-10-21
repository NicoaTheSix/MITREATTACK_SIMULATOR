"""Verify independent states, scope selection and atomic native batch editing. Flow: README.md."""
from copy import deepcopy
from pathlib import Path
import csv
import json
import time
from unittest.mock import patch
from PySide6 import QtCore, QtWidgets

from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from attack_matrix import MATRIX_ID, MATRIX_SLUG, MATRIX_STYLE
from audit_advanced_navigator import fixture, catalog as fixture_catalog
from batch_dialogs import BatchEditDialog
from layer_analysis import calculate_layer
from main import MainWindow, configure_application
from navigator_dialogs import AnnotationDialog
from navigator_integration import (document_layer, export_layer, imported_document, update_annotation, SELECTION_MARKER)
from navigator_visuals import LayerAppearance, OverlayAppearance
from ttp_documents import TTPDocument, export_document_json, export_document_csv, technique_states
from ttp_operations import batch_patch, apply_selection, annotated_keys

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts' / 'batch-operations'
CHECKS = []


def log(message, current=0, total=0):
    print(message + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, label):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def wait(condition, label):
    until = time.monotonic() + 90
    while not condition():
        if time.monotonic() > until:
            raise TimeoutError(label)
        QtWidgets.QApplication.processEvents()
        time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def expect_error(task, label):
    try:
        task()
    except (ValueError, TypeError):
        check(True, label)
    else:
        raise AssertionError(label)


def layer_cell(document, key, slug='execution'):
    return LayerAppearance(document_layer(document), document.catalog).cell(external_id(document.catalog.records[key]), slug)


def run():
    log(f'Input pointer: {(DATA / "latest.json").resolve()}')
    log(f'Output directory: {OUT.resolve()}')
    OUT.mkdir(parents=True, exist_ok=True)
    pointers = {p: p.read_bytes() for p in (DATA / 'active.json', DATA / 'latest.json') if p.exists()}
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    window = MainWindow(DATA, settings_path=OUT / 'settings.ini')
    window.resize(1600, 1050)
    window.show()
    wait(lambda: window.loaded_ok, 'startup')
    window.open_matrix()
    matrix = window.matrix_view
    wait(lambda: not matrix.building, 'matrix')
    official = window.catalog
    ids = {external_id(obj): key for key, obj in official.records.items()}
    task, parent, shell = ids['T1053.005'], ids['T1053'], ids['T1059']
    document = window.current_document

    log('[Batch Audit 1/6] Inclusion and enabled state independence')
    window.select_matrix_ttp(task, True)
    initial = document_layer(document)
    check(not next(row for row in initial['techniques'] if row['techniqueID'] == 'T1053.005').get('color'), 'inclusion does not synthesize a color')
    check(layer_cell(document, task)['enabled'], 'new techniques default to enabled')
    update_annotation(document, task, '', 'Research note', 5, '#eecc44')
    window.set_technique_states({task}, False)
    check(task in document.selected and not layer_cell(document, task)['enabled'], 'disable retains selected TTP')
    preserved = deepcopy(document.navigator_layer)
    window.select_matrix_ttp(task, False)
    check(document.navigator_layer == preserved and not document.selected, 'deselection preserves all annotations and disabled flags')
    window.set_technique_states({task}, True)
    check(not document.selected and layer_cell(document, task)['background'] == '#eecc44', 'unchecked enable restores original color without inclusion')
    window.select_matrix_ttp(task, True)
    window.set_technique_states({task}, False, 'execution')
    check(not layer_cell(document, task, 'execution')['enabled'] and layer_cell(document, task, 'persistence')['enabled'], 'tactic-specific disable preserves other tactic state')
    scoped = next(row for row in document.navigator_layer['techniques'] if row.get('tactic') == 'execution')
    check(scoped['comment'] == 'Research note' and scoped['score'] == 5 and scoped['color'] == '#eecc44', 'new tactic state row inherits untouched global annotations')
    check(len({row['enabled'] for row in technique_states(document, task)[1]}) == 2, 'mixed tactic states exposed in state projection')
    window.set_technique_states({task}, False)
    check(all(not row['enabled'] for row in technique_states(document, task)[1]), 'whole-technique disable updates existing scope overrides')
    matrix.show_colors.setChecked(False)
    check(all(item.data(0, MATRIX_STYLE)['foreground'] == '#999999' for item in matrix.items_by_id[task]), 'hiding colors retains disabled foreground cue')
    matrix.show_colors.setChecked(True)
    matrix.search.setText('T1053.005')
    matrix.set_expanded(True)
    matrix.grab().save(str(OUT / 'disabled-included.png'))
    matrix.search.clear()
    before = deepcopy(document.navigator_layer)
    window.select_matrix_ttp(task, False)
    window.select_matrix_ttp(task, True)
    check(document.navigator_layer == before, 'checkbox round trip does not rewrite states')
    window.disable_selected_action.trigger()
    check(task in document.selected and not layer_cell(document, task)['enabled'], 'native disable action preserves inclusion')
    for name, export in [('state.studio.json', export_document_json), ('state.csv', export_document_csv), ('state.navigator.json', export_layer)]:
        export(document, OUT / name, log)
    studio = json.loads((OUT / 'state.studio.json').read_text(encoding='utf-8'))
    check(studio['selected_ttps'][0]['enabled'] is False and all(not row['enabled'] for row in studio['selected_ttps'][0]['tactic_enabled']), 'Studio JSON includes disabled selected row and all tactic states')
    with (OUT / 'state.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(csv.DictReader(stream))
    check(row['enabled'] == 'false' and all(not value['enabled'] for value in json.loads(row['tactic_enabled'])), 'CSV includes actual independent global/tactic flags')
    exported = json.loads((OUT / 'state.navigator.json').read_text(encoding='utf-8'))
    restored = imported_document(exported, official)
    check(restored.selected == {task} and not layer_cell(restored, task)['enabled'], 'Navigator round trip restores disabled selected TTP')
    imported_all = imported_document(exported, official, 'all')
    check(not layer_cell(imported_all, task)['enabled'], 'all-row import never enables disabled annotations')
    standard = deepcopy(exported)
    for entry in standard['techniques']:
        entry['metadata'] = []
    check(not imported_document(standard, official).selected, 'external layer without inclusion marker still uses enabled-row import policy')

    log('[Batch Audit 2/6] Atomic patches, clearing and scope inheritance')
    custom = fixture_catalog(fixture('19.3', True))
    keys = {external_id(obj): key for key, obj in custom.records.items()}
    a, child, b = keys['T1000'], keys['T1000.001'], keys['T1001']
    draft = TTPDocument('Atomic batch', custom, selected={a, child, b})
    update_annotation(draft, a, '', 'Original', 13, '#aabbcc', [{'label': 'Case', 'url': 'https://example.org/case'}],
                      [{'name': 'Owner', 'value': 'Team'}, {'name': SELECTION_MARKER, 'value': 'true'}])
    draft.navigator_layer['techniques'][0].update(enabled=False, x_lab={'keep': 7})
    saved = deepcopy(draft.navigator_layer['techniques'][0])
    batch_patch(draft, {a, child}, {'comment': 'Batch comment'}, notify=log)
    row = next(row for row in draft.navigator_layer['techniques'] if row['techniqueID'] == 'T1000')
    check(all(row[field] == saved[field] for field in ('score', 'color', 'links', 'metadata', 'enabled', 'x_lab')), 'editing comments keeps every unrequested field and extension')
    previous = draft.fingerprint()
    expect_error(lambda: batch_patch(draft, {a, child}, {'comment': 'must not commit', 'score': float('nan')}), 'invalid patch rejected')
    check(draft.fingerprint() == previous, 'invalid multi-target patch is atomic')
    expect_error(lambda: batch_patch(draft, {a, 'missing'}, {'enabled': False}), 'invalid target set rejected atomically')
    expect_error(lambda: batch_patch(draft, {a}, {'links': [{'label': 'Invalid', 'url': 'javascript:bad'}]}), 'batch core rejects unsafe replacement URLs')
    batch_patch(draft, {a, child}, {'score': 0}, 'execution', log)
    check(layer_cell(draft, a)['score'] == 0 and layer_cell(draft, child, 'initial-access')['score'] is None, 'tactic edit affects only mapped targets; zero score preserved')
    row = next(row for row in draft.navigator_layer['techniques'] if row.get('tactic') == 'execution')
    check(row['x_lab'] == {'keep': 7} and row['links'] == saved['links'] and row['enabled'] is False, 'new scoped batch row preserves inherited extension, links and disabled state')
    original_states = [entry['enabled'] for entry in technique_states(draft, a)[1]]
    batch_patch(draft, {a}, {'enabled': 'toggle'})
    check([entry['enabled'] for entry in technique_states(draft, a)[1]] == [not state for state in original_states], 'toggle inverts each mapped scope independently')
    batch_patch(draft, {a}, {'enabled': 'toggle'})
    selection = set(draft.selected)
    batch_patch(draft, {a, child}, {'links': [{'label': 'Replaced', 'url': 'https://example.org/new'}, {'divider': True}],
                                  'metadata': [{'name': 'Owner', 'value': 'Updated'}, {'divider': True}]}, notify=log)
    check(all(row['links'][1] == {'divider': True} for row in draft.navigator_layer['techniques'] if row['techniqueID'] == 'T1000'), 'batch list replacement preserves dividers across scopes')
    check(any(entry.get('name') == SELECTION_MARKER for entry in draft.navigator_layer['techniques'][0]['metadata']), 'reserved inclusion metadata survives batch list replacement')
    batch_patch(draft, {a, child}, dict.fromkeys(('score', 'color', 'comment', 'links', 'metadata', 'enabled')), notify=log)
    check(draft.selected == selection and all(layer_cell(draft, key, 'initial-access' if key == child else 'execution')['enabled'] for key in (a, child)), 'clear annotations retains selection and restores enabled state')
    check(draft.navigator_layer['techniques'][0]['x_lab'] == {'keep': 7}, 'clear preserves unknown extension fields')
    check(not annotated_keys(draft, {a, child}), 'reserved metadata and extension-only rows do not count as user annotations')
    inherited = TTPDocument('Inherited', custom, selected={a})
    update_annotation(inherited, a, '', 'Keep comment', 9, '#abcdef')
    batch_patch(inherited, {a}, {'enabled': False})
    batch_patch(inherited, {a}, {'color': None, 'enabled': None}, 'execution')
    check(layer_cell(inherited, a)['enabled'] and layer_cell(inherited, a)['comment'] == 'Keep comment'
          and next(row for row in inherited.navigator_layer['techniques'] if row.get('tactic') == 'execution').get('color') is None,
          'tactic clear overrides inherited color/state while preserving other global fields')
    empty = TTPDocument('Empty', custom)
    previous = empty.fingerprint()
    check(not batch_patch(empty, {b}, {'color': None, 'score': None})['changed'] and empty.fingerprint() == previous, 'clear absent fields leaves empty document unchanged')

    log('[Batch Audit 3/6] Native scope selection, predicates and all layouts')
    document.navigator_layer = {}
    window.clear_selection()
    matrix.platform.setCurrentText('Windows')
    wait(lambda: not matrix.building, 'Windows scope')
    matrix.search.setText('T1053.005')
    check(matrix.scope_keys('search') == {task}, 'search scope selects direct ID matches without ancestor headings')
    window.select_ttp_batch('replace', 'search')
    check(window.selected == {task}, 'native search replace selects exact technique')
    window.select_ttp_batch('invert', 'search')
    check(not window.selected, 'invert toggles membership only inside scope')
    window.select_ttp_batch('add', 'search')
    window.select_ttp_batch('remove', 'search')
    check(not window.selected, 'scope add/remove compose correctly')
    for mode in ('Flat', 'Side', 'Mini'):
        matrix.view_layout.setCurrentText(mode)
        wait(lambda: not matrix.building, mode)
        matrix.search.clear()
        matrix.set_expanded(False)
        check(task not in matrix.scope_keys('visible'), mode + ' visible scope excludes collapsed child')
        matrix.set_expanded(True)
        check(task in matrix.scope_keys('visible'), mode + ' visible scope includes expanded child')
        matrix.search.setText('T1053.005')
        check(matrix.scope_keys('search') == {task}, mode + ' search scope excludes context parent')
        matrix.grab().save(str(OUT / (mode.lower() + '.png')))
    window.set_technique_states({task}, False)
    document.navigator_layer['hideDisabled'] = True
    window.refresh_selection()
    check(task in matrix.scope_keys('platform') and task not in matrix.scope_keys('search'), 'platform scope includes hidden disabled row; search scope excludes it')
    check(task not in matrix.scope_keys('visible'), 'visible scope excludes hidden disabled row')
    document.navigator_layer['hideDisabled'] = False
    update_annotation(document, parent, '', '', 0, '')
    document.navigator_layer['techniques'].append({'techniqueID': 'T1059', 'metadata': [{'name': SELECTION_MARKER, 'value': 'true'}]})
    window.refresh_selection()
    matrix.search.clear()
    window.select_ttp_batch('annotated', 'platform', 'execution')
    check(task in window.selected and parent in window.selected and shell not in window.selected, 'annotated selection includes disabled and zero-score rows but excludes reserved markers')
    before = deepcopy(document.navigator_layer)
    window.select_ttp_batch('unannotated', 'platform', 'execution')
    check(task not in window.selected and parent not in window.selected and shell in window.selected, 'unannotated selection replaces with correct complementary subset')
    check(document.navigator_layer == before, 'all batch selection actions preserve state and raw annotations')
    matrix.selection_scope.setCurrentIndex(matrix.selection_scope.findData('search'))
    matrix.search.setText('T1053.005')
    matrix.bulk_select_button.menu().actions()[1].trigger()
    check(window.selected == {task}, 'native Select menu invokes actual scoped operation')
    check(apply_selection({a}, {b}, 'invert') == {a, b}, 'invert preserves outside selections')

    log('[Batch Audit 4/6] Native batch drafts, cancellation and single-editor states')
    snapshot = document.fingerprint()
    dialog = BatchEditDialog(document, {task}, window)
    check(all(combo.currentIndex() == 0 for combo in dialog.modes.values()), 'batch editor defaults every field to Keep')
    dialog.modes['score'].setCurrentIndex(1)
    dialog.values['score'].setText('nan')
    dialog.save()
    check(dialog.error.text() and not dialog.worker and document.fingerprint() == snapshot, 'native invalid score preserves original and avoids worker commit')
    dialog.reject()
    cancelled = BatchEditDialog(document, {task}, window)
    cancelled.modes['comment'].setCurrentIndex(1)
    cancelled.values['comment'].setPlainText('Cancelled draft')
    def interruptible(doc, keys, patch_values, tactic=None, notify=log):
        for number in range(20):
            time.sleep(.01)
            notify('[Cancellation fixture] Draft progress', number, 20)
        return batch_patch(doc, keys, patch_values, tactic, notify)
    with patch('batch_dialogs.batch_patch', interruptible):
        cancelled.save()
        cancelled.reject()
        wait(lambda: cancelled.worker and not cancelled.worker.isRunning(), 'cancelled worker')
    check(document.fingerprint() == snapshot and cancelled.result_layer is None, 'cancel during background editing preserves source document')
    def apply_native():
        dialog = window.integration_dialog
        dialog.modes['comment'].setCurrentIndex(1)
        dialog.values['comment'].setPlainText('Native batch note\nSecond line')
        dialog.modes['score'].setCurrentIndex(1)
        dialog.values['score'].setText('0')
        dialog.modes['links'].setCurrentIndex(1)
        dialog.values['links'].add({'label': 'Case evidence', 'url': 'https://example.org/evidence'})
        dialog.values['links'].add({'divider': True})
        dialog.modes['metadata'].setCurrentIndex(1)
        dialog.values['metadata'].add({'name': 'Analyst', 'value': 'Blue team'})
        dialog.values['metadata'].add({'divider': True})
        dialog.grab().save(str(OUT / 'batch-editor.png'))
        dialog.save()
    QtCore.QTimer.singleShot(0, apply_native)
    window.edit_ttp_batch()
    check(window.selected == {task} and not layer_cell(document, task)['enabled'] and layer_cell(document, task)['score'] == 0, 'native batch applies score/comment while preserving disabled state and selection')
    check(layer_cell(document, task)['comment'] == 'Native batch note\nSecond line', 'native multiline comments retained')
    check(layer_cell(document, task)['links'][1] == {'divider': True}
          and layer_cell(document, task)['metadata'][0]['value'] == 'Blue team', 'native Links/Metadata replacement supports dividers')
    snapshot = document.fingerprint()
    invalid_links = BatchEditDialog(document, {task}, window)
    invalid_links.modes['links'].setCurrentIndex(1)
    invalid_links.values['links'].add({})
    invalid_links.values['links'].table.item(0, 0).setText('Invalid')
    invalid_links.values['links'].table.item(0, 1).setText('javascript:bad')
    invalid_links.save()
    check(invalid_links.error.text() and document.fingerprint() == snapshot, 'native batch invalid URL does not mutate source')
    invalid_links.reject()
    snapshot = document.fingerprint()
    QtCore.QTimer.singleShot(0, lambda: window.integration_dialog.reject())
    window.edit_ttp_batch(clear=True)
    check(document.fingerprint() == snapshot, 'cancelled clear draft preserves complete document')
    QtCore.QTimer.singleShot(0, lambda: window.integration_dialog.save())
    window.edit_ttp_batch(clear=True)
    check(window.selected == {task} and layer_cell(document, task)['enabled'] and layer_cell(document, task)['score'] is None, 'native clear resets annotations/state without deselection')
    editor = AnnotationDialog(document, task, window)
    editor.enabled.setChecked(False)
    editor.include.setChecked(True)
    editor.save()
    check(editor.result() == QtWidgets.QDialog.DialogCode.Accepted, 'single editor accepts included but disabled TTP')
    document.navigator_layer = editor.result_layer
    window.refresh_selection()
    check(not layer_cell(document, task)['enabled'] and 'Disabled' in window.selection_list.item(0).text(), 'selection page labels independent disabled state')

    log('[Batch Audit 5/6] Domain, version, duplication and analytic isolation')
    for domain in ('mobile-attack', 'ics-attack'):
        window.change_document_domain(window.active_document_index, domain)
        wait(lambda: window.loaded_ok, domain)
        key = next(iter(window.catalog.records))
        window.select_matrix_ttp(key, True)
        window.set_technique_states({key}, False)
        check(key in window.selected and all(not row['enabled'] for row in technique_states(window.current_document, key)[1]), domain + ' independent state supported')
        export_document_json(window.current_document, OUT / (domain + '.json'), log)
        export_document_csv(window.current_document, OUT / (domain + '.csv'), log)
        restored = imported_document(document_layer(window.current_document), window.catalog)
        check(restored.selected == {key} and not technique_states(restored, key)[0], domain + ' disabled selected export round trip')
    window.change_document_domain(window.active_document_index, 'enterprise-attack')
    wait(lambda: window.loaded_ok, 'Enterprise archive')
    check(window.selected == {task} and not layer_cell(document, task)['enabled'], 'domain archive restores original independent state')
    protected = deepcopy(document.navigator_layer)
    window.duplicate_navigator_layer()
    wait(lambda: window.loaded_ok, 'duplicate')
    duplicate = window.current_document
    window.set_technique_states({task}, True)
    check(duplicate is not document and document.navigator_layer == protected and layer_cell(duplicate, task)['enabled'], 'duplicate enabled edits do not mutate source state')
    old = load_catalog(DATA, log, snapshot_pointer(DATA, '11.3'))
    version_doc = TTPDocument('State archive', official, selected={task}, navigator_layer=deepcopy(document.navigator_layer))
    version_doc.set_catalog(old)
    version_doc.set_catalog(official)
    check(version_doc.navigator_layer == document.navigator_layer, 'version archive restores exact state annotations')
    disabled = TTPDocument('Disabled source', official, selected={task})
    update_annotation(disabled, task, '', 'Retain', 10, '#ff0000')
    batch_patch(disabled, {task}, {'enabled': False})
    enabled = TTPDocument('Enabled source', official)
    update_annotation(enabled, task, '', 'Unchecked but enabled', 2, '#0000ff')
    overlay = OverlayAppearance([('disabled', document_layer(disabled)), ('enabled', document_layer(enabled))], document_layer(disabled), official)
    check(overlay.cell('T1053.005', 'execution')['background'] == '#0000ff', 'unchecked enabled source contributes; disabled source does not')
    calculated = calculate_layer([disabled], 'a', 'Disabled score', notify=log)
    check(not calculated.selected and calculated.navigator_layer['techniques'][0]['enabled'] is False, 'formula excludes disabled score without modifying source inclusion')
    check(disabled.selected == {task}, 'analytic operations preserve source inclusion')
    check(all(path.read_bytes() == content for path, content in pointers.items()), 'all operations preserve official snapshot pointers')

    log('[Batch Audit 6/6] Publishing report')
    report = OUT / 'audit.json'
    log(f'Output file: {report.resolve()}')
    report.write_text(json.dumps({'passed': True, 'assertions': len(CHECKS), 'checks': CHECKS}, indent=2), encoding='utf-8')
    log(f'Batch operations audit passed: {len(CHECKS)} assertions', 6, 6)
    window.closing = True
    window.confirm_studio_changes = lambda *_: "discard"
    window.close()


if __name__ == '__main__':
    run()
