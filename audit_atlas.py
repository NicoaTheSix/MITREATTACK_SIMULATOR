"""Exercise ATLAS + ATT&CK Workplace, matrix lifecycle and saves. Flow: README.md."""
import csv
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import time
from unittest.mock import patch

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from atlas_catalog import DOMAIN
from atlas_matrix import KEY, TACTIC
from attack_catalog import external_id
from layer_analysis import snapshot_document
from main import MainWindow, ROLE_ID, configure_application
from localization import language_manager
from navigator_integration import update_annotation
from studio_files import save_studio, open_studio, StudioReader, session_payload, write_session, read_session
from ttp_documents import document_payload, csv_content

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts' / 'atlas-workplace'
CHECKS = []


def log(message, *args):
    print(message, flush=True)


def check(value, label):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)
    print('[Check] ' + label, flush=True)


def wait(condition, label):
    deadline = time.monotonic() + 60
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError(label)
        QtWidgets.QApplication.processEvents()
        time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def tree_item(tree, key):
    iterator = QtWidgets.QTreeWidgetItemIterator(tree)
    while iterator.value():
        item = iterator.value()
        if item.data(0, KEY) == key:
            return item
        iterator += 1
    raise AssertionError('ATLAS tree item not found: ' + key)


def audit_multiselect(window):
    """Exercise native modifier clicks and destructive-menu scope, not just selection flags."""
    doc = window.current_document
    snapshot = snapshot_document(doc)
    attack_keys = sorted(doc.catalog.records, key=lambda k:external_id(doc.catalog.records[k]))[:6]
    atlas_keys = sorted(doc.atlas_document.catalog.records, key=lambda k:external_id(doc.atlas_document.catalog.records[k]))[:6]
    doc.selected = set(attack_keys)
    window.selected = set(attack_keys)
    doc.atlas_document.selected = set(atlas_keys)
    for owner, keys in ((doc,attack_keys),(doc.atlas_document,atlas_keys)):
        owner.selection_preferences.update(with_family=True,visible_only=True)
        for key in keys:
            update_annotation(owner,key,'','Retain multi-select note '+external_id(owner.catalog.records[key]),2.75,'#abcdef')
    window.refresh_selection()
    window.open_matrix()
    wait(lambda:not window.matrix_view.building,'matrix for multi-select')
    for framework, listing, role, owner, other, menu_attr in [
            ('ATT&CK',window.selection_list,ROLE_ID,doc,doc.atlas_document,'selected_context_menu'),
            ('ATLAS',window.atlas_selection_list,KEY,doc.atlas_document,doc,'workplace_context_menu')]:
        window.switch_category('Workplace')
        QtWidgets.QApplication.processEvents()
        included = set(owner.selected)
        others = set(other.selected)
        annotations = deepcopy(owner.navigator_layer)
        other_annotations = deepcopy(other.navigator_layer)
        token = doc.content_token()
        def marked():
            return {item.data(role) for item in listing.selectedItems()}
        def click(row, modifiers=QtCore.Qt.KeyboardModifier.NoModifier):
            item = listing.item(row)
            listing.scrollToItem(item)
            QtWidgets.QApplication.processEvents()
            QtTest.QTest.mouseClick(listing.viewport(),QtCore.Qt.MouseButton.LeftButton,modifiers,listing.visualItemRect(item).center())
            QtWidgets.QApplication.processEvents()
        def menu_for(row):
            item = listing.item(row)
            listing.scrollToItem(item)
            QtWidgets.QApplication.processEvents()
            point = listing.visualItemRect(item).center()
            QtTest.QTest.mouseClick(listing.viewport(),QtCore.Qt.MouseButton.RightButton,pos=point)
            if QtWidgets.QApplication.activePopupWidget() is None:
                event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse,point,listing.viewport().mapToGlobal(point))
                QtWidgets.QApplication.sendEvent(listing.viewport(),event)
            return getattr(window,menu_attr)
        first, third = listing.item(0).data(role), listing.item(2).data(role)
        click(0)
        click(2,QtCore.Qt.KeyboardModifier.ControlModifier)
        check(marked()=={first,third},framework+' Ctrl-click selects disjoint rows')
        click(2,QtCore.Qt.KeyboardModifier.ControlModifier)
        check(marked()=={first},framework+' Ctrl-click toggles a highlighted row off')
        click(2)
        click(4,QtCore.Qt.KeyboardModifier.ShiftModifier)
        check(marked()=={listing.item(i).data(role) for i in range(2,5)},framework+' Shift-click selects a contiguous range')
        check(doc.content_token()==token and window.workspace.currentWidget() is window.tabs,
              framework+' modifier clicks do not change inclusion, annotations or page')
        click(0)
        click(2,QtCore.Qt.KeyboardModifier.ControlModifier)
        window.refresh_selection()
        check(marked()=={first,third},framework+' data refresh preserves the highlighted set')
        menu=menu_for(0)
        check(marked()=={first,third},framework+' right-click within a multi-selection preserves all highlighted rows')
        remove=next(action for action in menu.actions() if action.text()=='Remove selected TTPs')
        check(remove.isEnabled(),framework+' context menu offers batch deselection')
        menu.close()
        QtWidgets.QApplication.processEvents()
        check(doc.content_token()==token,framework+' cancelling the removal menu preserves all data')
        menu=menu_for(1)
        check(marked()=={listing.item(1).data(role)},framework+' right-click outside the highlighted set targets only that row')
        menu.close()
        QtWidgets.QApplication.processEvents()
        click(0)
        click(2,QtCore.Qt.KeyboardModifier.ControlModifier)
        menu=menu_for(0)
        remove=next(action for action in menu.actions() if action.text()=='Remove selected TTPs')
        remove.trigger()
        menu.close()
        QtWidgets.QApplication.processEvents()
        check(owner.selected==included-{first,third},framework+' removes exactly the highlighted TTPs despite family/visible-only preferences')
        check(other.selected==others and other.navigator_layer==other_annotations,framework+' batch removal leaves the other framework intact')
        check(owner.navigator_layer==annotations,framework+' batch removal retains every annotation including removed rows')
        check(listing.count()==len(included)-2 and not marked(),framework+' removed rows disappear without highlighting unrelated survivors')
        check(window.workspace.currentWidget() is window.tabs,framework+' batch removal stays in Selected Techniques')
        current_matrix = window.matrix_view if framework=='ATT&CK' else window.atlas_matrix
        current_selected = current_matrix.selected if framework=='ATT&CK' else current_matrix.document.selected
        check(current_selected==owner.selected,framework+' matrix selection synchronizes with batch removal')
        if framework=='ATT&CK':
            window.show_selected_context_menu(QtCore.QPoint(-1,-1))
        else:
            window.atlas_selected_menu(QtCore.QPoint(-1,-1))
        menu=getattr(window,menu_attr)
        check(not next(action for action in menu.actions() if action.text()=='Remove selected TTPs').isEnabled(),
              framework+' removal is disabled when no rows are highlighted')
        menu.close()
        owner.selected.add(first)
        if framework=='ATT&CK':
            window.selected=set(owner.selected)
        window.refresh_selection()
        check(owner.navigator_layer==annotations,framework+' reselecting a removed TTP retains its original annotation')
    doc.selected=set(snapshot.selected)
    window.selected=set(snapshot.selected)
    doc.selection_scopes=deepcopy(snapshot.selection_scopes)
    doc.selection_preferences=dict(snapshot.selection_preferences)
    doc.navigator_layer=deepcopy(snapshot.navigator_layer)
    doc.atlas_document=snapshot.atlas_document
    window.refresh_selection()


