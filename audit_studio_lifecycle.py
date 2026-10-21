"""Validate complete Studio saves and native recovery/exit. Workflow: README.md."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time
from unittest.mock import patch
import uuid

from PySide6 import QtCore, QtWidgets
from attack_catalog import load_catalog, external_id
from attack_versions import snapshot_pointer
from audit_advanced_navigator import fixture
from custom_sources import load_custom
from layer_analysis import snapshot_document
from main import MainWindow, configure_application
from navigator_integration import document_layer, update_annotation, export_layer
from studio_files import (StudioReader, open_studio, save_studio, read_session, write_session,
                          session_payload, read_json, session_checksum)
from studio_dialogs import StudioTaskDialog
from ttp_documents import TTPDocument, document_payload, export_document_json, export_document_csv

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts' / 'studio-lifecycle'
CHECKS = []


def log(message, current=0, total=0):
    print(message + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, label):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def bad(task, label):
    try:
        task()
    except (ValueError, TypeError, OSError, KeyError):
        check(True, label)
    else:
        raise AssertionError(label)


def wait(condition, label):
    end = time.monotonic() + 80
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError(label)
        QtWidgets.QApplication.processEvents()
        time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def write_payload(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def shutdown(window, answer=QtWidgets.QMessageBox.StandardButton.Discard):
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=answer):
        window.close()
    wait(lambda: not window.isVisible(), 'window shutdown')


def main():
    log(f'Input directory: {DATA.resolve()}')
    log(f'Output directory: {OUT.resolve()}')
    OUT.mkdir(parents=True, exist_ok=True)
    pointers = {p: p.read_bytes() for p in [DATA/'active.json', DATA/'latest.json'] if p.exists()}
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    official = load_catalog(DATA, log)
    older = load_catalog(DATA, log, snapshot_pointer(DATA, '11.3'))
    task = next(k for k, v in official.records.items() if external_id(v) == 'T1053.005')
    d = TTPDocument('Research 中文', official, selected={task})
    update_annotation(d, task, '', 'Multiline\n註解', 2.75, '#aabbcc',
                      links=[{'label':'Reference','url':'https://example.org/ttp'}, {'divider':True}],
                      metadata=[{'name':'Analyst','value':'研究員'}, {'divider':True}])
    d.navigator_layer['techniques'][0].update(enabled=False, x_lab={'keep':[0, False, '資料']})
    d.navigator_layer['x_lab'] = {'keep':True}
    d.navigator_import_selected = {'T1053.005'}
    log('[Lifecycle audit 1/7] Complete state, domains, versions and provenance')
    original_layer = deepcopy(d.navigator_layer)
    d.set_catalog(older)
    update_annotation(d, task, '', 'Historical', 0, '')
    d.set_catalog(older.for_domain('mobile-attack'))
    mk = next(iter(d.catalog.records))
    d.selected = {mk}
    update_annotation(d, mk, '', 'Mobile archive', 3, '#55aa66')
    d.set_catalog(official.for_domain('mobile-attack'))
    d.selected.intersection_update(d.catalog.records)
    d.set_catalog(official)
    check(d.navigator_layer == original_layer, 'test fixture restores original Enterprise layer')
    d.migration_archives = [{'domain':older.domain, 'version':older.version, 'dataset_id':'', 'custom_source':'',
        'layer':document_layer(TTPDocument('Archive', older, selected={task})),
        'selected_stix_ids':[task], 'import_selected':['T1053.005']}]
    before = d.content_token()
    saved = save_studio(d, OUT/'Research.json', log, save_as=True)
    check(d.content_token() == before and d.save_path is None, 'core save does not mutate source draft')
    check(not saved.dirty and saved.save_path == OUT/'Research.json', 'successful save records complete baseline and path')
    loaded = open_studio(DATA, saved.save_path, log)
    check(loaded.content_token() == saved.content_token(), 'all selections/annotations/domain/version/migration archives round-trip')
    check(loaded.document_id == d.document_id and loaded.created_at_utc == d.created_at_utc, 'document UUID/creation time preserved')
    check(not loaded.dirty, 'opened Studio JSON starts clean')
    check(loaded.navigator_layer['techniques'][0]['score'] == 2.75, 'fractional scores retained')
    check(not loaded.navigator_layer['techniques'][0]['enabled'] and task in loaded.selected, 'disabled included TTP remains independently selected')
    check(loaded.navigator_layer['x_lab'] == {'keep':True}, 'unknown Navigator extensions retained')
    check(bool(loaded.domain_snapshots) and bool(loaded.navigator_snapshots), 'inactive domain and version archives restored')
    switched = snapshot_document(loaded)
    switched.set_catalog(official.for_domain('mobile-attack'))
    check('11.3' in switched.navigator_snapshots and switched.catalog.domain == 'mobile-attack', 'reopened domain archive remains usable')
    switched.set_catalog(official)
    check(switched.navigator_layer == original_layer, 'round-trip domain switch restores original annotations')
    payload = document_payload(saved)
    legacy = deepcopy(payload); legacy.pop('navigator_import_selected')
    reader = StudioReader(DATA, log)
    check(reader.document(legacy).selected == saved.selected, 'legacy Studio 1.0 JSON without new optional fields opens')
    for domain in ('mobile-attack','ics-attack'):
        catalog = official.for_domain(domain)
        doc = TTPDocument(domain, catalog, selected={next(iter(catalog.records))})
        s = save_studio(doc, OUT/(domain+'.json'), log, True)
        check(open_studio(DATA, s.save_path, log).content_token() == s.content_token(), domain + ' saves/reopens independently')
    historical = load_catalog(DATA, log, snapshot_pointer(DATA, '1.0'))
    hs = save_studio(TTPDocument('Historical', historical, selected={next(iter(historical.records))}), OUT/'historical.json', log, True)
    check(open_studio(DATA, hs.save_path, log).content_token() == hs.content_token(), 'historical v1.0 selection document reopens without requiring Navigator annotations')
    bundle = OUT/'custom-bundle.json'; write_payload(bundle, fixture())
    custom = load_custom(DATA, str(bundle), '19.2', log)['catalog']
    cd = TTPDocument('Custom', custom, selected={next(iter(custom.records))})
    cs = save_studio(cd, OUT/'custom.json', log, True)
    cr = open_studio(DATA, cs.save_path, log)
    check(cr.catalog.dataset_id == custom.dataset_id and cr.content_token() == cs.content_token(), 'custom Bundle reopens from exact verified content-hash cache')
    custom_reader = StudioReader(DATA, log)
    cp = document_payload(cs)
    custom_reader.document(cp)
    cp['attack']['source_url'] = 'https://example.org/same-bundle.json'
    check(custom_reader.document(cp).catalog.custom_source == cp['attack']['source_url'], 'shared custom hash cache retains each document source provenance')
    wrong_custom = deepcopy(cp); wrong_custom['attack']['version'] = '999.9'
    bad(lambda:custom_reader.document(wrong_custom), 'custom Bundle declared release must match Studio dataset version')

    log('[Lifecycle audit 2/7] Invalid input, atomic writes and external changes')
    mutations = [
        ('unsupported schema', lambda p:p.update(schema_version='99')),
        ('wrong domain', lambda p:p['attack'].update(domain='other')),
        ('unavailable version', lambda p:p['attack'].update(version='999.9')),
        ('selection count mismatch', lambda p:p.update(selected_count=99)),
        ('duplicate selected IDs', lambda p:p['selected_technique_ids'].append('T1053.005')),
        ('STIX/ATT&CK mismatch', lambda p:p['selected_ttps'][0].update(technique_id='T9999')),
        ('unknown selected STIX ID', lambda p:p['selected_ttps'][0].update(stix_id='attack-pattern--'+str(uuid.uuid4()))),
        ('bad UUID', lambda p:p.update(document_id='invalid')),
        ('bad creation time', lambda p:p.update(created_at_utc='2026-01-01')),
        ('wrong annotation domain', lambda p:p['navigator_layer'].update(domain='mobile-attack')),
        ('wrong annotation version', lambda p:p['navigator_layer']['versions'].update(attack='11.3')),
        ('invalid score', lambda p:p['navigator_layer']['techniques'][0].update(score=float('inf'))),
        ('bad version archive', lambda p:p['navigator_snapshots'].update({'nonsense':{}})),
        ('bad domain archive', lambda p:p['domain_snapshots'].update({'invalid':{}})),
        ('bad migration source', lambda p:p['migration_archives'][0].update(dataset_id='../../other')),
        ('custom source requires digest', lambda p:p['attack'].update(custom=True)),
    ]
    for label, change in mutations:
        candidate = deepcopy(payload); change(candidate)
        bad(lambda p=candidate: reader.document(p), 'reject ' + label)
    invalid = OUT/'invalid.json'
    invalid.write_text('{"schema_version":"1.0","schema_version":"1.0"}', encoding='utf-8')
    bad(lambda:read_json(invalid, log), 'duplicate JSON properties rejected')
    invalid.write_text('{"value":1e999}', encoding='utf-8')
    bad(lambda:read_json(invalid, log), 'overflow JSON numbers rejected')
    invalid.write_text('not JSON', encoding='utf-8')
    bad(lambda:open_studio(DATA, invalid, log), 'malformed JSON rejected')
    invalid.write_text('[]', encoding='utf-8')
    bad(lambda:read_json(invalid, log, limit=1), 'bounded reader enforces input limit')
    bad(lambda:open_studio(DATA, OUT/'wrong-extension.txt', log), 'Studio Open enforces recoverable JSON filename extension')
    protected = saved.save_path.read_bytes()
    broken = snapshot_document(saved); broken.name='Never committed'
    with patch('pathlib.Path.replace', side_effect=OSError('Injected publish failure')):
        bad(lambda:save_studio(broken, saved.save_path, log), 'atomic publication failure surfaced')
    check(saved.save_path.read_bytes() == protected and not list(OUT.glob('*.tmp')), 'failed save preserves previous bytes and removes temporary files')
    saved.save_path.write_bytes(protected+b' ')
    bad(lambda:save_studio(saved, saved.save_path, log), 'externally modified save target rejected')
    check(saved.save_path.read_bytes() == protected+b' ', 'external edits never overwritten by Save')
    saved.save_path.write_bytes(protected)
    rename = snapshot_document(saved); rename.name='In-app Rename'
    rename = save_studio(rename, rename.save_path, log)
    check(rename.name == 'In-app Rename' and open_studio(DATA, rename.save_path, log).name == rename.name, 'Save preserves explicit in-app rename at the same path')
    saved = save_studio(rename, OUT/'New Name.json', log, True)
    check(saved.name == 'New Name' and (OUT/'Research.json').exists(), 'Save As adopts new name and retains original file')
    csv_doc = TTPDocument('CSV', official, selected={task})
    export_document_csv(csv_doc, OUT/'exchange.csv', log)
    check(csv_doc.dirty and csv_doc.save_path is None, 'CSV exchange cannot mark a complete Studio document saved')
    export_layer(csv_doc, OUT/'exchange.navigator.json', log)
    check(csv_doc.dirty and csv_doc.save_path is None, 'Navigator exchange cannot mark a Studio document saved')
    export_document_json(csv_doc, OUT/'exchange.studio.json', log)
    check(not csv_doc.dirty and csv_doc.save_path is not None, 'complete Studio JSON export is also a usable save baseline')

    log('[Lifecycle audit 3/7] Session snapshots preserve dirty and clean states')
    dirty = snapshot_document(saved); dirty.name='Unwritten draft'
    empty = TTPDocument('Untitled-9', official)
    dirty2 = TTPDocument('New unsaved', official, selected={task})
    documents = [saved, dirty2, empty, cs]
    view = {'page':'matrix', 'details_open':False, 'category':'TTP', 'overlay':True, 'show_colors':False}
    checkpoint = OUT/'checkpoint.json'
    write_session(session_payload(documents, 1, view), checkpoint, log)
    restored = read_session(DATA, checkpoint, log)
    check([doc.content_token() for doc in restored['documents']] == [doc.content_token() for doc in documents], 'multi-document order, IDs and all content restored')
    check([doc.dirty for doc in restored['documents']] == [False,True,False,False], 'saved, dirty, empty and custom document dirty flags preserved')
    check(restored['active_index'] == 1 and restored['view'] == view, 'active tab and workspace view preserved')
    check(restored['documents'][0].save_path == saved.save_path, 'saved document paths survive recovery')
    envelope = json.loads(checkpoint.read_text(encoding='utf-8'))
    corrupt = deepcopy(envelope); corrupt['workspace']['active_index']=99
    write_payload(invalid, corrupt)
    bad(lambda:read_session(DATA, invalid, log), 'tampered checkpoint checksum rejected')
    for label, change in [
        ('duplicate document IDs', lambda p:p['documents'].append(deepcopy(p['documents'][0]))),
        ('bad active tab', lambda p:p.update(active_index=99)),
        ('relative save path', lambda p:p['documents'][0].update(save_path='../outside.json')),
        ('invalid baseline', lambda p:p['documents'][0].update(saved_fingerprint='invalid')),
        ('invalid view', lambda p:p['view'].update(page='other')),
    ]:
        candidate=deepcopy(envelope['workspace']); change(candidate)
        write_payload(invalid, {'workspace':candidate,'checksum':session_checksum(candidate)})
        bad(lambda:read_session(DATA, invalid, log), 'reject session ' + label)
    saved_path_bytes = saved.save_path.read_bytes()
    saved.save_path.write_bytes(saved_path_bytes+b' ')
    changed = read_session(DATA, checkpoint, log)['documents'][0]
    check(changed.dirty and changed.saved_file_sha256 == saved.saved_file_sha256, 'recovery notices changed disk file and retains conflict detection baseline')
    saved.save_path.write_bytes(saved_path_bytes)
    checkpoint_bytes = checkpoint.read_bytes()
    with patch('pathlib.Path.replace', side_effect=OSError('Injected checkpoint failure')):
        bad(lambda:write_session(session_payload([dirty],0,view), checkpoint, log), 'checkpoint publication failure surfaced')
    check(checkpoint.read_bytes() == checkpoint_bytes and not list(OUT.glob('*.tmp')), 'checkpoint failure preserves previous recovery file')

    log('[Lifecycle audit 4/7] Native Open, Save, shortcuts and cancellation')
    w = MainWindow(DATA, settings_path=OUT/'audit-ui.ini')
    w.resize(1500,950); w.show()
    wait(lambda:w.loaded_ok and not w.loader.isRunning(), 'native startup')
    calls=[]
    dialog=StudioTaskDialog('Open Studio JSON', lambda notify:calls.append('ran'), w)
    dialog.reject(); app.processEvents()
    check(not calls and dialog.worker is None, 'cancelling before worker startup prevents deferred IO')
    check(w.open_studio_action.shortcut().toString() == 'Ctrl+O', 'Open Studio shortcut Ctrl+O')
    check(w.save_action.shortcut().toString() == 'Ctrl+S' and w.save_as_action.shortcut().toString() == 'Ctrl+Shift+S', 'Save and Save As shortcuts')
    original=w.current_document
    opened=w.open_studio_document(saved.save_path)
    wait(lambda:w.loaded_ok, 'opened tree')
    check(opened in w.documents and w.current_document is opened and not opened.dirty, 'native Open installs an independent clean document')
    count=len(w.documents)
    check(w.open_studio_document(saved.save_path) is opened and len(w.documents)==count, 'reopening same path focuses existing tab')
    another=OUT/'same-id-copy.json'; another.write_bytes(saved.save_path.read_bytes())
    with patch.object(QtWidgets.QMessageBox,'warning') as warning:
        check(w.open_studio_document(another) is None and warning.called and len(w.documents)==count, 'duplicate UUID in another path rejected without workspace mutation')
    before=[doc.content_token() for doc in w.documents]
    with patch.object(QtWidgets.QMessageBox,'critical') as critical:
        check(w.open_studio_document(invalid) is None and critical.called, 'native malformed Open reports failure')
    check([doc.content_token() for doc in w.documents]==before, 'failed Open preserves every existing document')
    with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=('','')):
        check(w.open_studio_document() is None and len(w.documents)==count, 'cancelled Open preserves workspace')
    opened.name='Unsaved GUI'; w.update_document_labels()
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=('','')):
        check(w.save_studio_document(save_as=True) is None and opened.dirty, 'cancelled Save As retains dirty document')
    with patch.object(QtWidgets.QMessageBox,'critical') as critical:
        check(w.save_studio_document(target=OUT/'missing-folder'/'fail.json',save_as=True) is None and critical.called and opened.dirty, 'native failed Save keeps dirty document and existing path')
    with patch.object(QtWidgets.QMessageBox,'warning') as warning:
        original.save_path=OUT/'other-open.json'
        check(w.save_studio_document(target=original.save_path,save_as=True) is None and warning.called, 'Save As cannot overwrite another open tab')
        original.save_path=None
    p=w.save_studio_document(target=OUT/'Native.json',save_as=True)
    check(p and opened.name=='Native' and not opened.dirty and '*' not in w.document_tabs.tabText(w.active_document_index), 'native Save As updates name/path/baseline/star only after success')
    opened.name='Native renamed'; w.update_document_labels()
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName') as dialog:
        check(w.save_studio_document(frameworks=(True,True))==p and not dialog.called and not opened.dirty, 'Save reuses bound Studio path without file dialog')
    opened.name='Close draft'; w.update_document_labels()
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Cancel):
        check(not w.close_document(w.active_document_index) and opened in w.documents, 'Close Cancel preserves file')
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Save), \
            patch('studio_workspace.choose_frameworks',return_value=(True,True)):
        check(w.close_document(w.active_document_index) and opened not in w.documents, 'Close Save persists complete document before removing tab')
    check(open_studio(DATA,p,log).name=='Close draft', 'close-save writes latest annotations/name to disk')
    w.grab().save(str(OUT/'studio-file-menu-preview.png'))
    shutdown(w)

    log('[Lifecycle audit 5/7] Debounced checkpoints and crash-style recovery')
    session_file=OUT/('native-session-'+uuid.uuid4().hex+'.json')
    w=MainWindow(DATA,settings_path=OUT/'session-ui.ini',session_path=session_file)
    with patch.object(QtWidgets.QMessageBox,'question',side_effect=AssertionError('Fresh startup must not ask about recovery')) as question:
        w.show()
        wait(lambda:w.loaded_ok and w.session_initialized and not w.loader.isRunning(), 'checkpoint window')
        check(not question.called, 'startup without a checkpoint uses a fresh workspace without a question')
    first=w.current_document
    w.select_matrix_ttp(task, True)
    w.save_studio_document(target=OUT/'Session saved.json',save_as=True)
    w.new_document(); wait(lambda:w.loaded_ok, 'new draft')
    second=w.current_document
    w.select_matrix_ttp(task,True)
    update_annotation(second,task,'','Unsaved crash note',9.5,'#ff6633')
    second.name='Recovered draft'; w.refresh_selection()
    w.open_matrix(); wait(lambda:not w.matrix_view.building, 'matrix before crash')
    w.matrix_view.show_colors.setChecked(False)
    wait(lambda:session_file.exists() and w.session_worker and not w.session_worker.isRunning(), 'automatic debounce checkpoint')
    recovered=read_session(DATA,session_file,log)
    check(len(recovered['documents'])==2 and recovered['active_index']==1, 'automatic checkpoint captures all open tabs and active index')
    check(recovered['documents'][1].dirty and recovered['documents'][1].navigator_layer['techniques'][0]['comment']=='Unsaved crash note', 'automatic checkpoint retains unsaved annotation draft')
    before=[doc.content_token() for doc in w.documents]
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Cancel):
        check(not w.close() and w.isVisible(), 'application Exit Cancel preserves window')
    check([doc.content_token() for doc in w.documents]==before and not w.session_stopping, 'exit cancellation preserves workspace and automatic checkpoint capability')
    competing=MainWindow(DATA,settings_path=OUT/'competing-ui.ini',session_path=session_file); competing.show()
    wait(lambda:competing.loaded_ok and not competing.loader.isRunning(),'competing window')
    check(competing.session_path is None, 'second live instance cannot overwrite owned recovery file')
    shutdown(competing)
    # Simulate a crash without running the graceful exit/save/discard path.
    w.session_timer.stop(); w.session_stopping=True
    if w.session_worker and w.session_worker.isRunning(): w.session_worker.wait()
    w.session_lock.unlock(); w.hide()
    w2=MainWindow(DATA,settings_path=OUT/'session-ui.ini',session_path=session_file)
    with patch.object(QtWidgets.QMessageBox,'question',side_effect=AssertionError('Startup recovery must be automatic')) as question:
        w2.show()
        wait(lambda:w2.loaded_ok and w2.session_initialized and len(w2.documents)==2 and not w2.loader.isRunning(),'startup recovery')
        wait(lambda:w2.pending_session_notice is None,'automatic restore completion notice')
        check(not question.called, 'startup automatically restores the checkpoint without a confirmation question')
    wait(lambda:not w2.matrix_view.building,'restored matrix')
    check([doc.content_token() for doc in w2.documents]==before, 'native startup restores complete content of all draft and saved tabs')
    check(w2.active_document_index==1 and w2.current_document.name=='Recovered draft', 'startup restores active document')
    check(not w2.documents[0].dirty and w2.documents[1].dirty, 'native recovery preserves per-tab saved/dirty state')
    check(w2.tabs.currentIndex()==w2.matrix_tab_index and not w2.matrix_view.show_colors.isChecked(), 'matrix page and color visibility restored')
    output=w2.output.toPlainText()
    check('Automatically restored the previous session: 2 tabs (1 with unsaved changes).' in output,
          'bottom operation log announces restored tab and unsaved-draft counts')
    check(str(session_file.resolve()) in output and w2.output_panel.isVisible(),
          'restore notice shows the absolute checkpoint path in the visible output panel')
    w2.session_timer.stop()
    if w2.session_worker and w2.session_worker.isRunning(): w2.session_worker.wait()
    before_checkpoint=session_file.read_bytes()
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Cancel) as question:
        check(not w2.restore_studio_session() and question.called, 'explicit manual restore still asks before replacing the workspace')
    check([doc.content_token() for doc in w2.documents]==before and session_file.read_bytes()==before_checkpoint,
          'cancelling a manual restore retains the current documents and checkpoint')
    w2.session_initialized=True
    with patch.object(QtWidgets.QMessageBox,'warning') as warning:
        check(w2.save_studio_document(target=session_file,save_as=True) is None and warning.called, 'manual Save cannot overwrite its recovery file')
        warning.reset_mock()
        check(w2.export_current_document(session_file,'json') is None and warning.called, 'Studio export cannot overwrite its recovery checkpoint')
        warning.reset_mock()
        check(w2.export_all_layers(session_file) is None and warning.called, 'all-layers export cannot overwrite its recovery checkpoint')
    w2.menuBar().actions()[0].menu().popup(w2.mapToGlobal(QtCore.QPoint(10,30)))
    app.processEvents(); check(w2.grab().save(str(OUT/'recovered-workspace.png')), 'native recovered workspace screenshot saved')
    w2.menuBar().actions()[0].menu().close()
    shutdown(w2)
    check(not read_session(DATA,session_file,log)['documents'], 'Exit Discard invalidates all previous recovery drafts')
    empty=MainWindow(DATA,settings_path=OUT/'empty-session-ui.ini',session_path=session_file)
    with patch.object(QtWidgets.QMessageBox,'question',side_effect=AssertionError('Empty checkpoint must not prompt')) as question:
        empty.show()
        wait(lambda:empty.loaded_ok and empty.session_initialized and not empty.loader.isRunning(),'empty checkpoint startup')
        check(not question.called and len(empty.documents)==1 and not empty.current_document.dirty,
              'empty checkpoint starts a clean workspace without a recovery question')
    check('The previous checkpoint has no tabs; starting an empty workspace.' in empty.output.toPlainText(),
          'empty checkpoint is reported without a false restoration success')
    shutdown(empty)
    w.deleteLater()

    log('[Lifecycle audit 6/7] Exit Save All, partial cancellation and recovery failure')
    exit_file=OUT/('exit-session-'+uuid.uuid4().hex+'.json')
    w=MainWindow(DATA,settings_path=OUT/'exit-ui.ini',session_path=exit_file);w.show()
    wait(lambda:w.loaded_ok and not w.loader.isRunning(),'exit window')
    w.select_matrix_ttp(task,True); first=w.current_document
    w.new_document();wait(lambda:w.loaded_ok,'exit second')
    w.select_matrix_ttp(task,True); second=w.current_document
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Save), \
            patch('studio_workspace.choose_frameworks',return_value=(True,True)), \
            patch.object(QtWidgets.QFileDialog,'getSaveFileName',side_effect=[(str(OUT/'Exit first.json'),''),('','')]):
        check(not w.close() and w.isVisible(), 'cancelled second Save during Exit keeps whole workspace open')
    check(not first.dirty and second.dirty and len(w.documents)==2, 'successful first save retained after later Save cancellation')
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Save), \
            patch('studio_workspace.choose_frameworks',return_value=(True,True)), \
            patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(OUT/'Exit second.json'),'')):
        check(w.close() and not w.isVisible(), 'Exit Save All writes every remaining dirty tab then closes')
    recovered=read_session(DATA,exit_file,log)
    check(len(recovered['documents'])==2 and all(not doc.dirty for doc in recovered['documents']) and recovered['clean_exit'], 'graceful saved exit preserves clean workspace for next launch')
    corrupt_file=OUT/('bad-session-'+uuid.uuid4().hex+'.json'); corrupt_file.write_text('{broken',encoding='utf-8')
    w=MainWindow(DATA,settings_path=OUT/'bad-ui.ini',session_path=corrupt_file)
    with patch.object(QtWidgets.QMessageBox,'critical') as critical, \
            patch.object(QtWidgets.QMessageBox,'question',side_effect=AssertionError('Invalid startup recovery must not ask for restoration')) as question:
        w.show(); wait(lambda:w.loaded_ok and w.session_startup_done and not w.loader.isRunning(),'corrupt recovery startup')
        wait(lambda:w.integration_dialog is not None and w.integration_dialog.failure_message is not None,'corrupt recovery failure')
        app.processEvents()
        check(critical.called and not w.session_initialized, 'invalid recovery is reported and automatic overwrite suspended')
        check(not question.called and 'Automatically restored the previous session:' not in w.output.toPlainText(),
              'invalid checkpoint never requests restore confirmation or reports a false success')
    check(corrupt_file.read_text(encoding='utf-8')=='{broken' and len(w.documents)==1, 'failed recovery retains checkpoint bytes and current workspace')
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Yes):
        w.start_new_recovery()
    wait(lambda:corrupt_file.read_text(encoding='utf-8').startswith('{\n') and w.session_worker and not w.session_worker.isRunning(),'explicit recovery reset')
    check(len(read_session(DATA,corrupt_file,log)['documents'])==1, 'explicit new recovery session replaces invalid checkpoint')
    shutdown(w)

    w=MainWindow(DATA,settings_path=OUT/'exit-failure-ui.ini',session_path=OUT/('exit-failure-'+uuid.uuid4().hex+'.json'))
    w.show(); wait(lambda:w.loaded_ok and not w.loader.isRunning(),'exit checkpoint failure window')
    w.session_timer.stop()
    with patch('studio_workspace.write_session',side_effect=OSError('Injected final checkpoint failure')), \
            patch.object(QtWidgets.QMessageBox,'critical') as critical:
        check(not w.close() and w.isVisible() and critical.called, 'failed final checkpoint keeps the application open')
    check(not w.session_stopping and w.session_lock.isLocked(), 'failed exit retains session ownership for retry')
    shutdown(w)

    log('[Lifecycle audit 7/7] Official pointer isolation and report')
    check(all(p.read_bytes()==data for p,data in pointers.items()), 'Open/Save/recovery never change official snapshot pointers')
    check(not list(OUT.glob('*.tmp')), 'all atomic staging files cleaned')
    report=OUT/'audit.json'
    write_payload(report,{'passed':True,'assertions':len(CHECKS),'checks':CHECKS})
    log(f'PASS: {len(CHECKS)} assertions; report: {report.resolve()}')


if __name__ == '__main__':
    main()
