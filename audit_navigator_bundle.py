"""NAV-015 exact multi-layer preview, atomic opening and persistence. Flow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import threading
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id, load_catalog, catalog_identity
from attack_versions import snapshot_pointer
from audit_source_selection import fixture
from audit_visibility_presets import wait
from custom_sources import load_custom
from layer_analysis import snapshot_document
from main import MainWindow, configure_application
from navigator_dialogs import ImportLayerDialog
from navigator_import import LayerImportResolver, build_import_documents, validate_import_documents
from navigator_integration import document_layer, read_layers, export_layers
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument
from ttp_selection import selected_cells

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts' / 'navigator-bundle'
CHECKS = []


def log(text, current=0, total=0):
    print(text + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, text):
    if not value:
        raise AssertionError(text)
    CHECKS.append(text)


def bad(task, text):
    try:
        task()
    except (ValueError, TypeError, KeyError, OSError, InterruptedError):
        check(True, text)
    else:
        raise AssertionError(text)


def write(path, value, encoding='utf-8'):
    log('Output file: ' + str(path.resolve()))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding=encoding)


def layer(catalog, identity, name='Shared layer name'):
    key = next(k for k, obj in catalog.records.items() if external_id(obj) == identity)
    doc = TTPDocument(name, catalog, selected={key}, navigator_layer={'name': name, 'domain': catalog.domain,
        'description': 'Keep description ' + catalog.domain, 'techniques': [
            {'techniqueID': identity, 'enabled': False, 'score': 2.75, 'color': '#2277aa',
             'comment': 'Keep annotation\nsecond line', 'metadata': [{'name': 'Owner', 'value': 'Research'}],
             'links': [{'label': 'Reference', 'url': 'https://example.org/'}], 'x_fixture': {'keep': True}},
            {'techniqueID': 'T9999', 'comment': 'Unresolved row retained'}]})
    return document_layer(doc)


def workspace(w):
    return ([doc.content_token() for doc in w.documents], w.active_document_index,
            [(w.document_tabs.tabText(i), w.document_tabs.tabData(i)) for i in range(w.document_tabs.count())],
            set(w.selected), catalog_identity(w.catalog))


def ready(dialog):
    wait(lambda: bool(dialog.layers) and not dialog.busy and not dialog.pending_resolve
         and all(i in dialog.results for i in dialog.selected_indices()))


def close_dialog(dialog):
    dialog.reject()
    wait(lambda: not dialog.isVisible() and (not dialog.worker or not dialog.worker.isRunning()))


def main():
    log('Input directory: ' + str(DATA.resolve()))
    log('Output directory: ' + str(OUT.resolve()))
    for name in ('settings.ini', 'preview.png', 'blocked.png', 'preview-zh.png', 'roundtrip.navigator.json', 'session.json', 'audit.json'):
        log('Output file: ' + str(OUT / name))
    OUT.mkdir(parents=True, exist_ok=True)
    pointers = {p: p.read_bytes() for p in (DATA / 'latest.json', DATA / 'active.json') if p.exists()}
    log('[Bundle Audit 1/7] Preparing exact official/custom datasets', 0, 7)
    official = load_catalog(DATA, log)
    older = load_catalog(DATA, log, snapshot_pointer(DATA, '11.3'))
    a_path, b_path = OUT / 'custom-a.json', OUT / 'custom-b.json'
    a_payload = fixture()
    b_payload = deepcopy(a_payload)
    next(obj for obj in b_payload['objects'] if obj.get('type') == 'attack-pattern')['description'] = 'Independent dataset B'
    for obj in b_payload['objects']:
        if obj.get('type') == 'x-mitre-collection':
            obj['x_mitre_version'] = '20.0'
    write(a_path, a_payload)
    write(b_path, b_payload)
    a = load_custom(DATA, str(a_path), '19.2', log)['catalog']
    b = load_custom(DATA, str(b_path), '20.0', log)['catalog']
    mobile = older.for_domain('mobile-attack')
    mobile_id = external_id(next(iter(mobile.records.values())))
    layers = [layer(official, 'T1053.005'), layer(mobile, mobile_id),
              layer(a.for_domain('ics-attack'), 'T1000.001'), layer(b.for_domain('mobile-attack'), 'T1000'),
              layer(a, 'T1000')]
    source = OUT / 'bundle.json'
    write(source, layers)
    frozen = deepcopy(layers)
    check(read_layers(source, log) == layers, 'complete array validates without changing any layer payload')
    utf16 = OUT / 'bundle-utf16.json'
    write(utf16, layers, 'utf-16')
    check(read_layers(utf16, log) == layers, 'multi-layer UTF-16 input is supported')
    versions = {i: item['versions']['attack'] for i, item in enumerate(layers)}
    policies = dict.fromkeys(range(len(layers)), 'enabled')
    indices = list(range(len(layers)))
    log('[Bundle Audit 2/7] Independent dataset resolution and complete drafts', 1, 7)
    resolver = LayerImportResolver(DATA, [official, a])
    with patch('navigator_import.prepare_version', side_effect=AssertionError('Automatic preview must stay offline')):
        results = resolver.preview(layers, indices, versions, policies, log)
    check(all(result['catalog'] for result in results.values()), 'every mixed-domain/version/custom layer resolves from local data')
    check(results[1]['catalog'].version == '11.3' and results[1]['catalog'].domain == 'mobile-attack', 'historical Mobile stays separate from current Enterprise')
    check(results[3]['catalog'].dataset_id == b.dataset_id, 'unopened custom dataset resolves by its verified cached SHA-256')
    check(results[2]['catalog'].domain == 'ics-attack' and results[2]['catalog'].dataset_id == a.dataset_id, 'custom ICS projection keeps the exact dataset')
    catalogs = {i: result['catalog'] for i, result in results.items()}
    documents = build_import_documents(layers, indices, versions, policies, catalogs, log)
    check(len({doc.document_id for doc in documents}) == len(layers), 'duplicate layer names receive independent document identities')
    for index, doc in enumerate(documents):
        check(doc.navigator_layer == layers[index], f'layer {index + 1}: comments, scores, states, links and metadata remain exact')
        check(len(doc.selected) == 1 and results[index]['preview']['unresolved'] == 1, f'layer {index + 1}: inclusion independent from enabled; unresolved row counted')
        check(catalog_identity(doc.catalog) == catalog_identity(catalogs[index]), f'layer {index + 1}: exact domain/version/dataset identity')
    check(layers == frozen, 'all previews and drafts preserve input layers')
    unknown_policy = resolver.preview(layers, [0], versions, {0: 'unsupported'}, log)
    check(unknown_policy[0]['catalog'] is None, 'unsupported selection policy cannot appear ready')
    unsupported = deepcopy(layers[0]); unsupported['versions']['attack'] = '1.0'
    unsupported_result = LayerImportResolver(DATA, [replace(official, version='1.0')]).preview(
        [unsupported], [0], {0: '1.0'}, {0: 'enabled'}, log)
    check(unsupported_result[0]['catalog'] is None and 'v4' in unsupported_result[0]['error'],
          'an unsupported historical official Navigator release is blocked during preview')
    bad(lambda: build_import_documents(layers, [-1], versions, policies, catalogs, log), 'negative layer indices are rejected')
    log('[Bundle Audit 3/7] Missing, ambiguous and corrupt sources; full-file rejection', 2, 7)
    missing = deepcopy(layers)
    missing[-1]['x_ttp_studio_dataset'] = '0' * 64
    errors = resolver.preview(missing, indices, versions, policies, log)
    check(errors[4]['catalog'] is None and bool(errors[4]['error']) and all(errors[i]['catalog'] for i in range(4)), 'bad selected dataset is explicit and never replaced with another dataset')
    no_version = deepcopy(layers[0]); no_version['versions']['attack'] = '99.9'
    with patch('navigator_import.prepare_version', side_effect=AssertionError('No implicit download')):
        absent = LayerImportResolver(DATA).preview([no_version], [0], {0: '99.9'}, {0: 'enabled'}, log)
    check(absent[0]['catalog'] is None and '99.9' in absent[0]['error'], 'missing official release blocks preview without networking')
    url_layer = deepcopy(layers[4]); url_layer.pop('x_ttp_studio_dataset'); url_layer['customDataURL'] = 'https://example.invalid/custom'
    match_a = replace(a, custom_source=url_layer['customDataURL'])
    match_b = replace(b, version='19.2', custom_source=url_layer['customDataURL'])
    check(LayerImportResolver(DATA, [match_a]).catalog(url_layer, '19.2', log).dataset_id == a.dataset_id, 'URL-only layer resolves a unique loaded exact-version dataset')
    bad(lambda: LayerImportResolver(DATA, [match_a, match_b]).catalog(url_layer, '19.2', log), 'ambiguous URL-only datasets require an explicit exact source')
    wrong_version = deepcopy(url_layer); wrong_version['versions']['attack'] = '11.3'
    bad(lambda: LayerImportResolver(DATA, [match_a]).catalog(wrong_version, '11.3', log), 'URL-only matching never crosses version boundaries')
    corrupt_root = OUT / 'corrupt-cache'
    (corrupt_root / 'custom').mkdir(parents=True, exist_ok=True)
    corrupt_path = corrupt_root / 'custom' / (b.dataset_id + '.json')
    write(corrupt_path, {'type': 'bundle', 'objects': []})
    corrupt = LayerImportResolver(corrupt_root).preview([layers[3]], [0], {0: b.version}, {0: 'enabled'}, log)
    check(corrupt[0]['catalog'] is None and 'SHA-256 mismatch' in corrupt[0]['error'], 'custom cache digest mismatch is rejected for the correct recorded release')
    late = deepcopy(layers); late[3]['techniques'][0]['score'] = 'invalid'
    bad(lambda: build_import_documents(late, indices, versions, policies, catalogs, log), 'late invalid layer prevents returning any batch drafts')
    for name, payload in [('empty.json', []), ('too-many.json', layers[:1] * 21), ('bad-one.json', late)]:
        path = OUT / name; write(path, payload)
        bad(lambda path=path: read_layers(path, log), name + ': entire file is rejected without dropping bad entries')
    twenty = OUT / 'twenty.json'; write(twenty, layers[:1] * 20)
    check(len(read_layers(twenty, log)) == 20, 'array upper limit of twenty layers is accepted')
    no_recorded = deepcopy(layers[0]); no_recorded['versions'].pop('attack')
    check(resolver.catalog(no_recorded, official.version, log).version == official.version, 'versionless layer uses its explicit preview choice')
    log('[Bundle Audit 4/7] Real preview: all/subset selection, per-layer choices and cancellation', 3, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    QtCore.QSettings(str(OUT / 'settings.ini'), QtCore.QSettings.Format.IniFormat).clear()
    w = MainWindow(DATA, DATA / 'latest.json', settings_path=OUT / 'settings.ini')
    w.resize(1800, 1100); w.show()
    try:
        wait(lambda: w.loaded_ok and not w.loader.isRunning())
        w.install_imported_document(TTPDocument('Existing custom source', a))
        wait(lambda: w.loaded_ok)
        before = workspace(w)
        w.import_navigator_layer(source)
        dialog = w.integration_dialog; ready(dialog)
        check(dialog.selected_indices() == indices and dialog.import_button.isEnabled(), 'native review checks every layer and readies the entire bundle')
        check(workspace(w) == before, 'preview changes neither existing documents nor active dataset')
        for index in indices:
            dialog.layer.setCurrentIndex(index)
            check(catalog_identity(dialog.catalog) == catalog_identity(catalogs[index]) and not dialog.version.isEnabled(), f'preview focus {index + 1} restores its own fixed version and catalog')
        dialog.select_none_button.click()
        check(not dialog.selected_indices() and not dialog.import_button.isEnabled(), 'deselect all prevents an empty batch')
        for index in (1, 3): dialog.layers_table.item(index, 0).setCheckState(QtCore.Qt.CheckState.Checked)
        check(dialog.selected_indices() == [1, 3] and dialog.import_button.isEnabled(), 'checkbox subsets keep file order and require only chosen layers')
        dialog.layer.setCurrentIndex(3); dialog.policy.setCurrentIndex(dialog.policy.findData('all'))
        dialog.layer.setCurrentIndex(1)
        check(dialog.policy.currentData() == 'enabled', 'each layer retains its independent selection policy')
        dialog.layer.setCurrentIndex(3)
        check(dialog.policy.currentData() == 'all', 'returning to a layer restores its edited policy')
        dialog.policy.setCurrentIndex(dialog.policy.findData('enabled'))
        dialog.select_all_button.click()
        check(dialog.grab().save(str(OUT / 'preview.png')), 'complete mixed-layer preview screenshot')
        close_dialog(dialog)
        check(workspace(w) == before, 'cancelling a fully resolved preview installs nothing')
        early = ImportLayerDialog(DATA, source, a, w)
        with patch('navigator_dialogs.read_layers', side_effect=AssertionError('Cancelled before file read')):
            early.reject(); app.processEvents()
            check(early.worker is None, 'cancel before deferred worker start prevents file IO')
        started, release = threading.Event(), threading.Event()
        original_preview = LayerImportResolver.preview
        def delayed(self, *args, **kwargs):
            started.set(); release.wait(15)
            return original_preview(self, *args, **kwargs)
        with patch.object(LayerImportResolver, 'preview', delayed):
            w.import_navigator_layer(source); cancel = w.integration_dialog
            wait(started.is_set)
            cancel.reject(); release.set()
            wait(lambda: not cancel.isVisible() and not cancel.worker.isRunning())
        check(workspace(w) == before, 'cancel during catalog resolution never installs a partial bundle')
        log('[Bundle Audit 5/7] Blocked entries, explicit subsets and atomic installation', 4, 7)
        blocked = OUT / 'blocked.json'; write(blocked, missing)
        w.import_navigator_layer(blocked); dialog = w.integration_dialog; ready(dialog)
        check(not dialog.import_button.isEnabled() and dialog.layers_table.item(4, 4).text(), 'one unresolved selected source blocks the whole batch with a per-row error')
        check(dialog.grab().save(str(OUT / 'blocked.png')), 'blocked-layer error screenshot')
        dialog.layers_table.item(4, 0).setCheckState(QtCore.Qt.CheckState.Unchecked)
        check(dialog.import_button.isEnabled(), 'explicitly excluding the blocked layer permits the remaining ready subset')
        close_dialog(dialog)
        check(workspace(w) == before, 'excluding then cancelling does not install a subset accidentally')
        w.import_navigator_layer(source); dialog = w.integration_dialog; ready(dialog)
        prior_count = len(w.documents)
        dialog.import_button.click()
        wait(lambda: len(w.documents) == prior_count + len(layers) and w.loaded_ok and not dialog.worker.isRunning())
        opened = w.documents[prior_count:]
        check(not dialog.isVisible() and w.current_document is opened[0], 'one click opens every checked layer and activates the first')
        check([doc.navigator_layer for doc in opened] == layers, 'installed batch retains all layer contents in original order')
        check([catalog_identity(doc.catalog) for doc in opened] == [catalog_identity(catalogs[i]) for i in indices], 'installation preserves every domain/version/dataset')
        check(len({doc.document_id for doc in w.documents}) == len(w.documents), 'same-name tabs remain independent through UUIDs')
        check([doc.content_token() for doc in w.documents[:prior_count]] == before[0], 'all original documents remain intact after successful opening')
        snapshot = workspace(w)
        rollback = build_import_documents(layers, [0, 1, 2], versions, policies, catalogs, log)
        original_set_data = w.document_tabs.setTabData
        calls = []
        def fail_tab(index, value):
            calls.append(index)
            if len(calls) == 2: raise RuntimeError('Injected second-tab failure')
            return original_set_data(index, value)
        with patch.object(w.document_tabs, 'setTabData', side_effect=fail_tab):
            check(not w.install_imported_documents(rollback), 'tab insertion failure is reported as a failed batch')
        check(workspace(w) == snapshot, 'failed tab insertion rolls back every added tab and document')
        damaged = snapshot_document(rollback[-1]); damaged.navigator_layer['domain'] = 'mobile-attack'
        check(not w.install_imported_documents([rollback[0], damaged]) and workspace(w) == snapshot, 'late invalid draft cannot install an earlier valid one')
        bad(lambda: validate_import_documents(rollback, [TTPDocument('Limit', official) for _ in range(49)]), 'over-capacity group is rejected before tab mutation')
        check(workspace(w) == snapshot, 'capacity preflight has no workspace effects')
        w.import_navigator_layer(source); subset = w.integration_dialog; ready(subset)
        subset.select_none_button.click(); subset.layers_table.item(3, 0).setCheckState(QtCore.Qt.CheckState.Checked)
        count = len(w.documents); subset.import_button.click()
        wait(lambda: len(w.documents) == count + 1 and w.loaded_ok and not subset.worker.isRunning())
        check(w.current_document.navigator_layer == layers[3], 'explicit subset opens only its checked layer')
        policy_layer = deepcopy(layers[4])
        policy_layer['techniques'].append({'techniqueID': 'T1001', 'enabled': False})
        choices_path = OUT / 'version-policy-choices.json'
        write(choices_path, [no_recorded, policy_layer])
        w.import_navigator_layer(choices_path); choices = w.integration_dialog; ready(choices)
        check(choices.version.isEnabled(), 'a layer without recorded release exposes its own version selector')
        choices.version.setCurrentText('11.3')
        check(not choices.import_button.isEnabled(), 'changing an unversioned layer invalidates the old catalog preview')
        choices.load_button.click(); ready(choices)
        check(choices.catalog.version == '11.3' and choices.import_button.isEnabled(), 'explicit Load/Preview resolves the newly chosen exact release')
        choices.layer.setCurrentIndex(1); choices.policy.setCurrentIndex(choices.policy.findData('all'))
        check(len(choices.preview['selected']) == 2, 'a layer-specific All policy includes its additional disabled technique')
        count = len(w.documents); choices.import_button.click()
        wait(lambda: len(w.documents) == count + 2 and w.loaded_ok and not choices.worker.isRunning())
        check(w.documents[count].catalog.version == '11.3' and len(w.documents[count + 1].selected) == 2,
              'batch opening applies each layer\'s edited version and policy independently')
        log('[Bundle Audit 6/7] Failure isolation, localization and persistence', 5, 7)
        before_failure = workspace(w)
        w.import_navigator_layer(OUT / 'bad-one.json'); invalid = w.integration_dialog
        wait(lambda: invalid.worker is not None and not invalid.worker.isRunning())
        check(not invalid.layers and not invalid.import_button.isEnabled() and workspace(w) == before_failure, 'bad schema anywhere in an array leaves the current workspace intact')
        close_dialog(invalid)
        w.import_navigator_layer(source); failed = w.integration_dialog; ready(failed)
        with patch('navigator_import.build_import_documents', side_effect=ValueError('Injected draft failure')):
            failed.import_button.click()
            wait(lambda: not failed.busy and not failed.worker.isRunning())
        check(failed.isVisible() and workspace(w) == before_failure, 'background draft failure installs no documents and leaves review available')
        close_dialog(failed)
        started, release = threading.Event(), threading.Event()
        def delayed_build(*args, **kwargs):
            started.set(); release.wait(15)
            return build_import_documents(*args, **kwargs)
        w.import_navigator_layer(source); cancel_draft = w.integration_dialog; ready(cancel_draft)
        with patch('navigator_import.build_import_documents', delayed_build):
            cancel_draft.import_button.click(); wait(started.is_set)
            cancel_draft.reject(); release.set()
            wait(lambda: not cancel_draft.isVisible() and not cancel_draft.worker.isRunning())
        check(workspace(w) == before_failure, 'cancel during final draft preparation installs no completed or partial group')
        from localization import language_manager
        manager = language_manager(); manager.set_language('zh_TW')
        w.import_navigator_layer(source); localized = w.integration_dialog; ready(localized)
        check(localized.select_all_button.text() == '全選圖層' and localized.import_button.text() == '開啟勾選圖層',
              'batch selection and opening controls use the Traditional Chinese labels')
        check([localized.layers_table.item(i, 1).text() for i in indices] == [item['name'] for item in layers],
              'localization preserves authored layer names')
        check(localized.grab().save(str(OUT / 'preview-zh.png')), 'Traditional Chinese batch preview screenshot')
        close_dialog(localized); manager.set_language('en')
        export_layers(opened, OUT / 'roundtrip.navigator.json', log)
        check(read_layers(OUT / 'roundtrip.navigator.json', log) == [document_layer(doc) for doc in opened], 'all opened layers re-export as a complete Navigator array')
        for index, doc in enumerate(opened):
            target = OUT / f'opened-{index + 1}.studio.json'
            saved = save_studio(doc, target, log)
            restored = open_studio(DATA, target, log)
            check(restored.navigator_layer == doc.navigator_layer and selected_cells(restored) == selected_cells(doc), f'layer {index + 1}: Studio Save/Open preserves annotations and exact selection')
            check(catalog_identity(restored.catalog) == catalog_identity(doc.catalog), f'layer {index + 1}: Studio reopening retains domain/version/dataset')
        write_session(session_payload(opened, 2, {'page': 'selected'}), OUT / 'session.json', log)
        recovered = read_session(DATA, OUT / 'session.json', log)
        check([doc.content_token() for doc in recovered['documents']] == [doc.content_token() for doc in opened], 'session recovery preserves the entire independently opened batch')
        log('[Bundle Audit 7/7] Pointer isolation and report', 6, 7)
        check(all(path.read_bytes() == content for path, content in pointers.items()), 'batch preview/import never changes official active/latest pointers')
        check(layers == frozen, 'input layers stay unchanged after preview, failure, opening and persistence')
        write(OUT / 'audit.json', {'passed': True, 'count': len(CHECKS), 'checks': CHECKS})
        log(f'[Bundle Audit] PASS: {len(CHECKS)} checks', 7, 7)
    finally:
        with patch.object(w, 'confirm_studio_changes', return_value='discard'):
            w.close()
        app.processEvents()


if __name__ == '__main__':
    main()
