"""CAR-001..008 native catalog, Qt interaction and full lifecycle acceptance. Workflow: README.md."""
import ast
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from PySide6 import QtCore, QtGui, QtWidgets, QtTest, QtSvg
from attack_catalog import external_id
from audit_export_options import wait
from car_catalog import load_car, ROOT as CAR_ROOT
from car_documents import change_inclusion, included, validate_workspace, empty_catalog
from car_mapping import related_analytics, resolve_technique
from car_views import REF, SORT, row_values
from framework_dialog import FrameworkOptionsDialog
from framework_io import selection, framework_payload, framework_documents, read_framework_document
from layer_analysis import snapshot_document
from main import MainWindow, configure_application
from navigator_integration import document_layer, update_annotation, export_layers
from studio_files import save_studio, open_studio, session_payload, write_session, read_session, StudioReader
from ttp_documents import TTPDocument, export_document_csv, document_payload
from localization import language_manager

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/car-integration'
DATA=ROOT/'data/attack'
CHECKS=[]


def log(message,current=0,total=0):
    print(str(message)+(f' ({current}/{total})' if total else ''),flush=True)


def check(value,label):
    if not value: raise AssertionError(label)
    CHECKS.append(label)


def bad(task,label):
    try: task()
    except (ValueError,FileNotFoundError,PermissionError): check(True,label)
    else: raise AssertionError(label)


def click_row(listing,row,modifier=QtCore.Qt.KeyboardModifier.NoModifier):
    listing.scrollToItem(listing.item(row)); QtWidgets.QApplication.processEvents()
    QtTest.QTest.mouseClick(listing.viewport(),QtCore.Qt.MouseButton.LeftButton,modifier,listing.visualItemRect(listing.item(row)).center())
    QtWidgets.QApplication.processEvents()


