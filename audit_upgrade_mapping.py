"""NAV-023 destination expansion, conflict decisions, native UI and IO audit. Workflow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import time
import uuid

from PySide6 import QtCore, QtWidgets
from audit_advanced_navigator import fixture
from audit_upgrade_review import wait, reviewed, mapped
from attack_catalog import external_id, tactic_phases
from custom_sources import load_custom
from layer_upgrade import upgrade_preview, migration_plan, migrate_layer
from localization import language_manager
from main import configure_application
from navigator_dialogs import AnnotationDialog
from navigator_integration import document_layer, update_annotation, export_layers, SELECTION_MARKER
from source_dialogs import UpgradeDialog
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument
from ttp_selection import selected_cells
from upgrade_mapping import decision_targets, resolved_layer
from upgrade_mapping_dialogs import MappingTargetsDialog, ConflictResolutionDialog

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts/upgrade-mapping'
CACHE = OUT / 'cache'
DATA = ROOT / 'data/attack'
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
        check(text.lower() in str(error).lower(), message + ': ' + str(error))
    else:
        raise AssertionError(message)


def schedule_dialog(kind, action):
    state = {'done': False, 'errors': []}
    deadline = time.monotonic() + 30
    def poll():
        dialog = next((w for w in QtWidgets.QApplication.topLevelWidgets() if isinstance(w, kind) and w.isVisible()), None)
        if dialog is None:
            if time.monotonic() > deadline:
                state['errors'].append('Timed out opening ' + kind.__name__)
                state['done'] = True
                return
            QtCore.QTimer.singleShot(25, poll)
            return
        try:
            action(dialog)
        except Exception as error:
            state['errors'].append(str(error))
            dialog.reject()
        state['done'] = True
    QtCore.QTimer.singleShot(25, poll)
    return state


def resolutions_for(plan):
    results = []
    for conflict in plan['conflicts']:
        entry = {k: conflict[k] for k in ('target_id', 'target_scope', 'field', 'fingerprint')}
        entry.update(action='candidate', origin=conflict['candidates'][0]['origin'], reviewed=True)
        if conflict['field'] == 'score': entry.update(action='custom', value=5.5)
        elif conflict['field'] == 'x_audit_note': entry.update(action='clear')
        elif conflict['field'] == 'enabled': entry['origin'] = next(c['origin'] for c in conflict['candidates'] if c['value'] is True)
        results.append(entry)
    return results


def main():
    log('Input official data directory: ' + str(DATA.resolve()))
    log('Output fixtures, isolated cache, previews and report: ' + str(OUT.resolve()))
    OUT.mkdir(parents=True, exist_ok=True)
    log('[Mapping Audit 1/7] Prepare source and three-tactic target snapshots', 0, 7)
    catalogs = []
    for newer in (False, True):
        payload = fixture('19.3' if newer else '19.2', newer)
        if newer:
            tactic = deepcopy(next(o for o in payload['objects'] if o.get('type') == 'x-mitre-tactic'))
            tactic.update(id='x-mitre-tactic--' + str(uuid.uuid5(uuid.NAMESPACE_DNS, 'mapping-persistence')),
                          name='Persistence', x_mitre_shortname='persistence')
            payload['objects'].append(tactic)
            next(o for o in payload['objects'] if o['type'] == 'x-mitre-matrix')['tactic_refs'].append(tactic['id'])
            parent = next(o for o in payload['objects'] if o['type'] == 'attack-pattern' and external_id(o) == 'T1000')
            parent['kill_chain_phases'] = [{'kill_chain_name': 'mitre-attack', 'phase_name': slug}
                                          for slug in ('execution', 'initial-access', 'persistence')]
        path = OUT / ('target.json' if newer else 'source.json')
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        catalogs.append(load_custom(CACHE, str(path.resolve()), '19.2', log)['catalog'])
    source, target = catalogs
    ids = {external_id(o): k for k, o in source.records.items()}
    target_ids = {external_id(o): k for k, o in target.records.items()}
    doc = TTPDocument('Mapping source', source, selected={ids['T1000'], ids['T1000.001']})
    link = {'label': 'Common evidence', 'url': 'https://example.org/evidence', 'extra': 'preserved'}
    meta = {'name': 'Owner', 'value': 'Shared', 'extra': 123}
    update_annotation(doc, ids['T1000'], '', 'Common note', 2, '#112233', [link], [meta])
    update_annotation(doc, ids['T1000.001'], 'execution', 'Other note', 8, '#aabbcc',
                      [link, {'label': 'Child evidence', 'url': 'https://example.org/child'}], [meta, {'name': 'Case', 'value': 'Child'}])
    update_annotation(doc, ids['T1002'], '', 'Legacy annotation', 4, '')
    for row in doc.navigator_layer['techniques']:
        if row['techniqueID'] == 'T1000': row.update(enabled=False, x_audit_note={'origin': 'Parent'})
        elif row['techniqueID'] == 'T1000.001': row.update(enabled=True, x_audit_note={'origin': 'Child'})
    before = doc.fingerprint()
    preview = upgrade_preview(doc, target, log)
    decisions, reviews = mapped(preview), reviewed(preview)
    parent_index = next(i for i, r in enumerate(preview['rows']) if r['source_id'] == 'T1000')
    child_index = next(i for i, r in enumerate(preview['rows']) if r['source_id'] == 'T1000.001')
    decisions[parent_index]['targets'] = [{'target_id': 'T1000', 'target_scope': slug} for slug in ('execution', 'initial-access')]
    decisions[child_index].update(target_id='T1000', target_scope='execution')
    log('[Mapping Audit 2/7] Destination validation and exact partial selection', 1, 7)
    for targets, text in [([], 'one to'), ([{'target_id': 'T1000', 'target_scope': 'unknown'}], 'valid target'),
                          ([{'target_id': 'T9999', 'target_scope': ''}], 'valid target'),
                          ([{'target_id': 'T1000', 'target_scope': None}], 'valid target'),
                          ([{'target_id': 'T1000', 'target_scope': ''}] * 2, 'Duplicate'),
                          ([{'target_id': 'T1000', 'target_scope': ''}, {'target_id': 'T1000', 'target_scope': 'execution'}], 'overlap'),
                          ([{'target_id': 'T1000', 'target_scope': ''}] * 101, 'one to')]:
        bad(lambda ts=targets: decision_targets({'action': 'Copy', 'targets': ts}, target), text, 'invalid destination list blocked')
    single = deepcopy(decisions)
    single[child_index]['action'] = 'Drop'
    split = migrate_layer(doc, target, single, 'Split only', log, reviews=reviews)
    cells = {(external_id(target.records[key]), slug) for key, slug in selected_cells(split)}
    check(cells == {('T1000', 'execution'), ('T1000', 'initial-access')}, 'one selected source maps to exactly two explicit target tactics')
    check(split.selection_scopes[target_ids['T1000']] == ['execution', 'initial-access'], 'unrequested third tactic is not selected or broadened')
    check(len([r for r in split.navigator_layer['techniques'] if r['techniqueID'] == 'T1000']) == 2, 'two explicit tactic annotations are emitted without a global row')
    per_target = deepcopy(single)
    per_target[parent_index]['annotation_patch'] = {'score': 10}
    per_target[parent_index]['targets'][1]['annotation_patch'] = {'score': 0, 'comment': 'Specific destination'}
    distinct = migrate_layer(doc, target, per_target, 'Per destination', reviews=reviews)
    scores = {r['tactic']: r['score'] for r in distinct.navigator_layer['techniques'] if r['techniqueID'] == 'T1000'}
    check(scores == {'execution': 10, 'initial-access': 0}, 'destination-specific edits override shared edits including zero')
    multiple_ids = deepcopy(single)
    multiple_ids[parent_index]['targets'][1] = {'target_id': 'T1001', 'target_scope': 'execution'}
    cross = migrate_layer(doc, target, multiple_ids, 'Multiple techniques', reviews=reviews)
    check(cross.selected == {target_ids['T1000'], target_ids['T1001']}, 'one source may explicitly map to different target techniques')
    log('[Mapping Audit 3/7] Candidate/custom/clear field decisions and stale binding', 2, 7)
    plan = migration_plan(doc, target, decisions, log, reviews=reviews)
    check({c['field'] for c in plan['conflicts']} == {'score', 'color', 'enabled', 'x_audit_note'}, 'all conflicting scalar and extension fields are enumerated')
    check(all(c['target_scope'] == 'execution' for c in plan['conflicts']), 'fan-in conflicts are scoped to the colliding target tactic')
    bad(lambda: migrate_layer(doc, target, decisions, 'Unresolved', reviews=reviews), 'Conflicting', 'unresolved collision cannot silently overwrite annotations')
    resolutions = resolutions_for(plan)
    result = migrate_layer(doc, target, decisions, 'Resolved', log, reviews=reviews, resolutions=resolutions)
    row = next(r for r in result.navigator_layer['techniques'] if r['techniqueID'] == 'T1000' and r['tactic'] == 'execution')
    check(row['score'] == 5.5 and row['color'] == '#112233' and row['enabled'] is True and 'x_audit_note' not in row,
          'custom score, chosen color/enabled and explicit extension clear are applied')
    check(row['comment'].count('Common note') == 1 and row['comment'].count('Other note') == 1, 'distinct comments are retained once with source labels')
    check(len(row['links']) == 2 and row['links'][0]['extra'] == 'preserved', 'links merge without duplicate evidence and retain extension fields')
    check(len(row['metadata']) == 2 and row['metadata'][0]['extra'] == 123, 'metadata merge without duplicates and preserve extensions')
    three = deepcopy(decisions)
    legacy_index = next(i for i, r in enumerate(preview['rows']) if r['source_id'] == 'T1002')
    three[legacy_index].update(target_id='T1000', target_scope='execution', annotation_patch={
        'comment': 'Common note', 'score': 2, 'color': '#112233', 'enabled': False, 'links': [link], 'metadata': [meta]})
    three_plan = migration_plan(doc, target, three, reviews=reviews)
    three_result = migrate_layer(doc, target, three, 'Three sources', reviews=reviews, resolutions=resolutions_for(three_plan))
    combined = next(r for r in three_result.navigator_layer['techniques'] if r.get('tactic') == 'execution')
    check(combined['comment'].count('Common note') == 1 and len(combined['links']) == 2 and len(combined['metadata']) == 2,
          'three-way fan-in deduplicates a comment/link/metadata repeated by a later source')
    check(not any(m.get('name') == SELECTION_MARKER for r in result.navigator_layer['techniques'] for m in r.get('metadata', [])), 'internal selection markers do not duplicate in migration rows')
    initial = next(r for r in result.navigator_layer['techniques'] if r.get('tactic') == 'initial-access')
    check(initial['score'] == 2 and initial['x_audit_note'] == {'origin': 'Parent'}, 'resolutions do not affect noncolliding destinations')
    check(doc.fingerprint() == before and result.migration_archives[-1]['layer'] == document_layer(doc), 'success preserves immutable source and full original archive')
    bad(lambda: migrate_layer(doc, target, decisions, 'Missing', reviews=reviews, resolutions=resolutions[:-1]), 'Conflicting', 'every conflicting field needs a decision')
    bad(lambda: migrate_layer(doc, target, decisions, 'Duplicate', reviews=reviews, resolutions=resolutions + resolutions[:1]), 'duplicate', 'duplicate conflict decisions rejected')
    bad(lambda: migrate_layer(doc, target, decisions, 'Unreviewed', reviews=reviews,
        resolutions=[{**r, 'reviewed': False} for r in resolutions]), 'Review', 'unacknowledged field decision rejected')
    changed = deepcopy(decisions)
    changed[parent_index]['annotation_patch'] = {'comment': 'Candidates changed'}
    bad(lambda: migrate_layer(doc, target, changed, 'Stale', reviews=reviews, resolutions=resolutions), 'changed', 'fingerprint rejects stale resolutions after any candidate edit')
    bad(lambda: migrate_layer(doc, target, single, 'Unrelated', reviews=reviews, resolutions=resolutions), 'Stale', 'resolutions for conflicts no longer present are rejected')
    foreign = deepcopy(resolutions)
    next(r for r in foreign if r['action'] == 'candidate')['origin'] = 'source:999:0'
    bad(lambda: migrate_layer(doc, target, decisions, 'Foreign candidate', reviews=reviews, resolutions=foreign), 'current conflict candidate',
        'a resolution cannot refer to a nonexistent candidate')
    injected = deepcopy(single)
    injected[parent_index]['targets'][0]['annotation_patch'] = {'techniqueID': 'T9999'}
    bad(lambda: migrate_layer(doc, target, injected, 'Injected', reviews=reviews), 'only comment', 'per-destination patch cannot rewrite technique identity')
    invalid = deepcopy(resolutions)
    next(r for r in invalid if r['field'] == 'score').update(action='custom', value=float('nan'))
    bad(lambda: migrate_layer(doc, target, decisions, 'NaN', reviews=reviews, resolutions=invalid), 'finite', 'nonfinite custom resolution rejected')
    invalid = deepcopy(resolutions)
    next(r for r in invalid if r['field'] == 'enabled').update(action='custom', value=1)
    bad(lambda: migrate_layer(doc, target, decisions, 'Bad type', reviews=reviews, resolutions=invalid), 'boolean', 'custom resolution retains field type validation')
    unreviewed = [{**d, 'reviewed': False} for d in decisions]
    pending_reviews = [{**r, 'reviewed': False} for r in reviews]
    check(migration_plan(doc, target, unreviewed, reviews=pending_reviews, require_review=False)['conflicts'] == plan['conflicts'],
          'conflict preview is available before acknowledgement without bypassing final review')
    bad(lambda: migrate_layer(doc, target, unreviewed, 'Pending', reviews=reviews, resolutions=resolutions), 'Review', 'resolved fields do not bypass source-row review')
    extra = deepcopy(reviews)
    next(r for r in extra if r['id'] == 'T1003')['annotation_rows'] = [{'techniqueID': 'T1003', 'score': 100}]
    draft_plan = migration_plan(doc, target, single, reviews=extra)
    check(any(c['target_id'] == 'T1003' and any(v['origin'].startswith('target:') for v in c['candidates']) for c in draft_plan['conflicts']),
          'independent target drafts participate in the same conflict review')
    log('[Mapping Audit 4/7] Native destination list, per-target editor and cancellation', 3, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    manager = language_manager(); manager.set_language('en')
    parent = QtWidgets.QWidget(); parent.operation_report = log
    dialog = UpgradeDialog(DATA, doc, [TTPDocument('Target', target)], parent)
    dialog.loaded((target, preview)); dialog.show()
    dialog.review_tabs.setCurrentIndex(1); dialog.table.setCurrentCell(parent_index, 0)
    def set_destinations(editor):
        c = editor.controls[0]; c['scope'].setCurrentIndex(c['scope'].findData('execution'))
        editor.add_target({'target_id': 'T1000', 'target_scope': 'initial-access'})
        editor.add_target({'target_id': 'T1000', 'target_scope': 'execution'})
        editor.save()
        check(editor.result() != QtWidgets.QDialog.DialogCode.Accepted and 'Duplicate' in editor.error.text(),
              'native duplicate destination cannot be saved')
        editor.table.setCurrentCell(2, 0); editor.remove_target()
        editor.add_target({'target_id': 'T1000', 'target_scope': 'persistence'})
        editor.table.setCurrentCell(2, 0); editor.remove_target()
        editor.save()
    state = schedule_dialog(MappingTargetsDialog, set_destinations)
    dialog.edit_mapping_targets()
    check(not state['errors'] and len(dialog.mapping_targets[parent_index]) == 2, 'native add/remove destination list saves atomically')
    check(not dialog.controls[parent_index]['scope'].isEnabled() and dialog.comparison.destination.count() == 2, 'multi-target source uses explicit list and destination inspection selector')
    saved_targets = deepcopy(dialog.mapping_targets)
    state = schedule_dialog(MappingTargetsDialog, lambda editor: (editor.controls[0]['scope'].setCurrentIndex(0), editor.reject()))
    dialog.edit_mapping_targets()
    check(not state['errors'] and dialog.mapping_targets == saved_targets, 'cancelling destination edits preserves previous list')
    dialog.comparison.destination.setCurrentIndex(1)
    state = schedule_dialog(AnnotationDialog, lambda editor: (editor.comment.setPlainText('Second target only'), editor.score.setText('42'), editor.save()))
    dialog.comparison.edit_target()
    check(not state['errors'] and dialog.mapping_targets[parent_index][1]['annotation_patch']['score'] == 42,
          'annotation editor saves a branch-specific target draft')
    check('annotation_patch' not in dialog.mapping_targets[parent_index][0], 'branch edit leaves other destination untouched')
    child_control = dialog.controls[child_index]
    child_control['technique'].setCurrentIndex(child_control['technique'].findData('T1000'))
    child_control['scope'].setCurrentIndex(child_control['scope'].findData('execution'))
    check(not dialog.review_panel.states['T1000']['reviewed'] and not dialog.review_panel.states['T1000.001']['reviewed'], 'mapping/branch edits invalidate affected technique acknowledgements')
    log('[Mapping Audit 5/7] Native conflict review, invalid JSON, reopening and stale invalidation', 4, 7)
    def fill_resolutions(editor):
        for c in editor.controls:
            field = c['conflict']['field']
            if field == 'score':
                c['choice'].setCurrentIndex(c['choice'].findData('custom')); c['value'].setPlainText('6.75')
            elif field == 'x_audit_note': c['choice'].setCurrentIndex(c['choice'].findData('clear'))
            elif field == 'enabled':
                candidate = next(v for v in c['conflict']['candidates'] if v['value'] is True)
                c['choice'].setCurrentIndex(c['choice'].findData('candidate|' + candidate['origin']))
            else: c['choice'].setCurrentIndex(1)
            c['reviewed'].setChecked(True)
        score = next(c for c in editor.controls if c['conflict']['field'] == 'score')
        score['reviewed'].setChecked(False); editor.save()
        check('review every' in editor.error.text(), 'native incomplete field acknowledgement is blocked')
        score['value'].setPlainText('NaN'); score['reviewed'].setChecked(True); editor.save()
        check(editor.result() != QtWidgets.QDialog.DialogCode.Accepted and 'finite' in editor.error.text(), 'native invalid custom JSON cannot be accepted: ' + editor.error.text())
        score['value'].setPlainText('6.75'); score['reviewed'].setChecked(True)
        app.processEvents()
        check(editor.grab().save(str(OUT / 'conflicts-en.png')), 'native conflict candidate/field screenshot saved')
        manager.set_language('zh_TW')
        check(editor.windowTitle() == '解決搬移衝突' and editor.grab().save(str(OUT / 'conflicts-zh.png')),
              'Traditional Chinese field conflict editor and preview preserve current choices')
        manager.set_language('en')
        editor.save()
    state = schedule_dialog(ConflictResolutionDialog, lambda editor: editor.reject())
    dialog.review_conflicts()
    check(dialog.conflict_preview_pending and not dialog.targets_button.isEnabled(), 'planning remains locked until the conflict preview has been presented')
    wait(lambda: state['done'])
    check(not state['errors'] and not dialog.conflict_resolutions, 'cancelling conflict review commits no resolution')
    state = schedule_dialog(ConflictResolutionDialog, fill_resolutions)
    dialog.review_conflicts(); wait(lambda: state['done'])
    check(not state['errors'] and len(dialog.conflict_resolutions) == 4, 'native candidate/custom/clear resolutions save with fingerprints: ' + repr(state['errors']))
    old_resolutions = deepcopy(dialog.conflict_resolutions)
    def inspect_existing(editor):
        check(all(c['reviewed'].isChecked() for c in editor.controls), 'unchanged conflict review reopens previous choices and acknowledgements')
        editor.reject()
    state = schedule_dialog(ConflictResolutionDialog, inspect_existing)
    dialog.review_conflicts(); wait(lambda: state['done'])
    check(not state['errors'] and dialog.conflict_resolutions == old_resolutions, 'cancel on reopened conflicts preserves existing decisions')
    child_control['scope'].setCurrentIndex(child_control['scope'].findData('persistence'))
    check(not dialog.conflict_resolutions, 'any mapping change invalidates prior UI field resolutions')
    child_control['scope'].setCurrentIndex(child_control['scope'].findData('execution'))
    state = schedule_dialog(ConflictResolutionDialog, fill_resolutions)
    dialog.review_conflicts(); wait(lambda: state['done'])
    check(not state['errors'] and dialog.conflict_resolutions, 'changed mapping can be re-reviewed and resolved')
    dialog.mark_reviewed()
    dialog.show_changes(parent_index)
    check(dialog.grab().save(str(OUT / 'mapping-en.png')), 'native multi-destination comparison preview saved')
    manager.set_language('zh_TW')
    check(dialog.targets_button.text() == '編輯映射目標…' and dialog.conflicts_button.text() == '審核搬移衝突…', 'mapping and conflict controls translate to Traditional Chinese')
    check(dialog.grab().save(str(OUT / 'mapping-zh.png')), 'Traditional Chinese mapping preview saved')
    manager.set_language('en')
    dialog.create(); wait(lambda: dialog.worker and not dialog.worker.isRunning())
    check(dialog.result_document is not None, 'native resolved migration installs a complete new document: ' + dialog.status.text())
    native = dialog.result_document
    scores = {r.get('tactic'): r.get('score') for r in native.navigator_layer['techniques'] if r['techniqueID'] == 'T1000'}
    check(scores == {'execution': 6.75, 'initial-access': 42}, 'native final result contains both resolved and per-branch scores')
    check(len(native.navigator_layer['x_ttp_studio_upgrade']['conflict_resolutions']) == 4, 'native result persists every field conflict decision')
    check(doc.fingerprint() == before, 'native editing/cancellation/conflict review leaves original unchanged')
    log('[Mapping Audit 6/7] Studio/session/Navigator and legacy compatibility', 5, 7)
    path = OUT / 'resolved.studio.json'; save_studio(native, path, log)
    reopened = open_studio(CACHE, path, log)
    check(reopened.navigator_layer == native.navigator_layer and reopened.selection_scopes == native.selection_scopes,
          'Studio reopens expanded annotations, partial selection and conflict audit')
    check(reopened.migration_archives == native.migration_archives, 'Studio retains immutable source migration archive')
    session = OUT / 'session.json'; write_session(session_payload([native], 0, {}), session, log)
    check(read_session(CACHE, session, log)['documents'][0].content_token() == native.content_token(), 'session recovery restores destinations and resolved fields')
    export_layers([native], OUT / 'resolved.navigator.json', log)
    exported = json.loads((OUT / 'resolved.navigator.json').read_text(encoding='utf-8'))
    if isinstance(exported, list): exported = exported[0]
    check(exported['x_ttp_studio_upgrade']['review_schema'] == 2 and len(exported['x_ttp_studio_upgrade']['conflict_resolutions']) == 4,
          'Navigator JSON preserves new mapping/resolution audit schema')
    check(all(sum(m.get('name') == SELECTION_MARKER for m in row.get('metadata', [])) <= 1 for row in exported['techniques']), 'export emits at most one internal selection marker per row')
    legacy = mapped(preview)
    legacy_result = migrate_layer(doc, target, legacy, 'Legacy one-to-one', reviews=reviews)
    check(any(r.get('comment') == 'Common note' and not r.get('tactic') for r in legacy_result.navigator_layer['techniques']), 'legacy one-target API and all-tactics semantics remain valid')
    native_conflicts = native.navigator_layer['x_ttp_studio_upgrade']['conflict_resolutions']
    check(all(len(r['fingerprint']) == 64 and 'resolved_value' in r for r in native_conflicts), 'every saved resolution records candidate fingerprint and effective value')
    carry = UpgradeDialog(DATA, doc, [], parent)
    carry.loaded((target, preview))
    carry.mapping_targets[parent_index] = [{'target_id': 'T1000', 'target_scope': 'execution', 'annotation_patch': {'score': 13}}]
    carry.controls[parent_index]['technique'].setCurrentIndex(carry.controls[parent_index]['technique'].findData('T1001'))
    check(carry.annotation_edits[parent_index]['score'] == 13 and parent_index not in carry.mapping_targets,
          'single-destination branch edits follow a later legacy-column remap without being lost')
    carry.reject()
    failed_preview = UpgradeDialog(DATA, doc, [], parent)
    failed_preview.loaded((target, preview))
    failed_preview.review_conflicts()
    wait(lambda: failed_preview.worker and not failed_preview.worker.isRunning())
    wait(lambda: failed_preview.conflicts_button.isEnabled())
    check(not failed_preview.conflict_preview_pending and failed_preview.status.text().startswith('Failed:'),
          'invalid mapping preview failure releases the planning lock for retry')
    failed_preview.reject()
    empty = UpgradeDialog(DATA, TTPDocument('Empty source', source), [], parent)
    empty.loaded((target, upgrade_preview(empty.document, target)))
    empty.review_conflicts(); wait(lambda: empty.worker and not empty.worker.isRunning())
    wait(lambda: 'No conflicting' in empty.conflict_note.text())
    check(not empty.conflict_resolutions, 'empty conflict plan reports an explicit empty state')
    empty.reject()
    log('[Mapping Audit 7/7] Publish reproducible result', 6, 7)
    (OUT / 'audit.json').write_text(json.dumps({'passed': True, 'count': len(CHECKS), 'checks': CHECKS,
        'conflict_fields': [c['field'] for c in plan['conflicts']]}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log(f'[Mapping Audit] PASS: {len(CHECKS)} checks', 7, 7)
    parent.close()


if __name__ == '__main__':
    main()
