"""Native workspace geometry, navigation scope and ATLAS case-study tab checks. Flow: README.md."""
from pathlib import Path
from unittest.mock import patch
import argparse
import json
from copy import deepcopy
from PySide6 import QtCore, QtWidgets, QtTest
from main import MainWindow, CatalogLoader, configure_application
from navigation_scope import ATTACK_CATEGORIES, ATLAS_CATEGORIES
from atlas_cases import CASE_KEY
from atlas_catalog import DOMAIN
from attack_catalog import external_id
from audit_export_options import wait
from navigator_integration import update_annotation
from localization import language_manager
from studio_files import session_payload,write_session,read_session

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/workspace-layout'


def collapse_probe():
    print('Input files: None (native Qt layout with catalog worker paused)',flush=True)
    print('Input/output isolated settings: '+str(OUT/'probe.ini'),flush=True)
    print('Output geometry preview: '+str(OUT/'collapsed.png'),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    with patch.object(CatalogLoader,'start',return_value=None):
        window=MainWindow(ROOT/'data/attack',settings_path=OUT/'probe.ini',session_path=None)
    window.resize(1200,1200); window.show()
    window.workspace.setCurrentWidget(window.tabs); window.tabs.setCurrentIndex(window.selection_tab_index)
    for button in (window.attack_selection_toggle,window.atlas_selection_toggle,window.car_selection_toggle):
        button.setChecked(False)
    QtTest.QTest.qWait(30)
    summary=window.selection_summary.geometry()
    print('[Layout probe 1/2] Summary geometry: '+str((summary.y(),summary.height()))+'; font height: '+str(window.selection_summary.fontMetrics().height()),flush=True)
    window.grab().save(str(OUT/'collapsed.png'))
    ok=summary.height()<=window.selection_summary.fontMetrics().height()+16 and summary.y()<=20
    with patch.object(window,'finish_studio_exit',return_value=True): window.close()
    assert ok, 'All collapsed groups must keep summary compact and top-aligned'
    print('[Layout probe 2/2] PASS',flush=True)


def full_audit():
    checks=[]
    def check(value,label):
        assert value,label
        checks.append(label); print('[Check] '+label,flush=True)
    def log(message,*_): print(message,flush=True)
    print('Input dataset root: '+str(ROOT/'data/attack'),flush=True)
    print('Output settings/session/previews/report: '+str(OUT),flush=True)
    protected={p:p.read_bytes() for p in [ROOT/'data/ui-settings.ini',ROOT/'data/workspace-session.json',
        ROOT/'data/attack/active.json',ROOT/'data/attack/latest.json'] if p.exists()}
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); configure_application(app)
    settings=OUT/'settings.ini'; settings.unlink(missing_ok=True)
    print('[Workspace layout 1/4] Loading real catalogs and checking compact geometry',flush=True)
    w=MainWindow(ROOT/'data/attack',settings_path=settings,session_path=None); w.show()
    wait(lambda:w.loaded_ok and not w.loader.isRunning())
    w.switch_category('Workplace'); doc=w.current_document
    attack=next(iter(w.catalog.records)); atlas=next(iter(w.atlas_catalog.records))
    w.choose_technique_occurrence(attack,True);w.choose_atlas_technique(atlas,'',True)
    update_annotation(doc,attack,'','Retain ATT&CK note',4,'#112233')
    update_annotation(doc.atlas_document,atlas,'','Retain ATLAS note',6,'#445566')
    w.change_car_inclusion({'CAR-2013-05-009'},True,doc.document_id)
    baseline=doc.content_token()
    toggles=(w.attack_selection_toggle,w.atlas_selection_toggle,w.car_selection_toggle)
    lists=(w.selection_list,w.atlas_selection_list,w.car_selection_list)
    for size in ((1100,1100),(950,650)):
        w.resize(*size)
        for value in range(8):
            for i,toggle in enumerate(toggles):toggle.setChecked(bool(value&(1<<i)))
            QtTest.QTest.qWait(10)
            check(w.selection_summary.height()<=w.selection_summary.fontMetrics().height()+16 and w.selection_summary.y()<=20,
                f'summary stays compact and top-aligned: size={size}, expansion={value}')
            check(doc.content_token()==baseline,'collapse/expand keeps all content '+str((size,value)))
            for i,listing in enumerate(lists):
                check(listing.isHidden()==(not bool(value&(1<<i))),'independent list visibility '+str((size,value,i)))
        for toggle in toggles:toggle.setChecked(False)
        QtTest.QTest.qWait(20);w.grab().save(str(OUT/f'collapsed-{size[0]}.png'))
    w.resize(1440,920)
    for toggle in toggles:toggle.setChecked(True)
    w.open_matrix();wait(lambda:not w.matrix_view.building)
    matrix=w.matrix_view
    matrix.search.setText('PowerShell');QtTest.QTest.qWait(30)
    original_height=matrix.scroll.viewport().height()
    matrix.controls_toggle.click();QtTest.QTest.qWait(30)
    check(not matrix.controls_panel.isVisible() and matrix.scroll.viewport().height()>original_height+150,'real catalog matrix gains space when controls collapse')
    check(doc.content_token()==baseline and matrix.search.text()=='PowerShell','collapsing real controls preserves annotations, selections and query')
    w.grab().save(str(OUT/'matrix-controls-collapsed.png'))
    matrix.controls_toggle.click();matrix.search.clear()
    print('[Workspace layout 2/4] Settings scope, actual actions and persistence',flush=True)
    check(w.navigation_scope=='both' and all(not w.navigation_buttons[k].isHidden() for k in ATTACK_CATEGORIES|ATLAS_CATEGORIES),'both frameworks shown by default')
    check('ATLAS Case Studies' not in w.navigation_buttons,'case studies removed from activity rail')
    w.switch_category('ATLAS TTP');w.open_atlas_matrix()
    for scope in ('attack','atlas','both'):
        w.set_navigation_scope(scope);QtTest.QTest.qWait(10)
        check(all(w.navigation_buttons[k].isHidden()==(scope=='atlas') for k in ATTACK_CATEGORIES),'ATT&CK visibility '+scope)
        check(all(w.navigation_buttons[k].isHidden()==(scope=='attack') for k in ATLAS_CATEGORIES),'ATLAS visibility '+scope)
        check(not w.navigation_buttons['Workplace'].isHidden() and all(w.navigation_buttons[k].isHidden()==(scope!='both') for k in ('CAR Analytics','CAR Data Model','CAR Sensors')),'Workplace remains available; CAR respects its own switch '+scope)
        check(w.tabs.currentWidget() is w.atlas_matrix and w.workspace.currentWidget() is w.tabs and doc.content_token()==baseline,'filter retains current matrix and all content '+scope)
    w.set_navigation_scope('atlas')
    with patch.object(CatalogLoader,'start',return_value=None):
        reopened=MainWindow(ROOT/'data/attack',settings_path=settings,session_path=None)
    check(reopened.navigation_scope=='atlas' and reopened.navigation_buttons['TTP'].isHidden(),'scope restored from isolated settings')
    with patch.object(reopened,'finish_studio_exit',return_value=True):reopened.close()
    w.set_navigation_scope('both')
    print('[Workspace layout 3/4] Real Case Studies tab, search, navigation, source actions and close/reopen',flush=True)
    check(w.tabs.indexOf(w.atlas_cases_page)==-1 and w.workspace.indexOf(w.atlas_cases_page)>=0 and w.atlas_cases_page.parent() is not w.navigation_rail,'Case Studies is an upper reference page')
    w.atlas_cases_action.trigger();QtTest.QTest.qWait(20); page=w.atlas_cases_page
    check(w.workspace.currentWidget() is page,'View menu opens actual Case Studies tab')
    check(page.listing.topLevelItemCount()==73 and w.sidebar.isVisible() and w.sidebar.isAncestorOf(page.listing),'case list resides in the explorer sidebar')
    w.switch_category('ATLAS TTP');w.open_atlas_cases();w.set_navigation_scope('attack')
    check(w.workspace.currentWidget() is page and w.sidebar.isVisible() and w.explorer_stack.currentWidget() is page.sidebar and doc.content_token()==baseline,'scope changes retain case details and sidebar list')
    w.set_navigation_scope('both')
    obj=next(o for o in w.current_atlas_catalog.objects_by_domain[DOMAIN].values() if external_id(o)=='AML.CS0000')
    page.search.setText('AML.CS0000');app.processEvents()
    visible=[page.listing.topLevelItem(i) for i in range(page.listing.topLevelItemCount()) if not page.listing.topLevelItem(i).isHidden()]
    check(len(visible)==1,'case ID search filters actual list')
    item=visible[0];page.listing.scrollToItem(item);app.processEvents()
    QtTest.QTest.mouseClick(page.listing.viewport(),QtCore.Qt.MouseButton.LeftButton,QtCore.Qt.KeyboardModifier.NoModifier,page.listing.visualItemRect(item).center())
    check('AML.CS0000' in page.details.toPlainText() and 'S00' in page.details.toPlainText() and page.copy_bar.isVisible(),'native case detail/steps and source copy bar render in independent reference page')
    check(doc.content_token()==baseline,'case search/navigation does not edit content')
    check(w.atlas_cases_tab_index>=0 and w.details_tab_index>=0 and w.atlas_cases_tab_index!=w.details_tab_index,'case and technique details are independent sibling tabs')
    expected=w.atlas_source_techniques(w.current_atlas_catalog,obj['id']);before=set(doc.atlas_document.selected);notes=deepcopy(doc.atlas_document.navigator_layer)
    page.add.click();check(doc.atlas_document.selected==before|expected and doc.atlas_document.navigator_layer==notes,'case Add uses exact official relationships and retains annotations')
    page.remove.click();check(doc.atlas_document.selected==(before|expected)-expected and doc.atlas_document.navigator_layer==notes,'case Remove deselects exact related TTPs and retains annotations')
    page.details.copy_section('Title');check(app.clipboard().text()==obj['name'],'case title copy remains available')
    page.details.copy_section('Description');check(app.clipboard().text()==obj.get('description',''),'case description copy remains available')
    target=next(iter(expected));w.open_atlas_link(QtCore.QUrl('atlas:'+external_id(w.current_atlas_catalog.records[target])))
    check(w.workspace.currentWidget() is w.details_page,'case technique link opens internal technique detail')
    w.open_atlas_cases();check(page.search.text()=='AML.CS0000' and page.key==obj['id'],'return retains case search and selected entry')
    token=doc.content_token()
    w.show_document_context_menu(w.document_tabs.tabRect(w.atlas_cases_tab_index).center());w.document_context_menu.actions()[0].trigger();w.document_context_menu.close()
    check(w.atlas_cases_tab_index<0 and doc.content_token()==token,'case tab context close retains contents')
    w.open_atlas_cases_button.click();check(w.atlas_cases_tab_index>=0 and page.key==obj['id'],'Workplace button reopens retained case tab')
    context,old_owner=page.context,doc.document_id
    w.new_document();wait(lambda:w.loaded_ok)
    w.change_all_atlas_source_ttps('add',context,old_owner)
    check(w.current_document.atlas_document is None,'stale case action cannot edit another document')
    w.activate_document(0);wait(lambda:w.loaded_ok);w.open_atlas_cases(obj['id'])
    print('[Workspace layout 4/4] Session view restoration, bilingual controls and protected files',flush=True)
    for toggle in toggles:toggle.setChecked(False)
    matrix.set_controls_expanded(False)
    saved=w.studio_view();checkpoint=OUT/'case-session.json';write_session(session_payload(w.documents,0,saved),checkpoint,log)
    restored=read_session(ROOT/'data/attack',checkpoint,log)
    check(restored['view']['page']=='cases' and restored['view']['atlas_case_key']==obj['id'] and not restored['view']['car_expanded'],'session stores actual case page/query/key and all collapsed groups')
    w.close_atlas_cases();page.search.clear()
    matrix.set_controls_expanded(True)
    for toggle in toggles:toggle.setChecked(True)
    w.pending_session_view=restored['view'];w.finish_studio_startup();QtTest.QTest.qWait(30)
    check(w.workspace.currentWidget() is page and page.search.text()=='AML.CS0000' and page.key==obj['id'] and all(not b.isChecked() for b in toggles),'actual view restoration reopens case and restores three collapsed groups')
    check(not matrix.controls_toggle.isChecked() and not matrix.controls_panel.isVisible(),'session restores collapsed matrix controls independently of active reference tab')
    legacy=dict(restored['view']);legacy.pop('matrix_controls_expanded')
    w.pending_session_view=legacy;w.finish_studio_startup()
    check(matrix.controls_toggle.isChecked(),'older session defaults to expanded controls')
    reference_view=dict(saved,page='selected',atlas_cases_open=True)
    page.clear_detail();w.pending_session_view=reference_view;w.finish_studio_startup()
    check(w.workspace.currentWidget() is w.tabs and page.key==obj['id'] and w.atlas_cases_tab_index>=0,'inactive case reference restores content without taking focus')
    w.pending_session_view=saved;w.finish_studio_startup()
    w.grab().save(str(OUT/'case-studies-en.png'))
    manager=language_manager();manager.set_language('zh_TW');manager.refresh_all();app.processEvents()
    check('案例研究' in w.document_tabs.tabText(w.atlas_cases_tab_index) and [a.text().replace('&&','&') for a in w.navigation_family_actions.values()]==['ATT&CK','ATLAS','CAR'],'reference tab localizes and group names stay literal')
    w.grab().save(str(OUT/'case-studies-zh.png'));manager.set_language('en')
    with patch.object(w,'confirm_studio_changes',return_value='discard'):w.close()
    changed=[str(p) for p,v in protected.items() if p.read_bytes()!=v]
    if changed: print('Protected files changed during audit: '+', '.join(changed),flush=True)
    check(not changed,'user settings/session and dataset pointers preserved')
    (OUT/'audit.json').write_text(json.dumps({'passed':True,'count':len(checks),'checks':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'[Workspace layout] PASS: {len(checks)} checks',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--collapse-only',action='store_true')
    if parser.parse_args().collapse_only:collapse_probe()
    else:collapse_probe();full_audit()