def main():
    log('Input source manifest: '+str((CAR_ROOT/'source.json').resolve()))
    log('Input ATT&CK/ATLAS root: '+str(DATA.resolve()))
    log('Output tests/settings/session/JSON/CSV/SVG/previews/report: '+str(OUT.resolve()))
    OUT.mkdir(parents=True,exist_ok=True)
    protected={p:p.read_bytes() for p in [ROOT/'data/ui-settings.ini',ROOT/'data/workspace-session.json',DATA/'active.json',DATA/'latest.json'] if p.exists()}
    log('[CAR acceptance A1/4] Fixed source/schema and official grouping semantics',0,4)
    car=load_car(notify=log)
    check((len(car.analytics),len(car.models),len(car.sensors))==(102,13,7),'CAR-001 fixed snapshot native file counts')
    check(car.source['commit']=='1b922fe1527d956e222a99473472e594f10f610b','CAR-001 fixed upstream commit')
    check((CAR_ROOT/'LICENSE.txt').exists() and (CAR_ROOT/'NOTICE.txt').exists(),'CAR-001 original license/notice retained')
    analytic=car.analytics['CAR-2013-05-009']
    import yaml
    original = yaml.safe_load((CAR_ROOT/'analytics/CAR-2013-05-009.yaml').read_text(encoding='utf-8'))
    check(analytic['implementations']==original['implementations'] and any('code' not in i for i in analytic['implementations']),'CAR-001 every implementation retained, including link-only')
    check('implementations' not in car.analytics['CAR-2013-01-002'],'CAR-001 analytics without implementation remain available')
    # Execute only the fixed pure bucket loop, never upstream networking or document generators.
    tree=ast.parse((CAR_ROOT/'scripts/generate_analytics.py').read_text(encoding='utf-8'))
    loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='tid')
    code=compile(ast.fix_missing_locations(ast.Module(body=loop.body[:3],type_ignores=[])),'fixed-car-buckets','exec')
    expected={}
    for parent in sorted({c['technique'] for a in car.analytics.values() for c in a.get('coverage',[])}):
        scope={'tid':parent,'analytics':list(car.analytics.values())}; exec(code,scope)
        if scope['none_bucket']: expected[parent,'']=tuple(sorted({a['id'] for a in scope['none_bucket']}))
        expected.update({(parent,k):tuple(sorted({a['id'] for a in v})) for k,v in scope['sub_bucket'].items()})
    check(expected==car.groups,'CAR-003 every grouping matches fixed official generate_analytics.py loop')
    check('CAR-2013-05-009' in car.groups['T1036','T1036.003'],'CAR-003 explicit .003 mapping present')
    check('CAR-2013-05-002' in car.groups['T1036',''],'CAR-003 technique-only bucket retained')
    check('CAR-2013-05-009' not in {a for _,a in related_analytics(car,'T1036.005')},'CAR-003 no sibling expansion from parent or .003')
    check(any(scope=='T1036.003' and a=='CAR-2013-05-009' for scope,a in related_analytics(car,'T1036')),'CAR-003 parent aggregate identifies sub-technique source')
    check(('T1021','') in car.groups and sum(p=='T1021' and bool(s) for p,s in car.groups)>1,'CAR-003 T1021 retains direct and multiple sub-technique buckets')
    check(car.candidates(car.analytics['CAR-2013-01-002'])=={},'CAR-005 absent data requirements do not imply sensor readiness')
    matches=car.candidates(analytic)
    check('sysmon_13' in matches and matches['sysmon_13']==sorted(set(analytic['data_model_references']) & car.sensor_fields['sysmon_13']), 'CAR-005 sensor candidate is exact native triple intersection')
    fixture=OUT/'schema-fixture'; fixture.mkdir(exist_ok=True)
    record={'id':'CAR-2099-01-001','title':'Minimal optional record','description':'Read-only','unknown_extension':{'a':[1,2]}}
    import yaml
    raw=yaml.safe_dump(record).encode(); (fixture/'analytics').mkdir(exist_ok=True); (fixture/'analytics'/('CAR-2099-01-001.yaml')).write_bytes(raw)
    manifest={'schema':1,'commit':'a'*40,'files':{'analytics/CAR-2099-01-001.yaml':sha256(raw).hexdigest()}}
    (fixture/'source.json').write_text(json.dumps(manifest),encoding='utf-8')
    minimal=load_car(fixture)
    check(minimal.analytics[record['id']]['unknown_extension']==record['unknown_extension'],'CAR-001 missing optional fields/unknown native fields preserved')
    (fixture/'analytics'/('CAR-2099-01-001.yaml')).write_bytes(raw+b'\n# changed')
    bad(lambda:load_car(fixture),'CAR-001 corrupt source cannot publish partial index')
    log('[CAR acceptance B2/4] Real Qt lists, sorting, links, icons and independent inclusion',1,4)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); configure_application(app)
    window=MainWindow(DATA,settings_path=OUT/'settings.ini',session_path=OUT/'recovery.json')
    window.show(); wait(lambda:window.loaded_ok and not window.loader.isRunning())
    check(window.windowTitle().endswith(' — Fusion Studio'),'CAR-008 product rename retained')
    browser=window.car_browser
    check(window.car_catalog.dataset_id==car.dataset_id,'CAR-001 background loader publishes same verified snapshot')
    for category,name in [('CAR Analytics','car-analytics.svg'),('CAR Data Model','car-data-model.svg'),('CAR Sensors','car-sensors.svg')]:
        button=window.navigation_buttons[category]
        check(not button.icon().isNull() and bool(button.toolTip()) and button.accessibleName()==category,'CAR-005 rail icon/label/tooltip/accessibility: '+category)
        check(QtSvg.QSvgRenderer(str(ROOT/'assets/navigation'/name)).isValid(),'CAR-005 delivered usable SVG: '+name)
        button.click(); check(window.workspace.currentWidget() is browser,'CAR-005 rail opens native CAR page: '+category)
    window.navigation_buttons['CAR Analytics'].click()
    check(browser.model.columnCount()==7 and [browser.model.headerData(i,QtCore.Qt.Orientation.Horizontal) for i in range(1,7)]==
          ['ID','Name','Submission Date','ATT&CK Techniques','Implementations','Applicable Platforms'],'CAR-002 official six attributes plus independent include column')
    before=window.current_document.content_token()
    # Check each real header twice; expected sort calculated independently from displayed columns.
    for column in range(1,7):
        for turn in range(2):
            browser.table.scrollTo(browser.proxy.index(0,column)); app.processEvents()
            header=browser.table.horizontalHeader(); x=header.sectionViewportPosition(column)+min(header.sectionSize(column)//2,40)
            QtTest.QTest.mouseClick(header.viewport(),QtCore.Qt.MouseButton.LeftButton,QtCore.Qt.KeyboardModifier.NoModifier,QtCore.QPoint(x,header.height()//2)); app.processEvents()
            descending=header.sortIndicatorOrder()==QtCore.Qt.SortOrder.DescendingOrder
            records=list(car.analytics.values())
            present=[a for a in records if row_values(a,window.catalog)[1][column-1] is not None]
            missing=[a for a in records if row_values(a,window.catalog)[1][column-1] is None]
            present.sort(key=lambda a:a['id']); present.sort(key=lambda a:row_values(a,window.catalog)[1][column-1],reverse=descending)
            expected_ids=[a['id'] for a in present]+sorted(a['id'] for a in missing)
            actual=[browser.proxy.index(i,1).data(REF) for i in range(browser.proxy.rowCount())]
            check(actual==expected_ids,'CAR-002 real header sorts complete filtered data, stable ID ties/missing bottom: '+str((column,turn,descending)))
    check(window.current_document.content_token()==before,'CAR-002 sorting is read-only')
    browser.search.setText('CAR-2013-05-009'); app.processEvents()
    check(browser.proxy.rowCount()==1,'CAR-002 ID search narrows Analytics')
    index=browser.proxy.index(0,0); browser.table.setCurrentIndex(index); browser.table.scrollTo(index); app.processEvents()
    rect=browser.table.visualRect(index)
    QtTest.QTest.mouseClick(browser.table.viewport(),QtCore.Qt.MouseButton.LeftButton,QtCore.Qt.KeyboardModifier.NoModifier,QtCore.QPoint(rect.left()+10,rect.center().y())); app.processEvents()
    check(any(e['id']=='CAR-2013-05-009' for e in included(window.current_document).values()),'CAR-006 checkbox after sorting/search includes correct analytic ID')
    check(not window.current_document.selected and window.current_document.dirty,'CAR-006 CAR-only modification marks dirty without selecting TTPs')
    check(window.car_selection_list.count()==1 and 'CAR 1' in window.tabs.tabText(window.selection_tab_index),'CAR-006 Workplace list/count synchronized independently')
    browser.open_analytic('CAR-2013-01-002'); browser.add.click()
    check(len(included(window.current_document))==2,'CAR-006 detail Add includes analytic without code or coverage requirement')
    check('Unknown' in browser.details.toPlainText(),'CAR-005 missing requirements explicitly shown as unknown')
    browser.open_analytic('CAR-2013-05-009')
    check('Splunk' in browser.details.toPlainText() or 'splunk' in browser.details.toPlainText(),'CAR-004 native implementation details visible')
    browser.navigate('car:technique/T1036.003')
    check(window.workspace.currentWidget() is window.details_page and 'Related CAR Analytics' in window.details.toPlainText(),'CAR-004 analytic leads to current ATT&CK technique detail with CAR reverse links')
    window.open_detail_link(QtCore.QUrl('car:analytic/CAR-2013-05-009'))
    check(window.workspace.currentWidget() is browser and 'CAR-2013-05-009' in browser.details.toPlainText(),'CAR-004 technique reverse link returns to same analytic detail')
    browser.navigate('car:model/process/create/md5_hash')
    check('CAR-2013-05-009' in browser.details.toPlainText(),'CAR-005 exact Data Model reference finds analytic')
    browser.navigate('car:sensor/sysmon_13')
    check('Mapped to Event' in browser.details.toPlainText() and 'partial field intersections' in browser.details.toPlainText(),'CAR-005 sensor version/native mapping notes/candidate qualification visible')
    browser.show_list(); check(browser.search.text()=='CAR-2013-05-009' and browser.proxy.rowCount()==1,'CAR-004 Back retains source search/filter/sort state')
    browser.search.clear(); browser.only_included.setChecked(True); app.processEvents()
    check(browser.proxy.rowCount()==2,'CAR-006 included-only filter synchronizes check state')
    browser.only_included.setChecked(False)
    check(window.grab().save(str(OUT/'analytics-sort.png')),'CAR-002 Analytics sort screenshot')
    browser.table.sortByColumn(3,QtCore.Qt.SortOrder.DescendingOrder); app.processEvents()
    check(window.grab().save(str(OUT/'analytics-date.png')),'CAR-002 second date sort screenshot')
    browser.tabs.setCurrentIndex(1); check(window.grab().save(str(OUT/'by-technique.png')),'CAR-003 three-column native by-technique screenshot')
    window.switch_category('CAR Data Model'); browser.models.expandToDepth(1)
    check(window.grab().save(str(OUT/'data-model.png')),'CAR-005 Data Model screenshot')
    window.switch_category('CAR Sensors'); check(window.grab().save(str(OUT/'sensors.png')),'CAR-005 Sensors screenshot')
    source=window.current_document
    owner=source.document_id
    window.change_car_inclusion({'CAR-2013-05-002'},True,owner)
    window.switch_category('Workplace')
    count=len(included(source)); click_row(window.car_selection_list,0); click_row(window.car_selection_list,2,QtCore.Qt.KeyboardModifier.ShiftModifier)
    check(len(window.car_selection_list.selectedItems())==3,'CAR-006 native Shift selects a range without inclusion changes')
    click_row(window.car_selection_list,1,QtCore.Qt.KeyboardModifier.ControlModifier)
    check(len(window.car_selection_list.selectedItems())==2 and len(included(source))==count,'CAR-006 native Ctrl toggles highlight without changing inclusion')
    check(window.grab().save(str(OUT/'workplace.png')),'CAR-006 independent Workplace CAR section screenshot')
    target_ids={i.data(REF) for i in window.car_selection_list.selectedItems()}
    pos=window.car_selection_list.visualItemRect(window.car_selection_list.selectedItems()[0]).center()
    window.car_selected_menu(pos); menu=window.workplace_context_menu
    menu.close(); check(len(included(source))==count,'CAR-006 cancelling right-click preserves document')
    window.car_selected_menu(pos); remove=window.workplace_context_menu.actions()[-1]; remove.trigger(); window.workplace_context_menu.close()
    check(set(included(source))==set(source.car_workspace['entries'])-target_ids,'CAR-006 context removal only deselects highlighted analytics')
    check(all(not source.car_workspace['entries'][k]['included'] for k in target_ids),'CAR-006 removal retains analytic records and annotations')
    # Two documents, duplicate, and stale menu command ownership.
    source_key=next(iter(source.catalog.records)); window.choose_technique_occurrence(source_key,True)
    update_annotation(source,source_key,'','Keep ATT&CK annotation',3,'#112233')
    atlas_key=next(iter(window.atlas_catalog.records)); window.choose_atlas_technique(atlas_key,'',True)
    ttp_state=(set(source.selected),deepcopy(source.navigator_layer),source.atlas_document.content_token())
    window.change_car_inclusion({'CAR-2013-05-009'},True,owner)
    selected_ref=car.dataset_id+':CAR-2013-05-009'; source.car_workspace['entries'][selected_ref]['annotations']={'note':'Retained analyst note'}
    other=TTPDocument('Other Workplace',source.catalog); window.install_imported_document(other)
    wait(lambda:window.loaded_ok)
    window.change_car_inclusion({selected_ref},False,owner)
    check(not other.car_workspace and source.car_workspace['entries'][selected_ref]['included'],'CAR-006 stale owner command cannot change another Workplace')
    window.activate_document(window.documents.index(source)); wait(lambda:window.loaded_ok)
    window.duplicate_navigator_layer(); wait(lambda:window.loaded_ok)
    duplicate=window.current_document
    check(duplicate.car_workspace==source.car_workspace and duplicate.car_workspace is not source.car_workspace,'CAR-007 duplicate independently copies native CAR state')
    window.change_car_inclusion({selected_ref},False,duplicate.document_id)
    check(source.car_workspace['entries'][selected_ref]['included'] and not duplicate.car_workspace['entries'][selected_ref]['included'],'CAR-007 duplicate edits do not affect source')
    check(ttp_state==(set(source.selected),source.navigator_layer,source.atlas_document.content_token()),'CAR-006 CAR operations preserve all ATT&CK/ATLAS inclusion and annotations')
    log('[CAR acceptance C3/4] Native Save/Open, seven content scopes, CSV/Navigator and recovery',2,4)
    for attack,atlas,include_car in [(a,b,c) for a in (False,True) for b in (False,True) for c in (False,True) if a or b or c]:
        opts=(attack,atlas,include_car); label=''.join('1' if x else '0' for x in opts); path=OUT/('scope-'+label+'.json')
        saved=save_studio(source,path,log,save_as=True,frameworks=opts)
        restored=open_studio(DATA,path,log,fallback_catalog=source.catalog)
        check(bool(restored.selected)==attack and bool(restored.atlas_document)==atlas and bool(restored.car_workspace)==include_car,'CAR-007 native content combination '+label)
        check(saved.dirty!=(attack and atlas and include_car),'CAR-007 partial output retains unsaved complete baseline '+label)
        content=path.read_text(encoding='utf-8')
        if not include_car: check('CAR-2013-05-009' not in content and 'car_workspace' not in content,'CAR-007 excluded CAR leaves no snapshot/IDs '+label)
    car_only=OUT/'scope-001.json'
    restored=open_studio(OUT/'no-attack-files',car_only,log)
    check(restored.car_workspace==source.car_workspace and not restored.catalog.records,'CAR-007 CAR-only opens with no ATT&CK cache/files')
    session=OUT/'car-only-recovery.json'; write_session(session_payload([restored],0,{}),session,log)
    check(read_session(OUT/'no-attack-files',session,log)['documents'][0].car_workspace==source.car_workspace,'CAR-007 CAR-only recovery needs no ATT&CK files')
    old=document_payload(source); old.pop('car_workspace')
    check(not StudioReader(DATA,log).document(old).car_workspace,'CAR-007 old documents without extension remain readable')
    old['car_workspace']={'schema':'invalid'}
    check(not read_framework_document(StudioReader(DATA,log),old,(True,True,False),source.catalog).car_workspace,'CAR-007 skipped malformed CAR block is not parsed')
    only=json.loads(car_only.read_text(encoding='utf-8')); only['car_workspace']['entries'][selected_ref]['source']['commit']='a'*40
    unknown=deepcopy(source.car_workspace); entry=unknown['entries'].pop(selected_ref); entry['source']['dataset_sha256']='f'*64
    unknown_key='f'*64+':'+entry['id']; unknown['entries'][unknown_key]=entry
    missing=snapshot_document(source); missing.car_workspace=validate_workspace(unknown)
    missing_path=OUT/'missing-snapshot.json'; save_studio(missing,missing_path,log)
    recovered=open_studio(DATA,missing_path,log)
    check(recovered.car_workspace==missing.car_workspace,'CAR-007 missing exact CAR snapshot retains complete native reference')
    window.install_imported_document(recovered); wait(lambda:window.loaded_ok)
    check(any('Unresolved snapshot' in window.car_selection_list.item(i).text() for i in range(window.car_selection_list.count())),'CAR-007 missing snapshot is visibly unresolved, never replaced')
    browser.open_analytic(unknown_key)
    check('Unresolved snapshot' in browser.details.toPlainText(),'CAR-007 archived analytic detail stays available without exact source')
    csv_path=OUT/'mixed.csv'; export_document_csv(snapshot_document(source),csv_path,log)
    rows=list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8-sig'))))
    check({r['content_type'] for r in rows}=={'attack_ttp','atlas_ttp','car_analytic'},'CAR-007 CSV clearly distinguishes three row types')
    check(all(not r['technique_id'] and r['car_id'].startswith('CAR-') for r in rows if r['content_type']=='car_analytic'),'CAR-007 CAR IDs never masquerade as technique IDs')
    nav_path=OUT/'ttp-only.navigator.json'; export_layers(framework_documents(source),nav_path,log)
    check('CAR-' not in nav_path.read_text(encoding='utf-8'),'CAR-007 Navigator contains only explicit selected TTPs')
    bad(lambda:framework_documents(source,(False,False,True)),'CAR-007 CAR-only Navigator rejected with native-save guidance')
    dialog=FrameworkOptionsDialog('write',OUT/'choices.json',window)
    check(dialog.attack.isChecked() and dialog.atlas.isChecked() and dialog.car.isChecked(),'CAR-007 all three native content choices default on')
    dialog.attack.setChecked(False); dialog.atlas.setChecked(False)
    check(dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).isEnabled() and dialog.choices().car,'CAR-007 native UI permits CAR-only')
    dialog.car.setChecked(False); check(not dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).isEnabled(),'CAR-007 at least one content type required')
    dialog.reject()
    checkpoint=OUT/'full-session.json'; write_session(session_payload([source,duplicate],1,{}),checkpoint,log)
    docs=read_session(DATA,checkpoint,log)['documents']
    check([d.car_workspace for d in docs]==[source.car_workspace,duplicate.car_workspace],'CAR-007 recovery retains independent CAR state for all documents')
    path=OUT/'atomic.json'; path.write_bytes(b'Original')
    with patch.object(Path,'replace',side_effect=PermissionError('CAR acceptance publication failure')):
        bad(lambda:save_studio(source,path,log),'CAR-008 failed save reports atomic publication error')
    check(path.read_bytes()==b'Original' and not list(OUT.glob('*.tmp')),'CAR-008 failed native write preserves file and removes temporary output')
    log('[CAR acceptance D4/4] Bilingual UI, small rail, checkpoint and regression evidence',3,4)
    window.activate_document(window.documents.index(source)); wait(lambda:window.loaded_ok)
    manager=language_manager(); manager.set_language('zh_TW'); manager.refresh_all(); app.processEvents()
    window.switch_category('CAR Analytics'); browser.tabs.setCurrentIndex(0)
    check(window.grab().save(str(OUT/'analytics-zh.png')),'CAR-008 Traditional Chinese Analytics screenshot')
    manager.set_language('en')
    window.resize(950,650); window.set_navigation_labels_visible(False); app.processEvents()
    check(all(not window.navigation_buttons[k].icon().isNull() for k in ('CAR Analytics','CAR Data Model','CAR Sensors')),'CAR-005 small-window label toggle retains separate icons')
    window.set_navigation_labels_visible(True); window.resize(1440,920)
    window.checkpoint_session(); wait(lambda:not window.session_worker or not window.session_worker.isRunning())
    check(window.session_path.exists() and any(d.car_workspace for d in read_session(DATA,window.session_path,log)['documents']),'CAR-007 actual application automatic checkpoint includes CAR')
    window.session_stopping=True
    with patch.object(window,'confirm_studio_changes',return_value='discard'): window.close()
    check(all(p.read_bytes()==v for p,v in protected.items()),'CAR-008 user settings/session and ATT&CK pointers preserved')
    report={'passed':True,'count':len(CHECKS),'checks':CHECKS,'requirements':{f'CAR-{i:03}':'PASS' for i in range(1,9)},'source':car.source,'native_group_count':len(car.groups)}
    (OUT/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log(f'[CAR acceptance] PASS: {len(CHECKS)} checks',4,4)


if __name__=='__main__': main()
