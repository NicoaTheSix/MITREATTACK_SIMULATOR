"""NAV-022 readable comparison, target editing and archive-link audit. Workflow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request
import json

from PySide6 import QtCore, QtWidgets
from audit_advanced_navigator import fixture
from audit_upgrade_review import wait, mapped, reviewed
from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from custom_sources import load_custom
from layer_upgrade import upgrade_preview, migrate_layer
from localization import language_manager
from main import configure_application
from navigator_dialogs import AnnotationDialog
from navigator_integration import document_layer, update_annotation, export_layers
from source_dialogs import UpgradeDialog
from studio_files import save_studio, open_studio, write_session, read_session, session_payload
from ttp_documents import TTPDocument
from upgrade_content import version_page, checked_version_page, technique_record, content_html

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/attack'
OUT = ROOT / 'artifacts/upgrade-content'
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
    except (ValueError, HTTPError) as error:
        check(text in str(error), message)
    else:
        raise AssertionError(message)


def editor_action(action):
    errors = []
    def run():
        dialog = next(w for w in QtWidgets.QApplication.topLevelWidgets() if isinstance(w, AnnotationDialog) and w.isVisible())
        try:
            action(dialog)
        except Exception as error:
            errors.append(error)
            dialog.reject()
    QtCore.QTimer.singleShot(50, run)
    return errors


def main():
    log('Input official dataset directory: ' + str(DATA.resolve()))
    log('Output fixtures, cache, screenshots and report: ' + str(OUT.resolve()))
    OUT.mkdir(parents=True, exist_ok=True)
    log('[Content Audit 1/7] Prepare exact source and target snapshots', 0, 7)
    catalogs = []
    for newer in (False, True):
        payload = fixture('19.3' if newer else '19.2', newer)
        parent = next(o for o in payload['objects'] if o.get('type') == 'attack-pattern' and external_id(o) == 'T1000')
        parent['description'] = 'New description and scope' if newer else 'Original full description <img src="https://example.org/not-loaded">'
        parent['x_audit_extension'] = {'retained': ['Complete field', 123]}
        path = OUT / ('target.json' if newer else 'source.json')
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        catalogs.append(load_custom(CACHE, str(path.resolve()), '19.2', log)['catalog'])
    source, target = catalogs
    ids = {external_id(o): k for k, o in source.records.items()}
    doc = TTPDocument('Full content source', source, selected={ids['T1000']})
    update_annotation(doc, ids['T1000'], '', 'Original comment', 9, '#112233',
                      [{'label': 'Old link', 'url': 'https://example.org/old', 'extra': 'keep'}],
                      [{'name': 'Owner', 'value': 'Original', 'extra': 42}])
    doc.navigator_layer['techniques'][0]['x_custom_annotation'] = {'preserved': True}
    update_annotation(doc, ids['T1000.001'], 'execution', 'Scoped child', 2, '')
    update_annotation(doc, ids['T1002'], '', 'Revoked source annotation', 3, '')
    before = doc.fingerprint()
    preview = upgrade_preview(doc, target, log)
    decisions, reviews = mapped(preview), reviewed(preview)
    index = next(i for i, row in enumerate(preview['rows']) if row['source_id'] == 'T1000')
    legacy_index = next(i for i, row in enumerate(preview['rows']) if row['source_id'] == 'T1002')
    log('[Content Audit 2/7] Readable complete content, escaping and inactive records', 1, 7)
    text = content_html(source, 'T1000', [preview['rows'][index]['annotation']])
    check('Original full description' in text and 'Complete field' in text and 'kill_chain_phases' in text, 'viewer includes readable description and complete STIX extension/mappings')
    check('&lt;img' in text and '<img' not in text, 'catalog HTML is escaped instead of fetching remote images')
    check('Original comment' in text and 'x_custom_annotation' in text and 'Old link' in text, 'complete original annotation including extensions is shown')
    check(technique_record(target, 'T1002').get('revoked'), 'inactive raw target record remains inspectable')
    check('No technique record' in content_html(target, 'T9999', []), 'missing records have explicit local empty state')
    check(not version_page(source, 'T1000'), 'custom source never claims an official version page')
    official_source = replace(source, dataset_id='', custom_source='')
    official_target = replace(target, dataset_id='', custom_source='')
    check(version_page(official_source, 'T1000') == 'https://attack.mitre.org/versions/v19/techniques/T1000/', 'official page uses catalog major archive rather than latest')
    check(not version_page(official_source, 'T9999'), 'missing record has no invented version-page link')
    log('[Content Audit 3/7] Reviewed annotation patches, clearing, validation and preservation', 2, 7)
    patched = deepcopy(decisions)
    patched[index]['annotation_patch'] = {'comment': 'Revised evidence', 'score': 0, 'color': '#abcdef', 'enabled': False,
        'links': [{'label': 'New evidence', 'url': 'https://example.org/new'}], 'metadata': [{'name': 'Owner', 'value': 'Reviewer'}]}
    result = migrate_layer(doc, target, patched, 'Edited migration', log, reviews=reviews)
    row = next(r for r in result.navigator_layer['techniques'] if r['techniqueID'] == 'T1000')
    for field, value in patched[index]['annotation_patch'].items():
        check(row[field] == value, 'applied target edit: ' + field)
    check(row['x_custom_annotation'] == {'preserved': True}, 'editing supported fields preserves unrelated annotation extensions')
    check(result.selected == doc.selected, 'target annotation editing preserves source selection')
    check(result.navigator_layer['x_ttp_studio_upgrade']['decisions'][index]['annotation_patch'] == patched[index]['annotation_patch'], 'exact target patch is recorded in migration audit')
    check(doc.fingerprint() == before and result.migration_archives[-1]['layer'] == document_layer(doc), 'source and complete archived annotations remain immutable')
    cleared = deepcopy(patched)
    cleared[index]['annotation_patch'] = {'comment': '', 'score': None, 'color': '', 'links': [], 'metadata': []}
    cleared_result = migrate_layer(doc, target, cleared, 'Cleared annotations', reviews=reviews)
    row = next(r for r in cleared_result.navigator_layer['techniques'] if r['techniqueID'] == 'T1000')
    check('score' not in row and not row['color'] and not row['comment'] and not row['links'] and not row['metadata'], 'explicit clear removes score and empties comment/color/structured fields')
    invalid = deepcopy(patched)
    invalid[index]['annotation_patch']['techniqueID'] = 'T1001'
    bad(lambda: migrate_layer(doc, target, invalid, 'Invalid', reviews=reviews), 'only comment', 'patch cannot change identity/scope or inject other layer fields')
    invalid = deepcopy(patched)
    invalid[index]['annotation_patch']['score'] = float('nan')
    bad(lambda: migrate_layer(doc, target, invalid, 'Invalid', reviews=reviews), 'finite', 'nonfinite edited score is rejected')
    invalid = deepcopy(patched)
    invalid[index]['annotation_patch']['links'] = [{'label': 'Bad', 'url': 'javascript:alert(1)'}]
    bad(lambda: migrate_layer(doc, target, invalid, 'Invalid', reviews=reviews), 'HTTP', 'invalid edited link rejected before result installation')
    remapped = deepcopy(patched)
    remapped[legacy_index]['annotation_patch'] = {'comment': 'Replacement reviewed', 'score': 8}
    replaced = migrate_layer(doc, target, remapped, 'Replacement edit', reviews=reviews)
    check(any(r['techniqueID'] == 'T1003' and r.get('comment') == 'Replacement reviewed' for r in replaced.navigator_layer['techniques']), 'replacement target annotation can be revised during review')
    log('[Content Audit 4/7] Native paired panes, source-row editor, cancel and unannotated targets', 3, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    manager = language_manager()
    manager.set_language('en')
    parent = QtWidgets.QWidget()
    parent.operation_report = log
    dialog = UpgradeDialog(DATA, doc, [TTPDocument('Target', target)], parent)
    dialog.loaded((target, preview))
    dialog.show()
    dialog.review_tabs.setCurrentIndex(1)
    dialog.table.setCurrentCell(index, 0)
    dialog.show_changes(index)
    comparison = dialog.comparison
    check('Original full description' in comparison.browsers[0].toPlainText() and 'New description' in comparison.browsers[1].toPlainText(), 'native source/target panes show different full descriptions side by side')
    check('Alpha changed' in comparison.browsers[1].toPlainText(), 'target renamed technique is visible')
    check(all(not button.isEnabled() for button in comparison.page_buttons), 'custom dataset version-page buttons are disabled')
    def edit(editor):
        check(not editor.scope.isEnabled() and not editor.include.isVisible(), 'row editor locks mapped scope and does not alter inclusion')
        editor.comment.setPlainText('Native reviewed target')
        editor.score.setText('1.5')
        editor.color.setText('#445566')
        editor.enabled.setChecked(False)
        editor.links.load([{'label': 'Native link', 'url': 'https://example.org/native'}])
        editor.metadata.load([{'name': 'Case', 'value': 'Native review'}])
        editor.save()
    errors = editor_action(edit)
    comparison.edit_target()
    check(not errors, 'native annotation editor saved successfully')
    check(dialog.annotation_edits[index]['comment'] == 'Native reviewed target', 'native row edit stored as independent draft')
    check('Native reviewed target' in comparison.browsers[1].toPlainText() and 'Original comment' in comparison.browsers[0].toPlainText(), 'edited target refreshes without altering before pane')
    check(not dialog.review_panel.states['T1000']['reviewed'] and not dialog.controls[index]['reviewed'].isChecked(), 'editing clears both source-row and technique acknowledgement')
    saved_patch = deepcopy(dialog.annotation_edits[index])
    errors = editor_action(lambda editor: (editor.comment.setPlainText('Cancelled draft'), editor.reject()))
    comparison.edit_target()
    check(not errors and dialog.annotation_edits[index] == saved_patch, 'cancelling row editor preserves previous target draft')
    control = dialog.controls[index]
    control['technique'].setCurrentIndex(control['technique'].findData('T1001'))
    check(dialog.annotation_edits[index] == saved_patch and 'Beta' in comparison.browsers[1].toPlainText(), 'target edits follow explicit remapping and pane reflects new target')
    control['technique'].setCurrentIndex(control['technique'].findData('T1000'))
    child_index = next(i for i, row in enumerate(preview['rows']) if row['source_id'] == 'T1000.001')
    dialog.show_changes(child_index)
    check('execution' in comparison.browsers[0].toPlainText() and 'initial-access' in comparison.browsers[1].toPlainText(), 'tactic changes visible in the paired full records')
    check(not comparison.edit.isEnabled(), 'removed tactic requires a valid mapping before editing')
    dialog.controls[child_index]['scope'].setCurrentIndex(dialog.controls[child_index]['scope'].findData('initial-access'))
    check(comparison.edit.isEnabled(), 'valid remapping enables target annotation editor')
    item_index = next(i for i, item in enumerate(dialog.review_panel.items) if item['id'] == 'T1001')
    dialog.review_tabs.setCurrentIndex(0)
    dialog.review_panel.table.setCurrentCell(item_index, 0)
    errors = editor_action(lambda editor: (editor.comment.setPlainText('New existing-target annotation'), editor.save()))
    dialog.review_panel.edit_target()
    check(not errors and 'T1001' in dialog.review_panel.drafts, 'previously unannotated existing target can be annotated during review')
    check(not dialog.review_panel.drafts['T1001'].selected, 'new existing-target annotation does not add a selection')
    dialog.review_tabs.setCurrentIndex(1)
    dialog.table.setCurrentCell(index, 0)
    dialog.show_changes(index)
    dialog.mark_reviewed()
    check(all(r['reviewed'] for r in dialog.review_panel.decisions()), 'edited items can be explicitly reviewed again')
    app.processEvents()
    check(dialog.grab().save(str(OUT / 'comparison-en.png')), 'English paired-content screenshot saved')
    manager.set_language('zh_TW')
    check(dialog.content_tabs.tabText(0) == '內容並排比較', 'paired-view tab translates to Traditional Chinese')
    check(dialog.grab().save(str(OUT / 'comparison-zh.png')), 'Traditional Chinese paired-content screenshot saved')
    manager.set_language('en')
    dialog.create()
    wait(lambda: dialog.worker and not dialog.worker.isRunning())
    check(dialog.result_document is not None, 'native reviewed edits produce migrated document: ' + dialog.status.text())
    native = dialog.result_document
    check(any(r.get('comment') == 'Native reviewed target' for r in native.navigator_layer['techniques']), 'native migrated result contains edited source-row annotation')
    check(any(r.get('comment') == 'New existing-target annotation' for r in native.navigator_layer['techniques']), 'native migrated result contains new existing-target annotation')
    check(doc.fingerprint() == before, 'native edits and creation preserve the original document')
    log('[Content Audit 5/7] Version archive verification, missing pages and safe browser dispatch', 4, 7)
    url = version_page(official_source, 'T1000')
    class Response:
        status = 200
        def __init__(self, final=url): self.final = final
        def geturl(self): return self.final
        def __enter__(self): return self
        def __exit__(self, *_): pass
    class Opener:
        def __init__(self, final=url): self.final = final
        def open(self, request, timeout): return Response(self.final)
    with patch('upgrade_content.build_opener', return_value=Opener()):
        check(checked_version_page(url, log) == url, 'valid archive verified without switching version')
    for wrong in ('https://attack.mitre.org/techniques/T1000/', url.replace('v19', 'v20'), url.replace('T1000', 'T1001')):
        with patch('upgrade_content.build_opener', return_value=Opener(wrong)):
            bad(lambda: checked_version_page(url, log), 'unavailable', 'unexpected final version/identity is rejected: ' + wrong)
    handlers = []
    with patch('upgrade_content.build_opener', side_effect=lambda handler: (handlers.append(handler), Opener())[1]):
        checked_version_page(url, log)
    bad(lambda: handlers[0].redirect_request(Request(url), None, 302, '', {}, 'https://attack.mitre.org/techniques/T1000/'),
        'redirected away', 'redirect is blocked before requesting the latest page')
    for invalid_url in ('https://example.org/versions/v19/techniques/T1000/', url + '?latest=1', 'file:///tmp/example'):
        bad(lambda u=invalid_url: checked_version_page(u, log), 'version-specific', 'only official archive URLs accepted')
    page_doc = TTPDocument('Archive links', official_source)
    pages = UpgradeDialog(DATA, page_doc, [], parent)
    pages.loaded((official_target, upgrade_preview(page_doc, official_target)))
    pages.comparison.show_item('T1000')
    check(all(button.isEnabled() for button in pages.comparison.page_buttons), 'official source and target each have a version archive button')
    with patch('upgrade_content.build_opener') as opener, patch('upgrade_comparison.QtGui.QDesktopServices.openUrl') as opened:
        opener.return_value.open.side_effect = HTTPError(url, 404, 'Missing archive', {}, None)
        pages.comparison.open_page(0)
        wait(lambda: pages.worker and not pages.worker.isRunning())
        wait(lambda: pages.comparison.isEnabled())
        check(not opened.called and pages.status.text().startswith('Failed:'), 'missing old page reports failure and never opens latest')
    with patch('upgrade_content.build_opener', return_value=Opener()), patch('upgrade_comparison.QtGui.QDesktopServices.openUrl', return_value=True) as opened:
        pages.comparison.open_page(0)
        wait(lambda: pages.worker and not pages.worker.isRunning())
        wait(lambda: opened.called)
        check(opened.call_args.args[0].toString() == url, 'verified button opens exactly the requested archive in browser')
    pages.closing = True
    with patch('upgrade_comparison.QtGui.QDesktopServices.openUrl') as opened:
        pages.comparison.open_verified(url)
        check(not opened.called, 'completion after closing cannot launch a browser')
    pages.reject()
    log('[Content Audit 6/7] Save/reopen, session and Navigator round trips', 5, 7)
    saved = OUT / 'edited.studio.json'
    save_studio(native, saved, log)
    reopened = open_studio(CACHE, saved, log)
    check(reopened.navigator_layer == native.navigator_layer and reopened.migration_archives == native.migration_archives, 'Studio preserves revised annotations, audit and original archive')
    session = OUT / 'session.json'
    write_session(session_payload([native], 0, {}), session, log)
    check(read_session(CACHE, session, log)['documents'][0].content_token() == native.content_token(), 'session restores edited target and review provenance')
    export_layers([native], OUT / 'edited.navigator.json', log)
    exported = json.loads((OUT / 'edited.navigator.json').read_text(encoding='utf-8'))
    if isinstance(exported, list): exported = exported[0]
    check(any(r.get('comment') == 'Native reviewed target' for r in exported['techniques']), 'Navigator export includes revised target annotation')
    check(any('annotation_patch' in r for r in exported['x_ttp_studio_upgrade']['decisions']), 'Navigator export retains exact edited-field audit')
    log('[Content Audit 7/7] Historical snapshot page identity and publish report', 6, 7)
    historical = load_catalog(DATA, log, snapshot_pointer(DATA, '11.3'))
    check(version_page(historical, 'T1053.005') == 'https://attack.mitre.org/versions/v11/techniques/T1053/005/', 'real historical sub-technique uses v11 archive and split sub-ID')
    check('11.3' in content_html(historical, 'T1053.005', []) and 'Scheduled Task' in content_html(historical, 'T1053.005', []), 'exact local v11.3 record remains inspectable independently of website availability')
    (OUT / 'audit.json').write_text(json.dumps({'passed': True, 'count': len(CHECKS), 'checks': CHECKS,
        'network': 'mocked archive responses; no live third-party requests'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log(f'[Content Audit] PASS: {len(CHECKS)} checks', 7, 7)
    parent.close()


if __name__ == '__main__':
    main()
