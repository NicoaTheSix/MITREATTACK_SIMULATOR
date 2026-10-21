"""NAV-021 deterministic model, native dialog and persistence audit. Workflow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import time
import uuid

from PySide6 import QtCore, QtWidgets
from audit_advanced_navigator import fixture
from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from custom_sources import load_custom
from layer_upgrade import upgrade_preview, migrate_layer
from main import configure_application
from localization import language_manager
from navigator_dialogs import AnnotationDialog
from navigator_integration import document_layer, update_annotation, export_layers
from source_dialogs import UpgradeDialog
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument
from ttp_selection import selected_cells
from upgrade_review import CATEGORIES

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts' / 'upgrade-review'
CACHE = OUT / 'cache'
CHECKS = []


def log(message, current=0, total=0):
    print(str(message) + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, message):
    if not value:
        raise AssertionError(message)
    CHECKS.append(message)


def bad(task, text, message):
    try:
        task()
    except ValueError as error:
        check(text in str(error), message + ': ' + str(error))
    else:
        raise AssertionError(message)


def reviewed(preview):
    return [{'id': item['id'], 'reviewed': True} for item in preview['items']]


def mapped(preview):
    return [{'action': row['action'] if row['target_id'] else 'Drop', 'reviewed': True,
             'target_id': row['target_id'], 'target_scope': row['target_scope'] if row['target_scope'] is not None else 'initial-access'}
            for row in preview['rows']]


def wait(condition):
    limit = time.monotonic() + 45
    while not condition():
        QtWidgets.QApplication.processEvents()
        if time.monotonic() > limit:
            raise TimeoutError('Upgrade review worker')
        time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def main():
    log('Input datasets: ' + str(DATA.resolve()))
    log('Output fixtures, report and screenshots: ' + str(OUT.resolve()))
    OUT.mkdir(parents=True, exist_ok=True)
    log('[Review Audit 1/7] Prepare immutable source and target fixtures', 0, 7)
    catalogs = []
    for newer in (False, True):
        payload = fixture('19.3' if newer else '19.2', newer)
        removed = deepcopy(next(obj for obj in payload['objects'] if obj.get('name') == 'Beta'))
        removed.update(id='attack-pattern--' + str(uuid.uuid5(uuid.NAMESPACE_DNS, 'removed-review')), name='Removed example', x_mitre_deprecated=newer)
        removed['external_references'][0]['external_id'] = 'T1005'
        payload['objects'].append(removed)
        path = OUT / ('target.json' if newer else 'source.json')
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        catalogs.append(load_custom(CACHE, str(path.resolve()), '19.2', log)['catalog'])
    source, target = catalogs
    ids = {external_id(obj): key for key, obj in source.records.items()}
    target_ids = {external_id(obj): key for key, obj in target.records.items()}
    doc = TTPDocument('Review source', source, selected={ids['T1001']})
    update_annotation(doc, ids['T1000'], '', 'Keep annotation', 0, '#334455')
    update_annotation(doc, ids['T1000.001'], 'execution', 'Child tactic changed', 2, '')
    update_annotation(doc, ids['T1002'], '', 'Replacement annotation', 4, '')
    update_annotation(doc, ids['T1005'], '', 'Removed annotation', None, '')
    before = doc.fingerprint()
    preview = upgrade_preview(doc, target, log)
    expected = {'Added': {'T1003', 'T1004'}, 'Changed': {'T1000', 'T1000.001'},
                'Removed': {'T1005'}, 'Replaced': {'T1002'}, 'Unchanged': {'T1001'}}
    log('[Review Audit 2/7] Complete disjoint classification and strict review validation', 1, 7)
    for category in CATEGORIES:
        actual = {item['id'] for item in preview['items'] if item['category'] == category}
        check(actual == expected[category], category + ' covers exact identities including unannotated additions')
        check(preview['counts'][category] == len(actual), category + ' count matches list')
    check(sum(preview['counts'].values()) == len(set(ids) | set(target_ids)), 'categories partition source/target identity union')
    check(not next(i for i in preview['items'] if i['id'] == 'T1001')['annotated'], 'selection-only marker is not an authored annotation')
    check(next(i for i in preview['items'] if i['id'] == 'T1000')['annotated'], 'zero score and color count as annotations')
    decisions, reviews = mapped(preview), reviewed(preview)
    migrate = lambda rs=reviews, ds=decisions: migrate_layer(doc, target, ds, 'Reviewed result', log, reviews=rs)
    bad(lambda: migrate_layer(doc, target, decisions, 'Pending'), 'Review', 'omitting full review cannot bypass changed or added items')
    bad(lambda: migrate(reviews[:-1]), 'exactly once', 'missing hidden identity blocked')
    bad(lambda: migrate([reviews[0], *reviews[:-1]]), 'exactly once', 'duplicate identity blocked')
    bad(lambda: migrate([{**r, 'reviewed': False} if r['id'] == 'T1004' else r for r in reviews]), 'T1004', 'unannotated hidden Added item still blocks')
    bad(lambda: migrate([{**r, 'reviewed': 'true'} for r in reviews]), 'Review', 'review acknowledgement requires boolean true')
    bad(lambda: migrate(ds=[{**d, 'reviewed': False} for d in decisions]), 'Review', 'source mapping acknowledgement is independent')
    bad(lambda: migrate(ds=[{**d, 'action': 'Choose'} for d in decisions]), 'Review', 'unresolved removal cannot be copied implicitly')
    bad(lambda: migrate(ds=[{**d, 'target_scope': 'invalid-tactic'} if d['action'] == 'Copy' else d for d in decisions]),
        'valid target', 'acknowledged mapping still needs a valid target tactic')
    result = migrate()
    check(target_ids['T1004'] not in result.selected, 'reviewing/explicitly skipping Added does not select it')
    check(len(result.navigator_layer['x_ttp_studio_upgrade']['technique_reviews']) == 7, 'full technique audit survives migration')
    check(result.migration_archives[-1]['layer'] == document_layer(doc), 'unmodified source layer is archived')
    check(doc.fingerprint() == before, 'source document remains unchanged after success and errors')
    log('[Review Audit 3/7] Added annotations, explicit occurrence selection and collisions', 2, 7)
    enriched = deepcopy(reviews)
    added = next(r for r in enriched if r['id'] == 'T1004')
    added['annotation_rows'] = [{'techniqueID': 'T1004', 'tactic': 'execution', 'comment': 'New observation', 'score': 0,
                                 'color': '#abcdef', 'enabled': False,
                                 'links': [{'label': 'Evidence', 'url': 'https://example.org/evidence'}],
                                 'metadata': [{'name': 'Owner', 'value': 'Analyst'}]}]
    annotated = migrate(enriched)
    check(target_ids['T1004'] not in annotated.selected, 'annotation alone does not select Added')
    check(next(r for r in annotated.navigator_layer['techniques'] if r['techniqueID'] == 'T1004')['enabled'] is False,
          'Added annotation preserves independent disabled state and zero score')
    added['selected_scopes'] = ['execution']
    included = migrate(enriched)
    check((target_ids['T1004'], 'execution') in selected_cells(included), 'explicit Added occurrence is selected')
    corrupt = deepcopy(enriched)
    next(r for r in corrupt if r['id'] == 'T1004')['annotation_rows'][0]['tactic'] = 'persistence'
    bad(lambda: migrate(corrupt), 'valid, unique tactic', 'invalid Added annotation scope blocked')
    corrupt = deepcopy(enriched)
    next(r for r in corrupt if r['id'] == 'T1004')['annotation_rows'][0]['techniqueID'] = 'T1000'
    bad(lambda: migrate(corrupt), 'belong', 'cross-technique annotation injection blocked')
    corrupt = deepcopy(enriched)
    next(r for r in corrupt if r['id'] == 'T1001')['selected_scopes'] = ['execution']
    bad(lambda: migrate(corrupt), 'Only Added', 'existing identities cannot bypass source mapping with Added payload')
    corrupt = deepcopy(enriched)
    next(r for r in corrupt if r['id'] == 'T1004')['selected_scopes'] = ['initial-access']
    bad(lambda: migrate(corrupt), 'valid, unique tactic', 'invalid Added selection scope blocked')
    conflict = deepcopy(reviews)
    next(r for r in conflict if r['id'] == 'T1003')['annotation_rows'] = [{'techniqueID': 'T1003', 'score': 9}]
    bad(lambda: migrate(conflict), 'Conflicting score', 'Added draft cannot silently overwrite incoming replacement annotation')
    same = upgrade_preview(doc, source)
    check(same['counts']['Unchanged'] == len(source.records) and all(i['reviewed'] for i in same['items']), 'unchanged release auto-reviewed with empty change categories')
    unknown = TTPDocument('Unknown imported identity', source,
                          navigator_layer={**document_layer(doc), 'techniques': [{'techniqueID': 'T9999', 'comment': 'Unresolved'}]})
    unresolved = next(i for i in upgrade_preview(unknown, target)['items'] if i['id'] == 'T9999')
    check(unresolved['category'] == 'Removed' and unresolved['annotated'] and not unresolved['reviewed'],
          'unresolved imported annotations are retained as Removed requiring explicit mapping/drop')
    log('[Review Audit 4/7] Native category filters, acknowledgement, edit/cancel and worker retry', 3, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    manager = language_manager()
    manager.set_language('en')
    parent = QtWidgets.QWidget()
    parent.operation_report = log
    dialog = UpgradeDialog(DATA, doc, [TTPDocument('Target', target)], parent)
    dialog.loaded((target, preview))
    dialog.resize(1350, 850)
    dialog.show()
    panel = dialog.review_panel
    check(panel.table.rowCount() == 7 and dialog.table.rowCount() == len(decisions), 'catalog review and annotation mappings have independent complete tables')
    panel.category.setCurrentIndex(1)
    check(sum(not panel.table.isRowHidden(i) for i in range(7)) == 2, 'Added category shows both unannotated new identities')
    panel.annotated_only.setChecked(True)
    check(panel.empty.isVisible(), 'empty annotated Added category has an explicit empty state')
    check('Added: 0/2' in panel.counts.text(), 'category counts retain full review denominator under filter')
    panel.annotated_only.setChecked(False)
    row = next(i for i, item in enumerate(panel.items) if item['id'] == 'T1004')
    panel.table.setCurrentCell(row, 0)
    def edit_accept():
        editor = next(w for w in app.topLevelWidgets() if isinstance(w, AnnotationDialog) and w.isVisible())
        editor.comment.setPlainText('Native Added draft')
        editor.score.setText('0')
        check(not editor.include.isChecked(), 'Added editor defaults to unselected')
        editor.save()
    QtCore.QTimer.singleShot(50, edit_accept)
    panel.edit_added()
    check('T1004' in panel.drafts and not panel.drafts['T1004'].selected, 'native annotation saved without selecting')
    saved = panel.drafts['T1004'].fingerprint()
    def edit_cancel():
        editor = next(w for w in app.topLevelWidgets() if isinstance(w, AnnotationDialog) and w.isVisible())
        editor.comment.setPlainText('Cancelled mutation')
        editor.reject()
    QtCore.QTimer.singleShot(50, edit_cancel)
    panel.edit_added()
    check(panel.drafts['T1004'].fingerprint() == saved, 'cancel leaves previously saved Added draft unchanged')
    panel.annotated_only.setChecked(True)
    check(sum(not panel.table.isRowHidden(i) for i in range(7)) == 1, 'new authored draft participates in annotated-only filter')
    panel.annotated_only.setChecked(False)
    panel.category.setCurrentIndex(0)
    dialog.pending_only.setChecked(True)
    dialog.mark_reviewed()
    check(all(r['reviewed'] for r in panel.decisions()) and panel.empty.isVisible(), 'mark-visible uses frozen set while pending filter removes rows')
    check(json.loads(dialog.change_details.toPlainText())['reviewed'] is True, 'detail inspector reflects current acknowledgement rather than initial preview')
    child_index = next(i for i, item in enumerate(preview['rows']) if item['source_id'] == 'T1000.001')
    control = dialog.controls[child_index]
    control['scope'].setCurrentIndex(control['scope'].findData('initial-access'))
    check(not panel.states['T1000.001']['reviewed'], 'editing mapping invalidates identity review acknowledgement')
    removed_index = next(i for i, item in enumerate(preview['rows']) if item['source_id'] == 'T1005')
    dialog.controls[removed_index]['action'].setCurrentText('Drop')
    dialog.mark_reviewed()
    dialog.pending_only.setChecked(False)
    app.processEvents()
    check(dialog.grab().save(str(OUT / 'review.png')), 'native full review screenshot saved')
    manager.set_language('zh_TW')
    check(dialog.review_tabs.tabText(0) == '技術逐項審核' and panel.annotated_only.text() == '只顯示有註記的技術',
          'review tabs and annotated filter translate to Traditional Chinese')
    check(all(label in panel.counts.text() for label in ('新增', '變更', '移除', '替代', '未變更', '已審閱')),
          'all category counters translate without changing denominators')
    check(dialog.grab().save(str(OUT / 'review-zh.png')), 'native Traditional Chinese screenshot saved')
    manager.set_language('en')
    check('Unchanged: 1/1' in panel.counts.text() and 'Reviewed: 7/7' in panel.counts.text(), 'switching back restores English counters and exact totals')
    dialog.create()
    wait(lambda: dialog.worker and not dialog.worker.isRunning())
    if dialog.result_document is None:
        raise AssertionError('Native migration failed: ' + dialog.status.text())
    wait(lambda: dialog.result() == QtWidgets.QDialog.DialogCode.Accepted)
    native = dialog.result_document
    check(any(r.get('comment') == 'Native Added draft' for r in native.navigator_layer['techniques']), 'native worker commits reviewed Added draft')
    check(doc.fingerprint() == before, 'native workflow preserves original document')
    failed = UpgradeDialog(DATA, doc, [], parent)
    failed.loaded((target, preview))
    failed.create()
    wait(lambda: failed.worker and not failed.worker.isRunning())
    wait(lambda: failed.create_button.isEnabled())
    check(failed.result_document is None and failed.status.text().startswith('Failed:'), 'pending native review fails without installing a partial document')
    check(failed.review_panel.isEnabled() and failed.name.isEnabled(), 'worker failure restores editable review controls for retry')
    failed.reject()
    cancelled = UpgradeDialog(DATA, doc, [], parent)
    cancelled.loaded((target, preview))
    cancelled.reject()
    check(cancelled.result_document is None and doc.fingerprint() == before, 'closing review creates no output document')
    cancelled.invalidate()
    check(not cancelled.review_panel.states and not cancelled.preview_data, 'target invalidation clears all review and annotation drafts')
    busy = UpgradeDialog(DATA, doc, [], parent)
    def cancellation_checkpoint(notify):
        time.sleep(.05)
        notify('Cancellation checkpoint', 1, 1)
        return result
    busy.start_task(cancellation_checkpoint, busy.created)
    busy.reject()
    wait(lambda: not busy.worker.isRunning())
    check(busy.result_document is None and busy.closing, 'close during worker cancels before result installation')
    late = UpgradeDialog(DATA, doc, [], parent)
    installed = []
    late.imported.connect(installed.append)
    late.created(result)
    late.reject()
    app.processEvents()
    check(not installed and late.result() == QtWidgets.QDialog.DialogCode.Rejected, 'late queued completion cannot install a document after closing')
    log('[Review Audit 5/7] Studio/session/Navigator preservation', 4, 7)
    path = OUT / 'reviewed.studio.json'
    save_studio(included, path, log)
    reopened = open_studio(CACHE, path, log)
    check(reopened.navigator_layer['x_ttp_studio_upgrade'] == included.navigator_layer['x_ttp_studio_upgrade'], 'Studio retains every category and explicit skip/edit decision')
    check(reopened.migration_archives == included.migration_archives, 'Studio retains complete source archive')
    session = OUT / 'session.json'
    write_session(session_payload([included], 0, {}), session, log)
    restored = read_session(CACHE, session, log)['documents'][0]
    check(restored.content_token() == included.content_token(), 'session restores review audit, Added annotation and selection')
    export_layers([included], OUT / 'reviewed.navigator.json', log)
    exported = json.loads((OUT / 'reviewed.navigator.json').read_text(encoding='utf-8'))
    if isinstance(exported, list):
        exported = exported[0]
    check(exported['x_ttp_studio_upgrade']['category_counts'] == preview['counts'], 'Navigator export preserves complete review audit extension')
    log('[Review Audit 6/7] Complete real historical catalog partition', 5, 7)
    historical = load_catalog(DATA, log, snapshot_pointer(DATA, '11.3'))
    latest = load_catalog(DATA, log, DATA / 'latest.json')
    old_doc = TTPDocument('Historical review', historical)
    actual = upgrade_preview(old_doc, latest, log)
    old_ids = {external_id(o) for o in historical.records.values()}
    new_ids = {external_id(o) for o in latest.records.values()}
    check({i['id'] for i in actual['items']} == old_ids | new_ids, 'real 11.3 to latest covers all active source/target identities')
    check(actual['counts']['Added'] == len(new_ids - old_ids), 'real Added total is independent of annotation count')
    check(actual['counts']['Removed'] + actual['counts']['Replaced'] == len(old_ids - new_ids), 'real unavailable identities partition removed and explicit replacements')
    bad(lambda: migrate_layer(old_doc, latest, [], 'Bypass'), 'Review', 'empty historical annotation list cannot bypass whole-catalog review')
    log('[Review Audit 7/7] Publish reproducible report', 6, 7)
    report = {'passed': True, 'count': len(CHECKS), 'checks': CHECKS, 'fixture_counts': preview['counts'], 'historical_counts': actual['counts']}
    (OUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log(f'[Review Audit] PASS: {len(CHECKS)} checks', 7, 7)
    parent.close()


if __name__ == '__main__':
    main()
