"""NAV-024 final summary, skip reasons, navigation and persistence audit. Workflow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import uuid

from PySide6 import QtCore, QtWidgets
from audit_advanced_navigator import fixture
from audit_upgrade_review import wait, reviewed, mapped
from audit_upgrade_mapping import schedule_dialog, resolutions_for
from attack_catalog import external_id
from custom_sources import load_custom
from layer_upgrade import upgrade_preview, migration_plan, migrate_layer
from localization import language_manager
from main import configure_application
from navigator_integration import update_annotation, export_layers
from source_dialogs import UpgradeDialog
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument
from upgrade_summary import build_summary, validate_reasons, summary_token
from upgrade_summary_dialog import UpgradeSummaryDialog
from upgrade_mapping_dialogs import ConflictResolutionDialog

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts/upgrade-summary'
CACHE = OUT / 'cache'
DATA = ROOT / 'data/attack'
CHECKS = []


def log(message, current=0, total=0):
    print(str(message) + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, message):
    if not value:
        raise AssertionError(message)
    CHECKS.append(message)


def bad(task, fragment, message):
    try:
        task()
    except ValueError as error:
        check(fragment in str(error), message + ': ' + str(error))
    else:
        raise AssertionError(message)


def main():
    log('Input official catalogs: ' + str(DATA.resolve()))
    log('Output fixtures, cache, screenshots and report: ' + str(OUT.resolve()))
    OUT.mkdir(parents=True, exist_ok=True)
    log('[Summary Audit 1/7] Prepare five-category source and target fixtures', 0, 7)
    catalogs = []
    for newer in (False, True):
        payload = fixture('19.3' if newer else '19.2', newer)
        removed = deepcopy(next(o for o in payload['objects'] if o.get('name') == 'Beta'))
        removed.update(id='attack-pattern--' + str(uuid.uuid5(uuid.NAMESPACE_DNS, 'summary-removed')),
                       name='Removed summary example', x_mitre_deprecated=newer)
        removed['external_references'][0]['external_id'] = 'T1005'
        payload['objects'].append(removed)
        path = OUT / ('target.json' if newer else 'source.json')
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        catalogs.append(load_custom(CACHE, str(path.resolve()), '19.2', log)['catalog'])
    source, target = catalogs
    ids = {external_id(o): k for k, o in source.records.items()}
    doc = TTPDocument('Summary source', source, selected={ids['T1001']})
    update_annotation(doc, ids['T1000'], '', 'Keep', 0, '#334455')
    update_annotation(doc, ids['T1000.001'], 'execution', 'Child', 2, '')
    update_annotation(doc, ids['T1002'], '', 'Replacement', 4, '')
    update_annotation(doc, ids['T1005'], '', 'Removed', None, '')
    before = doc.content_token()
    preview = upgrade_preview(doc, target, log)
    decisions, reviews = mapped(preview), reviewed(preview)
    drop_index = next(i for i, r in enumerate(preview['rows']) if r['source_id'] == 'T1005')
    parent_index = next(i for i, r in enumerate(preview['rows']) if r['source_id'] == 'T1000')
    child_index = next(i for i, r in enumerate(preview['rows']) if r['source_id'] == 'T1000.001')
    reason = '保留舊版證據\nExcluded from target scope: 測試'
    reasons = {'source:' + str(drop_index): reason, 'added:T1004': 'No new annotation required',
               'source:' + str(parent_index): 'Inactive Copy reason draft'}
    report = build_summary(doc, target, decisions, '  Ready.json  ', log, reviews=reviews, skip_reasons=reasons)
    check(report['can_submit'] and not report['issues'], 'complete valid plan is ready with no pending checks')
    check(report['result_name'] == 'Ready', 'summary displays backend-normalized output name')
    check(report['source']['dataset_id'] == source.dataset_id and report['target']['dataset_id'] == target.dataset_id,
          'summary identifies exact source and target custom datasets')
    check(report['total'] == 7 and report['reviewed'] == 7, 'full identity union is counted including unannotated Added')
    for category in report['categories']:
        check(category['total'] == preview['counts'][category['category']] and category['reviewed'] == category['total'],
              category['category'] + ' full reviewed/total matches complete comparison')
    check(report['drop_rows'] == 1 and report['copy_rows'] == len(decisions) - 1, 'Copy and Drop count source rows independently of identities')
    check(len(report['skips']) == 3 and report['categories'][0]['state'] == 'Skipped', 'Added skips and dropped source are explicitly listed')
    check(next(s for s in report['skips'] if s.get('source_index') == drop_index)['reason'] == reason, 'Unicode multiline reason preserved exactly')
    check(not any(s['key'] == 'source:' + str(parent_index) for s in report['skips']), 'inactive Copy reason draft is omitted from emitted skips')
    check(report['conflicts'] == 0 and report['output_rows'] > 0, 'summary validates merged output and explicit zero conflicts')
    log('[Summary Audit 2/7] Incomplete reviews, mappings, drafts, names and reasons', 1, 7)
    pending_reviews = [{**r, 'reviewed': False} if r['id'] == 'T1004' else r for r in reviews]
    pending_decisions = deepcopy(decisions)
    pending_decisions[parent_index]['reviewed'] = False
    pending_decisions[child_index]['target_scope'] = 'removed-tactic'
    incomplete = build_summary(doc, target, pending_decisions, 'bad/name', reviews=pending_reviews)
    check(not incomplete['can_submit'] and {i['kind'] for i in incomplete['issues']} == {'technique', 'mapping', 'name'},
          'one summary aggregates hidden technique, source review, invalid scope and name failures')
    check(any(i.get('identity') == 'T1004' for i in incomplete['issues']), 'unannotated Added pending identity has a direct return target')
    check(any(i.get('source_index') == child_index for i in incomplete['issues']), 'invalid reviewed mapping has an exact source-row return target')
    check(next(c for c in incomplete['categories'] if c['category'] == 'Changed')['state'] == 'Incomplete', 'invalid mapping makes fully acknowledged category incomplete')
    check(not build_summary(doc, target, decisions, 'No roster', reviews=reviews[:-1])['can_submit'], 'missing review roster entry is blocked')
    check(not build_summary(doc, target, decisions, 'Malformed roster', reviews=[None])['can_submit'], 'malformed review roster produces a blocked report instead of bypassing validation')
    check(not build_summary(doc, target, decisions[:-1], 'No row', reviews=reviews)['can_submit'], 'missing source decision is blocked')
    draft_reviews = deepcopy(reviews)
    next(r for r in draft_reviews if r['id'] == 'T1004')['annotation_rows'] = [{'techniqueID': 'T9999', 'comment': 'bad draft'}]
    invalid_draft = build_summary(doc, target, decisions, 'Draft', reviews=draft_reviews)
    check(any(i.get('identity') == 'T1004' for i in invalid_draft['issues']), 'invalid independent draft returns to its owning technique')
    for value, fragment in [([], 'refer'), ({'stale:key': ''}, 'refer'), ({'added:T1004': None}, '4096'), ({'added:T1004': 'x' * 4097}, '4096')]:
        bad(lambda v=value: validate_reasons(preview, v), fragment, 'invalid skip reason input rejected')
    check(validate_reasons(preview, {'added:T1004': '字' * 4096})['added:T1004'] == '字' * 4096, 'Unicode reason limit counts characters')
    check(validate_reasons(preview, None) == {}, 'legacy callers default to optional empty reasons')
    toggled = deepcopy(decisions); toggled[parent_index]['action'] = 'Drop'
    toggled_report = build_summary(doc, target, toggled, 'Drop again', reviews=reviews, skip_reasons=reasons)
    check(next(s for s in toggled_report['skips'] if s.get('source_index') == parent_index)['reason'] == 'Inactive Copy reason draft',
          'a retained inactive reason reappears when source changes back to Drop')
    bad(lambda: migrate_layer(doc, target, decisions, 'Invalid reasons', reviews=reviews, skip_reasons={'stale': ''}), 'refer', 'backend independently validates reasons before creating result')
    check(doc.content_token() == before, 'summary and invalid submission never mutate source')
    log('[Summary Audit 3/7] Conflict readiness, fingerprints, empty output and snapshot binding', 2, 7)
    fanin = deepcopy(decisions)
    fanin[parent_index].update(target_id='T1000', target_scope='execution')
    fanin[child_index].update(target_id='T1000', target_scope='execution')
    plan = migration_plan(doc, target, fanin, reviews=reviews)
    resolutions = resolutions_for(plan)
    unresolved = build_summary(doc, target, fanin, 'Conflict', reviews=reviews)
    check(unresolved['conflicts'] > 0 and not unresolved['can_submit'], 'unresolved field conflicts block submission')
    check(all(i['kind'] == 'conflict' and 'source_index' in i for i in unresolved['issues']), 'each unresolved field retains source navigation information')
    resolved = build_summary(doc, target, fanin, 'Conflict', reviews=reviews, resolutions=resolutions)
    check(resolved['can_submit'] and resolved['resolved_conflicts'] == len(plan['conflicts']), 'fully reviewed resolutions produce ready output counts')
    stale = deepcopy(resolutions); stale[0]['fingerprint'] = 'old'
    check(not build_summary(doc, target, fanin, 'Conflict', reviews=reviews, resolutions=stale)['can_submit'], 'stale fingerprint blocked in final summary')
    duplicate = resolutions + [deepcopy(resolutions[0])]
    check(not build_summary(doc, target, fanin, 'Conflict', reviews=reviews, resolutions=duplicate)['can_submit'], 'duplicate field resolution blocked')
    wrong = deepcopy(resolutions); wrong[0].update(action='custom', value='invalid field type')
    check(not build_summary(doc, target, fanin, 'Conflict', reviews=reviews, resolutions=wrong)['can_submit'], 'invalid custom resolved field type blocked before submit')
    unreviewed = deepcopy(resolutions); unreviewed[0]['reviewed'] = False
    check(not build_summary(doc, target, fanin, 'Conflict', reviews=reviews, resolutions=unreviewed)['can_submit'], 'unacknowledged field resolution remains unfinished')
    drops = [{**d, 'action': 'Drop'} for d in decisions]
    empty = build_summary(doc, target, drops, 'Empty', reviews=reviews)
    check(empty['can_submit'] and empty['output_rows'] == 0 and empty['selected_techniques'] == 0, 'all-Drop result is valid and explicitly empty')
    same = TTPDocument('No annotations', source)
    same_preview = upgrade_preview(same, source)
    zeros = build_summary(same, source, [], 'Same version', reviews=reviewed(same_preview))
    check(zeros['can_submit'] and zeros['output_rows'] == 0, 'zero source-row plan can complete')
    check(sum(c['state'] == 'Empty' for c in zeros['categories']) == 4, 'empty categories are explicit rather than incomplete')
    check(report['input_token'] == summary_token(doc, target, decisions, reviews, None, '  Ready.json  '), 'input fingerprint binds immutable plan and raw output name')
    for ds, rs, nm in [(pending_decisions, reviews, '  Ready.json  '), (decisions, pending_reviews, '  Ready.json  '), (decisions, reviews, 'Renamed')]:
        check(summary_token(doc, target, ds, rs, None, nm) != report['input_token'], 'changed mapping/review/name invalidates summary fingerprint')
    log('[Summary Audit 4/7] Native summary, reasons, cancellation and return navigation', 3, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    manager = language_manager(); manager.set_language('en')
    parent = QtWidgets.QWidget(); parent.operation_report = log
    def native():
        dialog = UpgradeDialog(DATA, doc, [], parent)
        dialog.loaded((target, preview)); dialog.set_review_enabled(True)
        for index, decision in enumerate(decisions):
            control = dialog.controls[index]
            control['action'].setCurrentText(decision['action'])
            control['scope'].setCurrentIndex(control['scope'].findData(decision['target_scope']))
        dialog.show()
        return dialog
    dialog = native()
    dialog.pending_only.setChecked(True)
    dialog.review_panel.category.setCurrentIndex(1)
    dialog.review_panel.annotated_only.setChecked(True)
    def pending_ui(editor):
        check(not editor.submit.isEnabled() and editor.unfinished.rowCount() > 0, 'native summary blocks incomplete submission and lists pending checks')
        check(editor.categories.rowCount() == 5, 'native summary always shows all five categories')
        check(editor.report_data['total'] == 7, 'native summary retains complete denominator while every current review row is filtered out')
        check(editor.grab().save(str(OUT / 'pending-en.png')), 'English incomplete summary screenshot saved')
        editor.first.click()
    state = schedule_dialog(UpgradeSummaryDialog, pending_ui)
    dialog.create_button.click()
    check(dialog.summary_preview_pending and not dialog.create_button.isEnabled(), 'native summary worker locks submission controls')
    wait(lambda: state['done']); check(not state['errors'], 'native create button routes through final summary: ' + repr(state['errors']))
    wait(lambda: not dialog.summary_preview_pending)
    check(dialog.review_tabs.currentIndex() == 0, 'return-first goes back to technique review')
    dialog.mark_reviewed()
    dialog.skip_reasons = deepcopy(reasons)
    complete = build_summary(dialog.document, target, dialog.capture_decisions(), dialog.name.text(), reviews=dialog.review_panel.decisions(),
                             resolutions=dialog.conflict_resolutions, skip_reasons=dialog.skip_reasons)
    check(complete['can_submit'], 'native acknowledged decisions produce a ready summary')
    editor = UpgradeSummaryDialog(dialog, complete); editor.show(); app.processEvents()
    check(editor.submit.isEnabled() and not editor.first.isEnabled(), 'ready summary enables submit with no unfinished return action')
    check(dialog.name.text() in editor.overview.text() and doc.name in editor.overview.text(), 'native final summary identifies result and original document names')
    index = next(i for i, s in enumerate(complete['skips']) if s.get('source_index') == drop_index)
    editor.skips.setCurrentCell(index, 0); editor.reason_editor.setPlainText('Cancelled reason'); editor.apply_reason.click(); editor.reject()
    check(dialog.skip_reasons == reasons, 'cancelling reason editor preserves parent reason drafts')
    limit_editor = UpgradeSummaryDialog(dialog, complete)
    limit_editor.skips.item(index, 3).setText('x' * 4097)
    check(not limit_editor.submit.isEnabled() and bool(limit_editor.error.text()), 'oversize direct reason-cell edits disable native submission')
    limit_editor.skips.item(index, 3).setText('')
    check(limit_editor.submit.isEnabled(), 'clearing an oversize reason restores native submission readiness')
    limit_editor.reject()
    def edit_reasons(summary):
        summary.tabs.setCurrentIndex(1)
        summary.skips.selectAll()
        summary.reason_editor.setPlainText(reason)
        summary.apply_reason.click()
        check(all(summary.skips.item(i, 3).text() == reason for i in range(summary.skips.rowCount())), 'native reason editor applies multiline text to every highlighted skipped item')
        check(summary.grab().save(str(OUT / 'summary-en.png')), 'English final summary screenshot saved')
        manager.set_language('zh_TW'); app.processEvents()
        check(summary.windowTitle() == '升級最後摘要', 'summary title translates to Traditional Chinese')
        check(summary.grab().save(str(OUT / 'summary-zh.png')), 'Traditional Chinese summary screenshot saved')
        manager.set_language('en'); summary.back.click()
    state = schedule_dialog(UpgradeSummaryDialog, edit_reasons)
    dialog.open_summary(); wait(lambda: state['done'])
    check(not state['errors'], 'native Back preserves local reasons: ' + repr(state['errors']))
    check(all(dialog.skip_reasons[s['key']] == reason for s in complete['skips']), 'Back commits optional reason drafts without creating a document')
    check(dialog.result_document is None, 'return from summary never installs a result')
    dialog.pending_only.setChecked(True); dialog.review_panel.category.setCurrentIndex(1); dialog.review_panel.annotated_only.setChecked(True)
    dialog.return_to_unfinished({'kind': 'mapping', 'source_index': child_index})
    check(not dialog.pending_only.isChecked() and not dialog.review_panel.annotated_only.isChecked() and dialog.review_panel.category.currentIndex() == 0,
          'return clears every visibility filter including reviewed-row hiding')
    check(dialog.review_tabs.currentIndex() == 1 and dialog.table.currentRow() == child_index and not dialog.table.isRowHidden(child_index), 'return reveals and focuses exact hidden mapping row')
    dialog.return_to_unfinished({'kind': 'technique', 'identity': 'T1004'})
    check(dialog.review_tabs.currentIndex() == 0 and dialog.review_panel.items[dialog.review_panel.table.currentRow()]['id'] == 'T1004', 'return reveals exact Added technique')
    dialog.return_to_unfinished({'kind': 'name'})
    check(dialog.name.selectedText() == dialog.name.text(), 'return to invalid output name selects its complete text')
    dialog.mapping_targets[parent_index] = [{'target_id': 'T1000', 'target_scope': 'execution'}]
    dialog.mapping_targets[child_index] = [{'target_id': 'T1000', 'target_scope': 'execution'}]
    def inspect_conflict_focus(editor):
        check(editor.table.currentRow() == 0, 'unfinished conflict return focuses its exact destination field')
        editor.reject()
    state = schedule_dialog(ConflictResolutionDialog, inspect_conflict_focus)
    conflict_issue = next(i for i in unresolved['issues'] if i['kind'] == 'conflict')
    dialog.return_to_unfinished(conflict_issue); wait(lambda: state['done'])
    check(not state['errors'], 'return to unfinished conflict opens current complete conflict review')
    dialog.mapping_targets.clear()
    log('[Summary Audit 5/7] Submission, stale summary, failure recovery and close safety', 4, 7)
    def stale_summary(summary):
        dialog.name.setText('Changed after preview')
        summary.submit.click()
    state = schedule_dialog(UpgradeSummaryDialog, stale_summary)
    dialog.open_summary(); wait(lambda: state['done'])
    check(not state['errors'] and dialog.result_document is None and 'inputs changed' in dialog.status.text(), 'stale summary cannot submit changed input even through programmatic mutation')
    state = schedule_dialog(UpgradeSummaryDialog, lambda d: d.submit.click())
    dialog.open_summary(); wait(lambda: state['done']); wait(lambda: dialog.result_document is not None)
    wait(lambda: not dialog.worker.isRunning())
    result = dialog.result_document
    completion = result.navigator_layer['x_ttp_studio_upgrade']['final_summary']
    check(completion['can_submit'] and not completion['issues'] and completion['result_name'] == 'Changed after preview', 'native Submit installs reviewed new document with final summary')
    check(all(s['reason'] == reason for s in completion['skips']), 'submitted final summary persists all edited reasons')
    check(next(d for d in result.navigator_layer['x_ttp_studio_upgrade']['decisions'] if d['action'] == 'Drop')['skip_reason'] == reason, 'Drop audit also records the source-bound reason')
    added_skips = [r for r in result.navigator_layer['x_ttp_studio_upgrade']['technique_reviews'] if r.get('action') == 'Skip added']
    check(len(added_skips) == 2 and all(r.get('skip_reason') == reason for r in added_skips), 'Added Skip audit records its reason')
    check(any(r['techniqueID'] == 'T1003' for r in result.navigator_layer['techniques']), 'skipping Added annotations does not discard incoming replacement mappings')
    failed = native(); failed.skip_reasons = {'stale': 'reason'}; failed.open_summary()
    wait(lambda: failed.worker and not failed.worker.isRunning()); wait(lambda: failed.create_button.isEnabled())
    check(not failed.summary_preview_pending and failed.status.text().startswith('Failed:'), 'failed summary planning unlocks controls for correction and retry')
    failed.reject()
    closed = native(); installed = []; closed.imported.connect(installed.append)
    closed.open_summary(); closed.reject(); wait(lambda: closed.worker and not closed.worker.isRunning())
    check(not installed and closed.result_document is None, 'closing during planning never opens summary or installs a late result')
    check(doc.content_token() == before, 'all native edit, navigation and submit paths preserve source content')
    log('[Summary Audit 6/7] Studio, session, Navigator and legacy API round trips', 5, 7)
    path = OUT / 'summary.studio.json'; save_studio(result, path, log)
    reopened = open_studio(CACHE, path, log)
    check(reopened.navigator_layer == result.navigator_layer, 'Studio round trip preserves entire final summary and audit')
    check(reopened.migration_archives == result.migration_archives, 'Studio round trip retains immutable original archive')
    path = OUT / 'session.json'; write_session(session_payload([result], 0, {}), path, log)
    check(read_session(CACHE, path, log)['documents'][0].content_token() == result.content_token(), 'session restores final summary and reasons exactly')
    path = OUT / 'summary.navigator.json'; export_layers([result], path, log)
    exported = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(exported, list): exported = exported[0]
    check(exported['x_ttp_studio_upgrade']['final_summary'] == completion, 'Navigator JSON preserves final summary and Unicode reasons')
    legacy = migrate_layer(doc, target, decisions, 'Legacy', reviews=reviews)
    check(all(s['reason'] == '' for s in legacy.navigator_layer['x_ttp_studio_upgrade']['final_summary']['skips']), 'legacy callers get complete audit with optional blank skip reasons')
    check(legacy.navigator_layer['x_ttp_studio_upgrade']['review_schema'] == 2, 'optional final summary extension preserves review schema compatibility')
    log('[Summary Audit 7/7] Publish report and release native widgets', 6, 7)
    (OUT / 'audit.json').write_text(json.dumps({'passed': True, 'count': len(CHECKS), 'checks': CHECKS}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log(f'[Summary Audit] PASS: {len(CHECKS)} checks', 7, 7)
    parent.close()


if __name__ == '__main__':
    main()
