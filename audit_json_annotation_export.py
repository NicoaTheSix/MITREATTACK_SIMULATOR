"""NAV-014 export projection and native dialog audit. Workflow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
from unittest.mock import patch
from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id
from audit_source_selection import fixture
from audit_visibility_presets import wait
from custom_sources import load_custom
from json_annotation_export import annotation_export_plan, matrix_visibility, modified_annotation
from json_export_dialog import JSONAnnotationExportDialog
from layer_analysis import snapshot_document
from main import MainWindow, configure_application
from navigator_integration import document_layer, imported_document, export_layer, export_layers, SELECTION_MARKER
from studio_files import save_studio
from ttp_documents import TTPDocument
from ttp_selection import selected_cells

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts' / 'json-annotation-export'
CHECKS = []


def log(text, current=0, total=0):
    print(text + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, text):
    if not value:
        raise AssertionError(text)
    CHECKS.append(text)


def state(doc):
    return doc.name, doc.content_token(), doc.saved_fingerprint, doc.dirty


def example(catalog):
    ids = {external_id(obj): key for key, obj in catalog.records.items()}
    doc = TTPDocument('JSON view example', catalog, selected={ids['T1000'], ids['T1000.001']},
        navigator_layer={'name': 'JSON view example', 'domain': catalog.domain,
        'filters': {'platforms': ['Windows']}, 'layout': {'layout': 'flat', 'expandedSubtechniques': 'none'},
        'metadata': [{'name': 'Layer owner', 'value': 'Keep layer metadata'}],
        'techniques': [
            {'techniqueID': 'T1000', 'comment': 'Global parent', 'color': '#112233', 'score': 0,
             'links': [{'label': 'Reference', 'url': 'https://example.org/'}],
             'metadata': [{'name': 'Owner', 'value': 'Blue'}], 'x_fixture': 'keep extension'},
            {'techniqueID': 'T1000', 'tactic': 'initial-access', 'comment': 'Scoped parent'},
            {'techniqueID': 'T1000.001', 'comment': 'Collapsed child', 'enabled': False},
            {'techniqueID': 'T1000.002', 'color': '#445566'},
            {'techniqueID': 'T1001', 'showSubtechniques': True},
            {'techniqueID': 'T9999', 'comment': 'Unknown imported technique'}]})
    doc.selection_scopes = {ids['T1000']: ['execution']}
    return doc


def main():
    log('Input file: ' + str(Path(__file__).resolve()))
    log('Input directory: ' + str(ROOT / 'data' / 'attack'))
    log('Output directory: ' + str(OUT))
    for name in ('fixture.json', 'full.json', 'visible.json', 'legacy.json', 'all.json', 'settings.ini',
                 'state.studio.json', 'review.png', 'review-zh.png', 'audit.json'):
        log('Output file: ' + str(OUT / name))
    log('[JSON Audit 1/7] Preparing isolated three-domain fixtures', 0, 7)
    OUT.mkdir(parents=True, exist_ok=True)
    source = OUT / 'fixture.json'
    source.write_text(json.dumps(fixture()), encoding='utf-8')
    catalog = load_custom(OUT / 'cache', str(source), '19.2', log)['catalog']
    for row, expected in [({'score': 0}, True), ({'enabled': False}, True), ({'showSubtechniques': True}, True),
            ({'metadata': [{'divider': True}]}, True), ({'links': [{'divider': True}]}, True),
            ({'enabled': True, 'color': '', 'comment': '', 'showSubtechniques': False}, False),
            ({'metadata': [{'name': SELECTION_MARKER, 'value': 'true'}]}, False), ({'x_custom': 0}, True)]:
        check(modified_annotation({'techniqueID': 'T1000', **row}) == expected, 'modified classification: ' + repr(row))
    log('[JSON Audit 2/7] Global/scoped annotations, inclusion and all domains', 1, 7)
    for domain in ('enterprise-attack', 'mobile-attack', 'ics-attack'):
        doc = example(catalog.for_domain(domain))
        original = state(doc)
        plan = annotation_export_plan(doc, notify=log)
        check(plan.payload() == document_layer(doc), domain + ' complete default equals the lossless layer')
        visible = plan.payload(True)
        check(state(doc) == original, domain + ' preview and projection preserve source document')
        check(any(r['techniqueID'] == 'T9999' for r in plan.hidden_modified), domain + ' unknown imported row reported')
        check(not any(r['techniqueID'] == 'T9999' for r in visible['techniques']), domain + ' unknown row omitted only explicitly')
        check(all(r.get('tactic') for r in visible['techniques']), domain + ' no global annotation leaks to hidden tactics')
        child = next(r for r in visible['techniques'] if r['techniqueID'] == 'T1000.001')
        check(set(child) == {'techniqueID', 'tactic', 'metadata'}, domain + ' hidden selected child retains inclusion only')
        restored = imported_document(visible, doc.catalog)
        check(selected_cells(restored) == selected_cells(doc), domain + ' partial and hidden selections survive reduced export')
        check(visible['metadata'] == plan.layer['metadata'], domain + ' layer-level metadata remains complete')
        exact = annotation_export_plan(doc, {'visible_cells': {('T1000', 'execution')}})
        check(len(exact.hidden_modified) == 5 and exact.hidden_techniques == 5, domain + ' hidden counts use effective scope not global row count')
        rows = exact.payload(True)['techniques']
        parent = next(r for r in rows if r['techniqueID'] == 'T1000')
        check(parent['tactic'] == 'execution' and parent['comment'] == 'Global parent' and parent['score'] == 0,
              domain + ' visible inherited annotation retains precision and zero score')
        only = annotation_export_plan(doc, {'visible_cells': set()}).payload(True)
        check(all(not modified_annotation(r) for r in only['techniques']), domain + ' empty projection contains inclusion markers only')
        check(selected_cells(imported_document(only, doc.catalog)) == selected_cells(doc), domain + ' no visible cells still retains exact inclusion')
        duplicate = snapshot_document(doc)
        duplicate.navigator_layer['techniques'].append({'techniqueID': 'T1000', 'tactic': 'execution', 'comment': 'Last scoped value'})
        reduced = annotation_export_plan(duplicate, {'visible_cells': {('T1000', 'execution')}}).payload(True)
        check(next(r for r in reduced['techniques'] if r['techniqueID'] == 'T1000')['comment'] == 'Last scoped value', domain + ' scoped row wins over global row')
    doc = example(catalog)
    linux = annotation_export_plan(doc, {'platform': ['Linux']})
    check(('T1001', 'execution') in linux.visible and ('T1000.001', 'execution') not in linux.visible,
          'Linux platform excludes Windows-only child and includes Linux-only technique')
    windows = annotation_export_plan(doc, {'platform': ['Windows']})
    union = annotation_export_plan(doc, {'platform': ['Linux', 'Windows']})
    check(union.visible == linux.visible | windows.visible, 'multiple platforms use their union')
    check(not annotation_export_plan(doc, {'platform': []}).visible, 'empty platform filter yields no visible annotations')
    unknown_platform = snapshot_document(doc)
    unknown_platform.navigator_layer['filters']['platforms'] = ['Windows', 'Unknown imported platform']
    check(annotation_export_plan(unknown_platform).visible == windows.visible,
          'unknown imported platform names are ignored only for visibility projection')
    check(annotation_export_plan(unknown_platform).payload()['filters']['platforms'] == ['Windows', 'Unknown imported platform'],
          'complete default preserves unknown imported platform filters')
    disabled = snapshot_document(doc)
    disabled.navigator_layer['layout']['expandedSubtechniques'] = 'all'
    disabled.navigator_layer['hideDisabled'] = True
    check(('T1000.001', 'execution') not in annotation_export_plan(disabled).visible,
          'Hide disabled hides expanded disabled child')
    disabled.navigator_layer['hideDisabled'] = False
    check(('T1000.001', 'execution') in annotation_export_plan(disabled).visible,
          'disabled annotation remains visible when Hide disabled is off')
    structural = snapshot_document(doc)
    records = deepcopy(catalog.records)
    root_key = next(key for key, obj in records.items() if external_id(obj) == 'T1000')
    records[root_key]['kill_chain_phases'] = [p for p in records[root_key]['kill_chain_phases'] if p['phase_name'] == 'execution']
    structural.catalog = replace(catalog, records=records)
    structural.navigator_layer['techniques'] = [r for r in structural.navigator_layer['techniques']
        if not (r['techniqueID'] == 'T1000' and r.get('tactic') == 'initial-access')]
    heading = annotation_export_plan(structural, {'visible_cells': {('T1000', 'initial-access')}})
    heading_row = next(r for r in heading.payload(True)['techniques'] if r['techniqueID'] == 'T1000' and r['tactic'] == 'initial-access')
    check(heading_row['comment'] == 'Global parent' and heading_row['showSubtechniques'] is False,
          'structural family heading retains visible inherited annotation with an explicit display scope')
    check(selected_cells(imported_document(heading.payload(True), structural.catalog)) == selected_cells(structural),
          'structural heading is never made selectable in an unmapped parent tactic')
    log('[JSON Audit 3/7] Atomic publication, defaults and mixed bundles', 2, 7)
    before = state(doc)
    export_layer(doc, OUT / 'full.json', log)
    check(json.loads((OUT / 'full.json').read_text(encoding='utf-8')) == document_layer(doc), 'full disk export retains exact annotations')
    check(state(doc) == before, 'single export preserves name/content/dirty/save baseline')
    export_layer(doc, OUT / 'visible.json', log, visible_only=True, visibility={'visible_cells': {('T1000', 'execution')}})
    check(state(doc) == before, 'reduced export preserves original editable source')
    legacy_clean = snapshot_document(doc)
    legacy_clean.exported_fingerprint = legacy_clean.fingerprint()
    check(not legacy_clean.dirty, 'legacy fingerprint-only clean document fixture')
    export_layer(legacy_clean, OUT / 'legacy.json', log, visible_only=True)
    check(not legacy_clean.dirty and legacy_clean.exported_fingerprint == legacy_clean.fingerprint(),
          'exchange export preserves legacy clean baseline as well as Studio save baselines')
    docs = [doc, example(catalog.for_domain('mobile-attack')), example(catalog.for_domain('ics-attack'))]
    before_all = [(state(d), d.export_path, d.export_format) for d in docs]
    export_layers(docs, OUT / 'all.json', log, visible_only=True,
                  visibility_contexts=[{'visible_cells': set()}, None, None])
    bundle = json.loads((OUT / 'all.json').read_text(encoding='utf-8'))
    check(len(bundle) == 3 and bundle[1]['domain'] == 'mobile-attack', 'mixed-domain bundle uses independent catalogs')
    check(all(not modified_annotation(row) for row in bundle[0]['techniques']), 'active empty projection does not filter other bundle layers')
    check(any(modified_annotation(row) for row in bundle[1]['techniques']), 'inactive layer uses its saved visibility')
    check([(state(d), d.export_path, d.export_format) for d in docs] == before_all, 'bundle preserves every source and export bookkeeping')
    protected = (OUT / 'visible.json').read_bytes()
    with patch.object(Path, 'replace', side_effect=PermissionError('audit blocked publication')):
        try:
            export_layer(doc, OUT / 'visible.json', log, visible_only=True)
        except PermissionError:
            pass
        else:
            raise AssertionError('atomic failure expected')
    check((OUT / 'visible.json').read_bytes() == protected and not list(OUT.glob('*.tmp')), 'failed publication preserves output and cleans temporary file')
    log('[JSON Audit 4/7] Actual Flat/Side/Mini matrix visibility', 3, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    QtCore.QSettings(str(OUT / 'settings.ini'), QtCore.QSettings.Format.IniFormat).clear()
    w = MainWindow(ROOT / 'data' / 'attack', ROOT / 'data' / 'attack' / 'latest.json', settings_path=OUT / 'settings.ini')
    w.resize(1800, 1100)
    w.show()
    try:
        wait(lambda: w.loaded_ok and not w.loader.isRunning())
        w.install_imported_document(doc)
        wait(lambda: w.loaded_ok and w.current_document is doc)
        w.open_matrix()
        m = w.matrix_view
        wait(lambda: not m.building)
        for mode in ('Flat', 'Side', 'Mini'):
            m.view_layout.setCurrentText(mode)
            wait(lambda: not m.building)
            for expanded in ('none', 'all'):
                m.choose_expansion(expanded)
                wait(lambda: not m.building)
                for query in ('', 'child-only description needle', 'no matching technique'):
                    doc.search_fields = ['name', 'id', 'description']
                    m.search_fields = list(doc.search_fields)
                    m.search.setText(query)
                    m.filter_items()
                    captured = matrix_visibility(m)
                    projected = annotation_export_plan(doc, {'platform': m.platform_scope(), 'query': query}).visible
                    check(captured == projected, mode + '/' + expanded + '/' + query + ' saved projection equals native logical visibility')
                    frozen = state(doc)
                    plan = annotation_export_plan(doc, w.json_visibility_contexts([doc])[0])
                    check(plan.visible == captured and state(doc) == frozen, mode + ' active capture uses actual cells without edits')
            m.search.clear()
        m.view_layout.setCurrentText('Flat')
        wait(lambda: not m.building)
        for hidden in (True, False):
            doc.navigator_layer['hideDisabled'] = hidden
            w.refresh_selection()
            wait(lambda: not m.building)
            m.choose_expansion('all')
            native = matrix_visibility(m)
            check(annotation_export_plan(doc).visible == native, 'native Hide disabled=' + str(hidden) + ' matches export projection')
        m.show_colors.setChecked(False)
        base = matrix_visibility(m)
        m.source_preview_cells = frozenset({(next(iter(doc.selected)), 'execution')})
        check(matrix_visibility(m) == base, 'hidden fill colors and source preview do not change annotation visibility')
        m.clear_source_preview()
        m.hide()
        check(matrix_visibility(m) == base, 'hidden matrix tab does not change logical annotation visibility')
        m.show()
        inactive = example(catalog.for_domain('mobile-attack'))
        inactive_index = w.append_document(catalog)
        w.documents[inactive_index] = inactive
        w.document_tabs.setTabData(inactive_index, inactive.document_id)
        w.update_document_labels()
        m.search.setText('no matching technique')
        m.filter_items()
        contexts = w.json_visibility_contexts([doc, inactive])
        check(contexts[0]['visible_cells'] == frozenset() and contexts[1] is None,
              'active search is frozen but never applied to an inactive layer')
        m.search.clear()
        log('[JSON Audit 5/7] Native review, cancellation and explicit reduced export', 4, 7)
        plan = annotation_export_plan(doc, {'visible_cells': {('T1000', 'execution')}})
        dialog = JSONAnnotationExportDialog([plan], OUT / 'visible.json', w)
        dialog.show()
        app.processEvents()
        check(not dialog.visible_only.isChecked(), 'native review defaults to complete retention')
        check(str(len(plan.hidden_modified)) in dialog.warning.text(), 'native warning shows hidden annotation count')
        check('T9999' in dialog.details.toPlainText(), 'review lists unknown hidden annotations')
        dialog.visible_only.setChecked(True)
        check('omitted' in dialog.warning.text(), 'explicit visible-only choice updates warning')
        check(dialog.grab().save(str(OUT / 'review.png')), 'review screenshot saved')
        dialog.reject()
        dialog.deleteLater()
        frozen = state(doc)
        protected = (OUT / 'visible.json').read_bytes()
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(OUT / 'visible.json'), 'Navigator Layer files (*.json)')):
            QtCore.QTimer.singleShot(0, lambda: app.activeModalWidget().reject())
            check(w.export_current_document(file_format='navigator') is None, 'cancel native export review returns without publishing')
        check((OUT / 'visible.json').read_bytes() == protected and state(doc) == frozen, 'review cancellation preserves existing output and source')
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(OUT / 'visible.json'), 'Navigator Layer files (*.json)')):
            def accept_reduced():
                active = app.activeModalWidget()
                check(isinstance(active, JSONAnnotationExportDialog), 'File export opens annotation policy review')
                active.visible_only.setChecked(True)
                active.export_button.click()
            QtCore.QTimer.singleShot(0, accept_reduced)
            check(w.export_current_document(file_format='navigator') == OUT / 'visible.json', 'native visible-only export publishes selected policy')
        check(state(doc) == frozen, 'native export leaves original name/content/dirty unchanged')
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName', return_value=(str(OUT / 'all.json'), 'JSON files (*.json)')):
            QtCore.QTimer.singleShot(0, lambda: app.activeModalWidget().export_button.click())
            check(w.export_all_layers() == OUT / 'all.json', 'Navigator all-layer menu opens review and writes a complete array by default')
        bundle = json.loads((OUT / 'all.json').read_text(encoding='utf-8'))
        check(bundle == [document_layer(d) for d in w.documents], 'native all-layer default retains each original full layer')
        QtCore.QTimer.singleShot(0, lambda: app.activeModalWidget().accept())
        check(w.review_json_annotations([doc], [None], OUT / 'full.json') is False, 'next review resets to full annotation retention')
        log('[JSON Audit 6/7] Saved documents and localized review', 5, 7)
        saved = save_studio(doc, OUT / 'state.studio.json', log)
        plan = annotation_export_plan(saved, {'visible_cells': set()})
        baseline = state(saved)
        plan.payload(True)
        check(state(saved) == baseline and not saved.dirty, 'projection leaves a clean Studio document clean')
        from localization import language_manager
        manager = language_manager()
        manager.set_language('zh_TW')
        localized = JSONAnnotationExportDialog([plan], OUT / 'full.json', w)
        localized.show()
        app.processEvents()
        check(localized.visible_only.text() == '只匯出可見技術的註記', 'review checkbox is localized')
        check('保留' in localized.warning.text(), 'localized warning states the complete default')
        check(localized.grab().save(str(OUT / 'review-zh.png')), 'localized review screenshot saved')
        localized.reject()
        manager.set_language('en')
        log('[JSON Audit 7/7] Writing verification report', 6, 7)
        (OUT / 'audit.json').write_text(json.dumps({'checks': CHECKS, 'count': len(CHECKS)}, ensure_ascii=False, indent=2), encoding='utf-8')
        log(f'[JSON Audit 7/7] PASS: {len(CHECKS)} checks', 7, 7)
    finally:
        with patch.object(MainWindow, 'confirm_studio_changes', return_value='discard'):
            w.close()
        app.processEvents()


if __name__ == '__main__':
    main()