def main():
    print(f'Input directory: {(ROOT / "data").resolve()}', flush=True)
    print(f'Output directory: {OUT.resolve()}', flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    print('[ATLAS audit 1/5] Loading isolated Workplace', flush=True)
    window = MainWindow(ROOT / 'data' / 'attack', settings_path=OUT/'settings.ini', session_path=None)
    window.resize(1700, 1100)
    window.show()
    wait(lambda:window.loaded_ok and window.atlas_catalog is not None, 'catalogs')
    catalog = window.atlas_catalog
    check((len(catalog.tactics),len(catalog.records),len(catalog.parents)) == (16,208,88), 'official ATLAS counts')
    check(list(window.navigation_buttons)[0] == 'Workplace', 'Workplace is the top navigation entry')
    for name in ('Workplace','ATLAS TTP','ATLAS Mitigations','ATLAS Case Studies'):
        check(not window.navigation_buttons[name].icon().isNull(), name + ' icon loads')
    check(window.tabs.indexOf(window.matrix_view) != window.tabs.indexOf(window.atlas_matrix), 'matrix views are peer tabs')
    attack_key = next(iter(window.catalog.records))
    window.choose_technique_occurrence(attack_key, True)
    key = next(k for k,v in catalog.records.items() if external_id(v)=='AML.T0000.001')
    print('[ATLAS audit 2/5] Matrix selection, groups, close/reopen and navigation', flush=True)
    window.open_atlas_matrix()
    item = next(item for tree in window.atlas_matrix.columns if (item := tree_item_safe(tree,key)))
    item.setCheckState(0, QtCore.Qt.CheckState.Checked)
    doc = window.current_document
    check(key in doc.atlas_document.selected and attack_key in doc.selected, 'matrix checkbox preserves independent ATT&CK + ATLAS selections')
    check(window.atlas_selection_list.count()==1 and window.selection_list.count()==1, 'Workplace has two populated selection lists')
    for listing, role, target, menu_attr in [(window.selection_list,ROLE_ID,attack_key,'selected_context_menu'),
                                            (window.atlas_selection_list,KEY,key,'workplace_context_menu')]:
        window.switch_category('Workplace')
        QtWidgets.QApplication.processEvents()
        row = listing.item(0)
        point = listing.visualItemRect(row).center()
        before_click = doc.content_token()
        QtTest.QTest.mouseClick(listing.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=point)
        QtWidgets.QApplication.processEvents()
        check(window.workspace.currentWidget() is window.tabs and window.tabs.currentIndex()==window.selection_tab_index,
              ('ATLAS' if role==KEY else 'ATT&CK')+' single click stays in Selected Techniques')
        check(listing.currentItem().data(role)==target and doc.content_token()==before_click,
              ('ATLAS' if role==KEY else 'ATT&CK')+' single click only selects a row')
        event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse,point,listing.viewport().mapToGlobal(point))
        QtWidgets.QApplication.sendEvent(listing.viewport(),event)
        menu = getattr(window,menu_attr)
        check(menu.isVisible() and window.workspace.currentWidget() is window.tabs,
              ('ATLAS' if role==KEY else 'ATT&CK')+' right click opens a menu without navigating')
        action = next(action for action in menu.actions() if action.text()=='View TTP information')
        action.trigger()
        menu.close()
        check(window.workspace.currentWidget() is window.details_page
              and external_id((catalog if role==KEY else window.catalog).records[target]) in window.details.toPlainText()
              and doc.content_token()==before_click,
              ('ATLAS' if role==KEY else 'ATT&CK')+' context action opens the correct TTP without editing data')
    audit_multiselect(window)
    window.switch_category('ATLAS TTP')
    tree_item(window.atlas_sidebar,key).setCheckState(0, QtCore.Qt.CheckState.Unchecked)
    check(key not in doc.atlas_document.selected and attack_key in doc.selected, 'ATLAS tree uncheck updates matrix and leaves ATT&CK intact')
    tree_item(window.atlas_sidebar,key).setCheckState(0, QtCore.Qt.CheckState.Checked)
    window.switch_category('Workplace')
    window.attack_selection_toggle.click()
    window.atlas_selection_toggle.click()
    check(window.selection_list.isHidden() and window.atlas_selection_list.isHidden(), 'both framework groups collapse independently')
    check(key in doc.atlas_document.selected and attack_key in doc.selected, 'group collapse retains both selections')
    window.attack_selection_toggle.click()
    window.atlas_selection_toggle.click()
    window.close_matrix_view('attack')
    window.close_matrix_view('atlas')
    check(not window.tabs.isTabVisible(window.matrix_tab_index) and not window.tabs.isTabVisible(window.atlas_matrix_tab_index), 'both matrices can close together')
    check(key in doc.atlas_document.selected and attack_key in doc.selected, 'closing matrices preserves both selections')
    window.show_selected_context_menu(QtCore.QPoint(-1,-1))
    menu = window.selected_context_menu
    check(any('ATLAS' in action.text() for action in menu.actions()), 'empty selected-list context menu offers matrix reopen')
    menu.close()
    window.open_atlas_matrix_button.click()
    check(window.tabs.isTabVisible(window.atlas_matrix_tab_index), 'small selected-panel button reopens ATLAS matrix')
    window.open_attack_matrix_button.click()
    wait(lambda:not window.matrix_view.building,'ATT&CK matrix')
    check(window.tabs.isTabVisible(window.matrix_tab_index), 'small selected-panel button reopens ATT&CK matrix')
    window.matrix_tab_menu(window.tabs.tabBar().tabRect(window.matrix_tab_index).center())
    window.workplace_context_menu.actions()[0].trigger()
    window.workplace_context_menu.close()
    check(not window.tabs.isTabVisible(window.matrix_tab_index) and attack_key in doc.selected,
          'actual matrix tab context action closes without changing selection')
    for category, kind, count in [('ATLAS Mitigations','course-of-action',40),('ATLAS Case Studies','x-atlas-case-study',73)]:
        window.switch_category(category)
        check(window.atlas_sidebar.topLevelItemCount()==count, category + ' library count')
        node = window.atlas_sidebar.topLevelItem(0)
        check(not node.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable, category + ' entries are references, not selectable techniques')
        window.show_atlas_record(node.data(0,KEY))
        text = window.details.toPlainText()
        check(external_id(catalog.objects_by_domain[DOMAIN][node.data(0,KEY)]) in text, category + ' detail renders')
        if kind=='x-atlas-case-study':
            check('S00' in text and 'Leads to:' in text and 'Exercise' in text, 'case steps, graph edges and native type are retained')
        check(window.atlas_source_bar.isVisible() and window.atlas_add_all_button.isEnabled(),
              category + ' shows Add all ATLAS TTPs above the content')
        source = catalog.objects_by_domain[DOMAIN][node.data(0,KEY)]
        relation = 'mitigates' if kind == 'course-of-action' else 'employs'
        ids = {edge['target'] for edge in source['x_atlas_relationships'][relation]}
        expected = {k for k,obj in catalog.records.items() if external_id(obj) in ids}
        atlas = doc.atlas_document
        selected_before, scopes_before = set(atlas.selected), deepcopy(atlas.selection_scopes)
        layer_before = deepcopy(atlas.navigator_layer)
        update_annotation(atlas,key,'','Preserve bulk-add annotation',1,'#ffffff')
        layer_with_note = deepcopy(atlas.navigator_layer)
        window.atlas_add_all_button.click()
        check(atlas.selected == selected_before | expected, category + ' real button adds exactly its official related techniques')
        check(doc.selected == {attack_key} and atlas.navigator_layer == layer_with_note,
              category + ' preserves ATT&CK selections and ATLAS annotations')
        check(window.atlas_selection_list.count() == len(atlas.selected) and window.atlas_matrix.document is atlas,
              category + ' updates selected list and matrix')
        token = doc.content_token()
        window.atlas_add_all_button.click()
        check(doc.content_token() == token, category + ' repeated bulk add is idempotent')
        unrelated = next(k for k in catalog.records if k not in expected and k != key)
        atlas.selected.add(unrelated)
        update_annotation(atlas,next(iter(expected)),'','Keep removed technique annotation',3,'#112233')
        annotated = deepcopy(atlas.navigator_layer)
        remaining = atlas.selected - expected
        window.update_document_labels()
        check(window.atlas_remove_all_button.isVisible() and window.atlas_remove_all_button.isEnabled(),
              category + ' shows Remove all ATLAS TTPs above the content')
        window.atlas_remove_all_button.click()
        check(atlas.selected == remaining and unrelated in atlas.selected and doc.selected == {attack_key},
              category + ' removes only its related ATLAS TTPs')
        check(atlas.navigator_layer == annotated, category + ' retains annotations on removed and remaining techniques')
        check(window.atlas_selection_list.count()==len(remaining)
              and all(item.checkState(0)==QtCore.Qt.CheckState.Unchecked
                      for tree in window.atlas_matrix.columns for target in expected
                      if (item := tree_item_safe(tree,target)) is not None),
              category + ' removal synchronizes selected list and matrix checkboxes')
        token = doc.content_token()
        window.atlas_remove_all_button.click()
        check(doc.content_token()==token,category + ' repeated removal is idempotent')
        window.atlas_add_all_button.click()
        check(atlas.selected==remaining|expected and atlas.navigator_layer==annotated,
              category + ' re-add restores selection with retained annotations')
        atlas.selected, atlas.selection_scopes, atlas.navigator_layer = selected_before, scopes_before, layer_before
        window.update_document_labels()
    repeated_case = next(obj for obj in catalog.objects_by_domain[DOMAIN].values() if external_id(obj)=='AML.CS0030')
    steps = repeated_case['x_atlas_relationships']['employs']
    window.show_atlas_record(repeated_case['id'])
    before_selected = set(doc.atlas_document.selected)
    window.atlas_add_all_button.click()
    expected = {k for k,obj in catalog.records.items() if external_id(obj) in {step['target'] for step in steps}}
    check(len(steps) > len(expected) and doc.atlas_document.selected == before_selected | expected,
          'case with repeated technique steps adds each TTP only once')
    doc.atlas_document.selected = before_selected
    window.update_document_labels()
    window.atlas_source_context = (('stale-catalog',), repeated_case['id'])
    token = doc.content_token()
    window.atlas_add_all_button.click()
    check(doc.content_token() == token and not window.atlas_source_bar.isVisible(),
          'stale source context cannot add to another dataset')
    empty = deepcopy(repeated_case)
    empty['x_atlas_relationships'] = {}
    store = {**catalog.objects_by_domain[DOMAIN], empty['id']:empty}
    doc.atlas_document.catalog = replace(catalog, objects_by_domain={**catalog.objects_by_domain, DOMAIN:store})
    window.show_atlas_record(empty['id'])
    check(window.atlas_source_bar.isVisible() and not window.atlas_add_all_button.isEnabled()
          and not window.atlas_remove_all_button.isEnabled(),
          'source without mapped TTPs disables both source actions')
    doc.atlas_document.catalog = catalog
    window.show_atlas_record(key)
    check(not window.atlas_source_bar.isVisible() and window.atlas_source_context is None,
          'technique navigation clears the source bulk-add context')
    check(window.atlas_detail_bar.isVisible(), 'ATLAS technique detail has selection/annotation controls')
    window.atlas_search.setText('AML.CS0000')
    check(window.atlas_sidebar.topLevelItemCount()==1,'ATLAS library search')
    window.atlas_search.clear()

    print('[ATLAS audit 3/5] Mixed saves, multiline CSV, snapshots and exact-source validation', flush=True)
    atlas = doc.atlas_document
    update_annotation(atlas,key,'','ATLAS line 1\nline 2',2.5,'#ffffff')
    before = doc.content_token()
    snapshot = snapshot_document(doc)
    window.choose_atlas_technique(key,'',False)
    check(key in snapshot.atlas_document.selected and key not in atlas.selected, 'save snapshot isolates companion selection from live edits')
    window.choose_atlas_technique(key,'',True)
    check(doc.content_token()==before, 'ATLAS selection round trip has stable content token')
    path = OUT/'mixed.studio.json'
    saved = save_studio(snapshot,path,log,save_as=True)
    restored = open_studio(ROOT/'data'/'attack',path,log)
    check(restored.selected==snapshot.selected and restored.atlas_document.selected==snapshot.atlas_document.selected,'Studio save/open preserves both frameworks')
    check(restored.atlas_document.navigator_layer==snapshot.atlas_document.navigator_layer,'Studio save/open preserves ATLAS annotations')
    check(not restored.dirty,'mixed document opens clean')
    rows = list(csv.DictReader(io.StringIO(csv_content(document_payload(snapshot)))))
    check(len(rows)==2 and {row['attack_domain'] for row in rows}=={DOMAIN,doc.catalog.domain},'mixed CSV retains distinct domain/version columns')
    check(next(row for row in rows if row['attack_domain']==DOMAIN)['comment']=='ATLAS line 1\nline 2','CSV preserves multiline ATLAS annotation')
    bad = document_payload(snapshot)
    bad['atlas_workspace']['selected_ttps'][0]['technique_id']='AML.T9999'
    try:
        StudioReader(ROOT/'data'/'attack',log).document(bad)
    except ValueError:
        check(True,'invalid ATLAS identity is rejected without silently dropping selection')
    else:
        raise AssertionError('Invalid ATLAS identity accepted')

    print('[ATLAS audit 4/5] Independent documents and recovery view', flush=True)
    window.new_document()
    wait(lambda:window.loaded_ok,'new document')
    check(window.current_document is not doc and window.atlas_selection_list.count()==0,'new Workplace starts with its own ATLAS selection')
    empty_before = window.current_document.content_token()
    window.show_atlas_record(repeated_case['id'])
    window.atlas_remove_all_button.click()
    check(window.current_document.atlas_document is None and window.current_document.content_token()==empty_before,
          'bulk remove from empty Workplace does not create ATLAS state or dirty the document')
    with patch('atlas_workspace.AnnotationDialog.exec', return_value=QtWidgets.QDialog.DialogCode.Rejected):
        window.edit_atlas_annotation(key)
    check(window.current_document.atlas_document is None and window.current_document.content_token()==empty_before,
          'cancelling first ATLAS annotation leaves the Workplace unchanged')
    window.activate_document(0)
    wait(lambda:window.loaded_ok,'original document')
    check(window.atlas_selection_list.count()==1,'switching back restores original ATLAS selection')
    window.duplicate_navigator_layer()
    wait(lambda:window.loaded_ok,'duplicate workplace')
    duplicate = window.current_document
    check(duplicate.atlas_document.selected==doc.atlas_document.selected,
          'duplicate active layer retains the ATLAS companion')
    window.choose_atlas_technique(key,'',False)
    check(key in doc.atlas_document.selected and key not in duplicate.atlas_document.selected,
          'duplicated Workplace ATLAS state is independent')
    window.activate_document(0)
    wait(lambda:window.loaded_ok,'original after duplicate')
    window.switch_category('Workplace')
    window.close_matrix_view('attack')
    window.close_matrix_view('atlas')
    window.atlas_selection_toggle.setChecked(False)
    recovery = session_payload(window.documents,0,window.studio_view())
    write_session(recovery,OUT/'session.json',log)
    session = read_session(ROOT/'data'/'attack',OUT/'session.json',log)
    check(key in session['documents'][0].atlas_document.selected,'session serializes exact ATLAS selections')
    window.pending_session_view = session['view']
    window.finish_studio_startup()
    check(not window.tabs.isTabVisible(window.matrix_tab_index) and not window.tabs.isTabVisible(window.atlas_matrix_tab_index),'session restores both matrix visibility settings')
    check(not window.atlas_selection_toggle.isChecked(),'session restores collapsed ATLAS group')
    restart_path = OUT/'restart-session.json'
    write_session(recovery,restart_path,log)
    restarted = MainWindow(ROOT/'data'/'attack', settings_path=OUT/'restart-settings.ini',session_path=restart_path)
    restarted.show()
    wait(lambda:restarted.session_startup_done and restarted.session_initialized and restarted.pending_session_notice is None,
         'fresh-window automatic session restore')
    check(key in restarted.current_document.atlas_document.selected
          and attack_key in restarted.current_document.selected,'fresh process-style window automatically restores both frameworks')
    check(not restarted.tabs.isTabVisible(restarted.matrix_tab_index)
          and not restarted.tabs.isTabVisible(restarted.atlas_matrix_tab_index),'fresh window keeps both matrices closed')
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Discard):
        restarted.close()
    window.atlas_selection_toggle.setChecked(True)
    before_language = doc.content_token()
    manager = language_manager()
    manager.set_language('zh_TW')
    app.processEvents()
    check('開啟 ATLAS' in window.open_atlas_matrix_button.text(), 'new ATLAS controls localize to Traditional Chinese')
    check(doc.content_token()==before_language and window.atlas_selection_list.count()==1,'language switch retains framework data and selection')
    window.grab().save(str(OUT/'workplace.png'))
    window.open_atlas_matrix()
    window.grab().save(str(OUT/'atlas-matrix.png'))
    window.switch_category('ATLAS Case Studies')
    window.show_atlas_record(window.atlas_sidebar.topLevelItem(0).data(0,KEY))
    window.grab().save(str(OUT/'case-study.png'))
    manager.set_language('en')
    print('[ATLAS audit 5/5] Complete', flush=True)
    (OUT/'checks.json').write_text(json.dumps({'passed':len(CHECKS),'checks':CHECKS},indent=2),encoding='utf-8')
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Discard):
        window.close()
    app.processEvents()
    print(f'PASS: {len(CHECKS)} checks',flush=True)


def tree_item_safe(tree,key):
    try:
        return tree_item(tree,key)
    except AssertionError:
        return None


if __name__=='__main__':
    main()
