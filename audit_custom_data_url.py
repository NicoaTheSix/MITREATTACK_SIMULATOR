"""NAV-016 bounded local HTTP, reviewed binding, cancellation and round trips. Flow: README.md."""
from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets
from audit_navigator_bundle import layer, ready, workspace
from audit_source_selection import fixture
from audit_visibility_presets import wait
from attack_catalog import load_catalog
from custom_data_import import inspect_source, accept_source, resolve_location
from custom_sources import custom_catalog, load_layer_url
from main import MainWindow, configure_application
from navigator_dialogs import ImportLayerDialog
from navigator_import import LayerImportResolver, build_import_documents
from navigator_integration import document_layer, read_layers, export_layers
from studio_files import save_studio, open_studio, write_session, read_session, session_payload

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts' / 'custom-data-url'
CACHE = OUT / 'cache'
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
    except (ValueError, OSError, TypeError, InterruptedError):
        check(True, text)
    else:
        raise AssertionError(text)


def write(path, value):
    log('Output file: ' + str(path.resolve()))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    log('Input directory: ' + str(DATA))
    log('Output directory: ' + str(OUT))
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    pointers = {p: p.read_bytes() for p in (DATA / 'active.json', DATA / 'latest.json')}
    log('[Custom URL Audit 1/6] Starting isolated HTTP fixtures', 0, 6)
    payload = fixture()
    changed = deepcopy(payload)
    changed['objects'][0]['description'] = 'Changed bytes at the same release'
    other = deepcopy(payload)
    for obj in other['objects']:
        if obj.get('type') == 'x-mitre-collection':
            obj['x_mitre_version'] = '20.0'
    enterprise = deepcopy(payload)
    enterprise['objects'] = [obj for obj in enterprise['objects'] if 'enterprise-attack' in obj.get('x_mitre_domains', [])]
    encode = lambda value: json.dumps(value).encode('utf-8')
    raw, changed_raw = encode(payload), encode(changed)
    requests = []
    responses = {'/bundle': raw, '/stream-size': raw, '/final/bundle.json': raw, '/changed': changed_raw,
                 '/wrong-version': encode(other), '/enterprise': encode(enterprise), '/bad': b'not json'}
    layer_path = OUT / 'layers.json'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            requests.append(self.path)
            redirects = {'/redirect': '/final/bundle.json', '/bad-redirect': 'file:///C:/private.json',
                         '/loop': '/loop', '/layer-redirect': '/final/layer.json'}
            if self.path in redirects:
                self.send_response(302); self.send_header('Location', redirects[self.path]); self.end_headers()
                return
            if self.path == '/oversize':
                self.send_response(200); self.send_header('Content-Length', str(129 * 1024 * 1024)); self.end_headers()
                return
            content = responses.get(self.path)
            if self.path == '/index':
                content = encode({'collections': [{'name': 'Fixture', 'versions': [
                    {'version': '19.2', 'url': 'final/bundle.json'}, {'version': '20.0', 'url': 'wrong-version'}]}]})
            if content is None:
                self.send_error(404); return
            self.send_response(200)
            if self.path != '/stream-size':
                self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    log('Input fixture URL: ' + base)
    app = w = None
    try:
        catalog = custom_catalog(payload, sha256(raw).hexdigest(), base + '/bundle', '19.2', log)
        original = layer(catalog, 'T1000', 'Remote source layer')
        frozen = deepcopy(original)
        def inspect(item=original, suffix='/bundle', **kwargs):
            return inspect_source(CACHE, item, '19.2', base + suffix, layer_path, log, **kwargs)
        log('[Custom URL Audit 2/6] Transport, validation and explicit consent', 1, 6)
        candidate = inspect(suffix='/redirect')
        check(candidate['transport']['final'] == base + '/final/bundle.json', 'HTTP redirects retain the final source in review')
        check(not candidate['changed'] and candidate['digest'] == catalog.dataset_id, 'exact expected byte digest verified')
        check(not candidate['cache'].exists() or candidate['cache'].read_bytes() == raw, 'inspection never publishes unverified bytes')
        check(original == frozen, 'candidate preparation does not modify the imported layer')
        for suffix, message in [('/missing', 'HTTP 404 is explicit'), ('/bad', 'malformed JSON rejected'),
                                ('/loop', 'redirect loop is bounded'), ('/bad-redirect', 'non-HTTP redirect rejected'),
                                ('/oversize', 'oversized Content-Length rejected before reading'),
                                ('/wrong-version', 'wrong Bundle release rejected')]:
            bad(lambda suffix=suffix: inspect(suffix=suffix), message)
        bad(lambda: inspect(suffix='/stream-size', limit=128), 'stream byte cap is enforced without Content-Length')
        ics = deepcopy(original); ics['domain'] = 'ics-attack'
        bad(lambda: inspect(ics, '/enterprise'), 'missing requested domain rejected')
        for source in ('file:///C:/secret.json', 'ftp://example.org/bundle', 'https://user:password@example.org/bundle', 'bad\npath'):
            bad(lambda source=source: resolve_location(source, layer_path), 'invalid source location rejected: ' + source)
        check(resolve_location('bundle.json', layer_path) == str(OUT / 'bundle.json'), 'local relative reference resolves against JSON directory')
        check(resolve_location('../bundle', layer_path, base + '/final/layer.json') == base + '/bundle', 'remote relative reference resolves against final layer URL')
        check(resolve_location('/bundle.json', layer_path, base + '/final/layer.json') == base + '/bundle.json',
              'remote root-relative references retain URL semantics')
        check(resolve_location(OUT / 'bundle.json', layer_path, base + '/final/layer.json') == str(OUT / 'bundle.json'),
              'explicit local Path stays local when a remote layer origin is present')
        index_requests = len(requests)
        index = inspect(suffix='/index')
        check('entries' in index and len(requests) == index_requests + 1, 'Collection Index never auto-fetches a Bundle')
        check(index['entries'][0]['url'] == base + '/final/bundle.json', 'Collection Index relative URL resolved')
        altered = inspect(suffix='/changed')
        check(altered['changed'] and altered['expected'] == catalog.dataset_id, 'same-URL content change is detected by exact bytes')
        bad(lambda: accept_source(CACHE, altered, log), 'changed dataset cannot be accepted without explicit consent')
        accepted = accept_source(CACHE, candidate, log)
        check(accepted['path'].read_bytes() == raw, 'accepted candidate cached by SHA-256')
        accepted_changed = accept_source(CACHE, altered, log, True)
        check(accepted_changed['path'] != accepted['path'] and accepted['path'].read_bytes() == raw, 'replacement preserves original content-addressed cache')
        check(accepted_changed['layer']['x_ttp_studio_source_review']['changed_dataset_accepted'], 'replacement records explicit consent and old/new identities')
        local = OUT / 'bundle.json'; write(local, payload)
        local_candidate = inspect_source(CACHE, original, '19.2', str(local), layer_path, log)
        check(local_candidate['transport']['source'] == str(local), 'local Bundle alternative is validated')
        # The pretty-printed file intentionally has a different byte digest from the HTTP fixture.
        check(local_candidate['changed'], 'semantic equality does not bypass exact byte digest review')
        corrupt = CACHE / 'custom' / ('0' * 64 + '.json')
        log('Output file: ' + str(corrupt)); corrupt.write_bytes(raw)
        bad(lambda: inspect_source(CACHE, original, '19.2', str(corrupt), layer_path, log), 'tampered digest-named cache cannot be approved as a replacement')
        def cancel(message, current=0, total=0):
            if 'Candidate verified' in message:
                raise InterruptedError('Cancelled during validation')
        bad(lambda: inspect_source(CACHE, original, '19.2', base + '/bundle', layer_path, cancel), 'cancel during validation exposes no accepted source')
        log('[Custom URL Audit 3/6] Exact binding and persistence', 2, 6)
        pinned = accepted_changed['layer']
        resolver = LayerImportResolver(CACHE)
        results = resolver.preview([pinned], [0], {0: '19.2'}, {0: 'enabled'}, log)
        check(results[0]['catalog'].dataset_id == altered['digest'], 'accepted replacement resolves exactly from cache')
        docs = build_import_documents([pinned], [0], {0: '19.2'}, {0: 'enabled'}, {0: results[0]['catalog']}, log)
        check(docs[0].navigator_layer['techniques'] == original['techniques'], 'source replacement preserves every original annotation row')
        target = OUT / 'reviewed.studio.json'; save_studio(docs[0], target, log)
        restored = open_studio(CACHE, target, log)
        check(restored.navigator_layer == docs[0].navigator_layer, 'Studio reopening preserves reviewed provenance and exact binding')
        export_layers(docs, OUT / 'reviewed.navigator.json', log)
        check(read_layers(OUT / 'reviewed.navigator.json', log)[0]['x_ttp_studio_dataset'] == altered['digest'], 'Navigator re-export pins accepted dataset hash')
        write_session(session_payload(docs, 0, {'page': 'selected'}), OUT / 'session.json', log)
        check(read_session(CACHE, OUT / 'session.json', log)['documents'][0].content_token() == docs[0].content_token(), 'session recovery preserves reviewed custom binding')
        url_only = deepcopy(original); url_only.pop('x_ttp_studio_dataset')
        url_only['customDataURL'] = 'bundle.json'
        responses['/final/layer.json'] = encode(url_only)
        fetched_layer = load_layer_url(CACHE, base + '/layer-redirect', log)
        check(fetched_layer['origin'] == base + '/final/layer.json', 'remote Navigator redirect retains origin for relative customDataURL')
        log('[Custom URL Audit 4/6] Native import review, failure and cancellation', 3, 6)
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); configure_application(app)
        QtCore.QSettings(str(OUT / 'settings.ini'), QtCore.QSettings.Format.IniFormat).clear()
        w = MainWindow(DATA, DATA / 'latest.json', settings_path=OUT / 'settings.ini'); w.show()
        wait(lambda: w.loaded_ok and not w.loader.isRunning())
        official = w.catalog
        before = workspace(w)
        write(layer_path, [url_only, original])
        dialog = ImportLayerDialog(CACHE, layer_path, official, w, install=w.install_imported_documents, origin=fetched_layer['origin'])
        dialog.show(); ready(dialog)
        check(not dialog.import_button.isEnabled(), 'unresolved checked URL-only source blocks the whole batch')
        requests_before = len(requests)
        dialog.custom_button.click(); source = dialog.source_dialog
        check(source is not None and len(requests) == requests_before, 'opening source review does not initiate networking')
        source.load_button.click(); wait(lambda: not source.busy)
        check(source.candidate is not None and source.accept_button.isEnabled(), 'relative remote Bundle validates within import review')
        check(workspace(w) == before and dialog.layers[0] == url_only, 'source preview leaves workspace and pending binding unchanged')
        check(source.grab().save(str(OUT / 'source-preview.png')), 'source acquisition review screenshot')
        source.accept_button.click(); wait(lambda: not source.isVisible() and not source.busy)
        check(dialog.layers[0]['x_ttp_studio_dataset'] == catalog.dataset_id and dialog.layers[0]['customDataURL'] == base + '/final/bundle.json', 'acceptance pins hash and canonical source per layer')
        check(dialog.import_button.isEnabled() and len(w.documents) == len(before[0]), 'source acceptance readies the batch without opening documents')
        dialog.custom_button.click(); change = dialog.source_dialog
        change.location.setText(base + '/changed'); change.load_button.click(); wait(lambda: not change.busy)
        check(change.changed.isVisible() and not change.accept_button.isEnabled(), 'UI requires unchecked-by-default consent for changed source')
        check(change.grab().save(str(OUT / 'changed-source.png')), 'changed-source review screenshot')
        saved = deepcopy(dialog.layers)
        change.reject(); wait(lambda: not change.isVisible())
        check(dialog.layers == saved and workspace(w) == before, 'cancel changed-source review retains previous binding and workspace')
        dialog.custom_button.click(); changed_ui = dialog.source_dialog
        changed_ui.location.setText(base + '/changed'); changed_ui.load_button.click(); wait(lambda: not changed_ui.busy)
        changed_ui.changed.setChecked(True); changed_ui.accept_button.click()
        wait(lambda: not changed_ui.isVisible() and not changed_ui.busy)
        check(dialog.layers[0]['x_ttp_studio_dataset'] == altered['digest'], 'explicit UI consent replaces only the reviewed layer')
        check(dialog.layers[1] == original, 'another layer sharing the original source is unchanged')
        dialog.import_button.click(); wait(lambda: not dialog.isVisible() and not dialog.busy and w.loaded_ok)
        check(len(w.documents) == len(before[0]) + 2, 'reviewed multi-source batch installs all checked layers atomically')
        check(w.documents[-2].catalog.dataset_id == altered['digest'] and w.documents[-1].catalog.dataset_id == catalog.dataset_id,
              'same URL can retain independent accepted datasets across layers')
        log('[Custom URL Audit 5/6] Stale completion and cache choices', 4, 6)
        cancelled = ImportLayerDialog(CACHE, layer_path, official, w, origin=fetched_layer['origin'])
        cancelled.show(); ready(cancelled); cancelled.custom_button.click(); pending = cancelled.source_dialog
        started, release = threading.Event(), threading.Event()
        real_inspect = inspect_source
        def delayed(*args, **kwargs):
            started.set(); release.wait(10)
            return real_inspect(*args, **kwargs)
        before_cancel = deepcopy(cancelled.layers)
        with patch('custom_data_dialog.inspect_source', delayed):
            pending.load_button.click(); wait(started.is_set)
            cancelled.reject(); release.set()
            wait(lambda: not cancelled.isVisible() and not pending.worker.isRunning())
        check(cancelled.layers == before_cancel, 'cancelling parent during acquisition rejects late results without binding')
        cache_dialog = ImportLayerDialog(CACHE, layer_path, official, w, origin=fetched_layer['origin'])
        cache_dialog.show(); ready(cache_dialog); cache_dialog.custom_button.click(); picker = cache_dialog.source_dialog
        chosen = picker.cache.findData(str(accepted['path']))
        check(chosen > 0, 'cache chooser lists existing digest-named Bundles')
        picker.cache.setCurrentIndex(chosen); picker.load_button.click(); wait(lambda: not picker.busy)
        check(picker.candidate is not None and not picker.candidate['changed'], 'cached Bundle gets full validation before use')
        picker.location.setText('~ttp-source-test-nonexistent-user')
        check(picker.candidate is None and not picker.accept_button.isEnabled(),
              'editing an incomplete home-user path invalidates approval without a UI exception')
        picker.location.setText(base + '/missing'); picker.load_button.click(); wait(lambda: not picker.busy)
        check(picker.candidate is None and not picker.accept_button.isEnabled(), 'failed retry cannot reuse an earlier candidate')
        picker.location.setText(str(accepted['path'])); picker.load_button.click(); wait(lambda: not picker.busy)
        check(picker.candidate is not None and picker.candidate['transport']['source'] == str(accepted['path']),
              'typing a native absolute path keeps a local alternative local despite the remote layer origin')
        picker.location.setText(base + '/index'); picker.load_button.click(); wait(lambda: not picker.busy)
        check(picker.collection.isVisible() and picker.collection.count() == 2 and not picker.accept_button.isEnabled(), 'Collection Index offers explicit Bundle choices in the import UI')
        picker.collection.setCurrentIndex(0); picker.load_button.click(); wait(lambda: not picker.busy)
        check(picker.candidate is not None, 'chosen Collection Bundle validates within the same review')
        from localization import language_manager
        manager = language_manager(); manager.set_language('zh_TW'); app.processEvents()
        check(picker.load_button.text() == '取得／驗證來源' and picker.accept_button.text() == '使用已驗證的 Bundle', 'custom acquisition controls use Traditional Chinese labels')
        check('解析來源：' in picker.preview.toPlainText() and picker.candidate['digest'] in picker.preview.toPlainText(),
              'source review language switching translates labels without changing source identities')
        check(picker.grab().save(str(OUT / 'source-preview-zh.png')), 'Traditional Chinese source review screenshot')
        picker.reject(); cache_dialog.reject(); manager.set_language('en')
        legacy = deepcopy(original); legacy.pop('x_ttp_studio_dataset')
        legacy_path = OUT / 'legacy.json'; write(legacy_path, legacy)
        legacy_dialog = ImportLayerDialog(CACHE, legacy_path, official, w)
        legacy_dialog.show(); ready(legacy_dialog)
        check(legacy_dialog.import_button.isEnabled(), 'URL-only layer still resolves a unique loaded dataset offline')
        legacy_dialog.custom_button.click(); legacy_source = legacy_dialog.source_dialog
        check(legacy_source.layer['x_ttp_studio_dataset'] == catalog.dataset_id, 'source review uses the resolved dataset hash for a URL-only layer')
        legacy_source.location.setText(base + '/changed'); legacy_source.load_button.click(); wait(lambda: not legacy_source.busy)
        check(legacy_source.candidate['changed'] and not legacy_source.accept_button.isEnabled(), 'URL-only loaded source change also requires explicit consent')
        legacy_source.reject(); legacy_dialog.reject()
        cache_cancel = ImportLayerDialog(CACHE, layer_path, official, w, origin=fetched_layer['origin'])
        cache_cancel.show(); ready(cache_cancel); cache_cancel.custom_button.click(); cache_pending = cache_cancel.source_dialog
        cache_pending.load_button.click(); wait(lambda: not cache_pending.busy)
        previous_binding, previous_workspace = deepcopy(cache_cancel.layers), workspace(w)
        start_cache, release_cache = threading.Event(), threading.Event()
        def delayed_accept(*args, **kwargs):
            start_cache.set(); release_cache.wait(10)
            return accept_source(*args, **kwargs)
        with patch('custom_data_dialog.accept_source', delayed_accept):
            cache_pending.accept_button.click(); wait(start_cache.is_set)
            cache_cancel.reject(); release_cache.set()
            wait(lambda: not cache_cancel.isVisible() and not cache_pending.worker.isRunning())
        check(cache_cancel.layers == previous_binding and workspace(w) == previous_workspace,
              'cancel during cache acceptance leaves bindings and all workspace documents unchanged')
        shutdown_dialog = ImportLayerDialog(CACHE, layer_path, official, w, origin=fetched_layer['origin'])
        w.show_integration_dialog(shutdown_dialog); ready(shutdown_dialog)
        shutdown_dialog.custom_button.click(); shutdown_source = shutdown_dialog.source_dialog
        started.clear(); release.clear()
        with patch('custom_data_dialog.inspect_source', delayed), patch.object(w, 'confirm_studio_changes', return_value='discard'):
            shutdown_source.load_button.click(); wait(started.is_set)
            w.close()
            check(w.isVisible() and shutdown_source.closing, 'application close requests cancellation and waits for nested source worker')
            release.set()
            wait(lambda: not w.isVisible() and not shutdown_source.worker.isRunning())
        check(shutdown_dialog.layers == [url_only, original], 'application exit never accepts a late source result')
        check(all(path.read_bytes() == data for path, data in pointers.items()), 'custom acquisition never changes official active/latest pointers')
        check(original == frozen, 'all operations preserve original imported data')
        log('[Custom URL Audit 6/6] Writing verification report', 5, 6)
        write(OUT / 'audit.json', {'passed': True, 'count': len(CHECKS), 'checks': CHECKS})
        log(f'[Custom URL Audit] PASS: {len(CHECKS)} checks', 6, 6)
    finally:
        if w is not None:
            with patch.object(w, 'confirm_studio_changes', return_value='discard'):
                w.close()
            app.processEvents()
        server.shutdown(); server.server_close(); thread.join(5)


if __name__ == '__main__':
    main()
