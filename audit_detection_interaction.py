"""Native detection search, per-family expansion, gestures and hover clipboard. Flow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import time
import uuid
from unittest.mock import patch
from PySide6 import QtCore, QtGui, QtWidgets, QtTest
from attack_catalog import external_id
from attack_matrix import MATRIX_ID
from audit_visibility_presets import fixture as base_fixture
from custom_sources import load_custom
from main import MainWindow, configure_application, ROLE_ID, ROLE_CONTEXT
from navigator_integration import document_layer, imported_document, update_annotation, import_preview
from navigator_visuals import LayerAppearance
from matrix_expansion import save_family_expansion
from matrix_exports import matrix_scene, export_matrix
from stix_clipboard import object_json
from studio_files import save_studio, open_studio, write_session, session_payload, read_session
from ttp_documents import TTPDocument, export_document_csv
from ttp_selection import selected_cells
from ttp_search import matches, search_index

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'attack'
OUT=ROOT/'artifacts'/'detection-interaction'
CHECKS=[]


def log(text,current=0,total=0):
    print(text+(f' ({current}/{total})' if total else ''),flush=True)


def check(value,text):
    if not value: raise AssertionError(text)
    CHECKS.append(text)


def wait(condition,label='UI ready'):
    until=time.monotonic()+90
    while not condition():
        if time.monotonic()>until: raise TimeoutError(label)
        QtWidgets.QApplication.processEvents(); time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def fixture():
    bundle=base_fixture();objects=bundle['objects']
    child=next(o for o in objects if external_id(o)=='T1000.001')
    child['x_research_data']={'unicode':'研究用資料','values':[False,0,None,{'url':'https://example.test/a?b=1&c=2'}]}
    strategy=next(o for o in objects if o['type']=='x-mitre-detection-strategy')
    strategy.update(name='Unique strategy title',description='Strategy description needle with spaces.',
                    external_references=[{'source_name':'mitre-attack','external_id':'DET9000'}])
    revoked=deepcopy(strategy)
    revoked.update(id='x-mitre-detection-strategy--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'revoked strategy')),
                   name='Revoked strategy needle',revoked=True)
    objects.append(revoked)
    target=next(o['id'] for o in objects if external_id(o)=='T1002')
    objects.append({'type':'relationship','id':'relationship--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'revoked strategy edge')),
                    'relationship_type':'detects','source_ref':revoked['id'],'target_ref':target})
    return bundle


def root_item(matrix,key,slug):
    col=next(col for col in matrix.columns if col['slug']==slug)
    if 'view' in col: return next(f for f in col['view'].families if f['root'].key==key)
    tree=col['tree']
    return next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).data(0,MATRIX_ID)==key)


def click_cell(matrix,key,slug,modifier=QtCore.Qt.KeyboardModifier.NoModifier,checkbox=False):
    col=next(col for col in matrix.columns if col['slug']==slug)
    if 'view' in col:
        cell=next(cell for family in col['view'].families for cell in [family['root'],*family['children']] if cell.key==key)
        QtTest.QTest.mouseClick(cell,QtCore.Qt.MouseButton.LeftButton,modifier)
    else:
        tree=col['tree'];item=next(i for i in matrix.items_by_id[key] if i.treeWidget() is tree)
        tree.scrollToItem(item);QtWidgets.QApplication.processEvents()
        rect=tree.visualItemRect(item)
        point=QtCore.QPoint(rect.left()+8 if checkbox else rect.right()-12,rect.center().y())
        QtTest.QTest.mouseClick(tree.viewport(),QtCore.Qt.MouseButton.LeftButton,modifier,point)
    QtWidgets.QApplication.processEvents()


def main():
    log('Input directory: '+str(DATA.resolve()))
    log('Output directory: '+str(OUT.resolve()))
    for name in ('fixture.json','state.studio.json','session.json','state.navigator.json','state.csv','matrix.svg','flat.png','stix-hover.png','taxii-hover.png','audit.json'):
        log('Output file: '+str((OUT/name).resolve()))
    log('[Interaction Audit 1/7] Isolated fixture and exact detection index',0,7)
    OUT.mkdir(parents=True,exist_ok=True)
    pointers={p:p.read_bytes() for p in (DATA/'latest.json',DATA/'active.json') if p.exists()}
    source=OUT/'fixture.json';source.write_text(json.dumps(fixture(),ensure_ascii=False),encoding='utf-8')
    catalog=load_custom(DATA,str(source),'19.2',log)['catalog']
    ids={external_id(o):key for key,o in catalog.records.items()}
    root,child,sibling,beta,legacy=[ids[i] for i in ('T1000','T1000.001','T1000.002','T1001','T1002')]
    for query in ('unique strategy title','DET9000','strategy DESCRIPTION needle with spaces'):
        check(matches(catalog,beta,query,['detection_strategies']),'Detection Strategy matches '+query)
        check(not matches(catalog,root,query,['detection_strategies']),'strategy matches only directly mapped techniques '+query)
    check(not matches(catalog,legacy,'Revoked strategy needle',['detection_strategies']),'inactive detection strategies excluded')
    check(not matches(catalog,legacy,'Unique strategy title',['detection_strategies']),'revoked detects relationships excluded')
    doc=TTPDocument('Interaction example',catalog)
    update_annotation(doc,root,'','Preserve parent annotation',7,'#123456')
    update_annotation(doc,child,'execution','Child annotation',0,'')
    structural_records=deepcopy(catalog.records)
    structural_records[root]['kill_chain_phases']=[{'kill_chain_name':'mitre-attack','phase_name':'execution'}]
    structural_groups=deepcopy(catalog.groups)
    for tactics in structural_groups.values():
        if root in tactics.get('initial-access',[]): tactics['initial-access'].remove(root)
    structural_catalog=replace(catalog,records=structural_records,groups=structural_groups)
    structural=TTPDocument('Grouping parent',structural_catalog,selected={root})
    update_annotation(structural,root,'','Grouping parent note',4,'#123456')
    save_family_expansion(structural,root,'initial-access',False,notify=log)
    structural_layer=document_layer(structural)
    style=LayerAppearance(structural_layer,structural_catalog).cell('T1000','initial-access')
    check(style['enabled'] and style['score']==4 and style['background']=='#123456','expansion-only structural scope preserves inherited state and color')
    check(import_preview(structural_layer,structural_catalog)['unresolved']==0,'structural expansion row resolves as a display scope')
    check(imported_document(structural_layer,structural_catalog).selected=={root},'structural expansion cannot select a grouping-only occurrence')
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    previous_clip=app.clipboard().text()
    w=MainWindow(DATA,settings_path=OUT/'settings.ini');w.resize(1700,1000);w.show()
    wait(lambda:w.loaded_ok and not w.loader.isRunning())
    official=w.catalog
    candidates=[(edge['source_ref'],edge['target_ref']) for edge in official.all_objects_by_domain[official.domain].values()
        if edge.get('type')=='relationship' and edge.get('relationship_type')=='detects' and not edge.get('revoked') and not edge.get('x_mitre_deprecated')
        and edge.get('target_ref') in official.records and official.objects_by_domain[official.domain].get(edge.get('source_ref'),{}).get('type')=='x-mitre-detection-strategy']
    check(bool(candidates),'current official dataset contains direct detection mappings')
    strategy,target=candidates[0]
    identity=external_id(official.objects_by_domain[official.domain][strategy])
    check(matches(official,target,identity,['detection_strategies']),'real official Detection Strategy ID is searchable')
    w.install_imported_document(doc);wait(lambda:w.loaded_ok)
    w.open_matrix();m=w.matrix_view;wait(lambda:not m.building)
    log('[Interaction Audit 2/7] Native search fields in sidebar, matrices and export',1,7)
    w.search_field_actions['detection_strategies'].setChecked(True)
    for field in ('name','id'): w.search_field_actions[field].setChecked(False)
    w.ttp_search.setText('DET9000');w.apply_ttp_search()
    check(w.proxy.mapFromSource(w.items_by_id[beta][0].index()).isValid(),'sidebar searches Detection Strategy ID')
    check(not w.proxy.mapFromSource(w.items_by_id[legacy][0].index()).isValid(),'sidebar excludes unrelated technique')
    for layout in ('Flat','Side','Mini'):
        m.view_layout.setCurrentText(layout);wait(lambda:not m.building)
        m.search.setText('strategy description needle')
        check(m.scope_keys('search')=={beta},layout+' searches Strategy description')
        w.select_ttp_batch('replace','search')
        check(doc.selected=={beta},layout+' search batch uses strategy field')
    check({c['id'] for col in matrix_scene(doc,query='DET9000')['columns'] for c in col['cells']}=={'T1001'},'export projection honors Detection Strategy field')
    w.ttp_search.clear();w.apply_ttp_search();m.search.clear()
    log('[Interaction Audit 3/7] Actual mouse single/Control/Shift gestures and checkbox compatibility',2,7)
    for layout in ('Flat','Side','Mini'):
        m.view_layout.setCurrentText(layout);wait(lambda:not m.building)
        m.platform.setCurrentText('Windows');wait(lambda:not m.building)
        m.expand_button.click();w.clear_selection()
        w.select_matrix_ttp(legacy,True,'execution')
        click_cell(m,root,'execution')
        check(doc.selected=={root},layout+' unmodified label click selects only this technique')
        annotations=deepcopy(doc.navigator_layer['techniques'])
        click_cell(m,child,'execution',QtCore.Qt.KeyboardModifier.ControlModifier)
        check(doc.selected=={root,child},layout+' Control-click adds a technique')
        click_cell(m,child,'execution',QtCore.Qt.KeyboardModifier.ShiftModifier)
        check(doc.selected=={root},layout+' Shift-click removes an included technique')
        click_cell(m,legacy,'execution',QtCore.Qt.KeyboardModifier.ShiftModifier)
        check(doc.selected=={root,legacy},layout+' Shift-click adds without range selection')
        click_cell(m,root,'execution',QtCore.Qt.KeyboardModifier.ControlModifier)
        check(doc.selected=={legacy},layout+' Control-click removes existing occurrence family')
        check(doc.navigator_layer['techniques']==annotations,layout+' gestures preserve annotations and enabled state')
        if layout=='Flat':
            click_cell(m,root,'execution',checkbox=True)
            check(doc.selected=={root,legacy},'Flat checkbox remains additive without a modifier')
        w.selection_pref_actions['with_family'].setChecked(True)
        w.selection_pref_actions['visible_only'].setChecked(True)
        m.collapse_button.click()
        click_cell(m,root,'execution')
        check(child not in doc.selected and sibling not in doc.selected,layout+' mouse gesture honors visible family linking')
        w.selection_pref_actions['visible_only'].setChecked(False)
        w.selection_pref_actions['with_family'].setChecked(False)
        w.clear_selection();w.select_matrix_ttp(root,True,'execution')
        w.selection_pref_actions['with_family'].setChecked(True)
        click_cell(m,root,'execution',QtCore.Qt.KeyboardModifier.ControlModifier)
        check(not doc.selected,layout+' removing a linked parent does not invert unselected children into selection')
        w.selection_pref_actions['with_family'].setChecked(False)
    log('[Interaction Audit 4/7] Native individual arrows, scope inheritance, search and rebuild',3,7)
    for layout in ('Flat','Side','Mini'):
        m.view_layout.setCurrentText(layout);wait(lambda:not m.building)
        m.expand_button.click()
        selected=set(doc.selected)
        if layout=='Flat': root_item(m,root,'execution').setExpanded(False)
        else: root_item(m,root,'execution')['toggle'].click()
        check('expandedSubtechniques' not in doc.navigator_layer['layout'],layout+' individual change switches to saved per-technique mode')
        check((root,'execution') not in m.expansion_snapshot() and (root,'initial-access') in m.expansion_snapshot(),layout+' only clicked tactic family collapses')
        before=LayerAppearance(document_layer(doc),catalog).cell('T1000','execution')
        check(before['score']==7 and before['comment']=='Preserve parent annotation' and before['background']=='#123456',layout+' scoped expansion retains global inherited annotations')
        token=doc.fingerprint()
        m.search.setText('DET9000');m.search.clear()
        check(doc.fingerprint()==token,layout+' search expansion does not dirty the document')
        m.rebuild();wait(lambda:not m.building)
        check((root,'execution') not in m.expansion_snapshot() and (root,'initial-access') in m.expansion_snapshot(),layout+' rebuild restores individual open and closed states')
        check(doc.selected==selected,layout+' arrows preserve selected techniques')
    m.view_layout.setCurrentText('Flat');wait(lambda:not m.building)
    check(m.grab().save(str(OUT/'flat.png')),'individual expansion preview saved')
    log('[Interaction Audit 5/7] Exact source JSON, clipboard formats and hover popup lifecycle',4,7)
    w.show_record(child)
    bar=w.object_copy_bar
    raw=deepcopy(catalog.all_objects_by_domain[catalog.domain][child])
    selected=set(doc.selected);token=doc.fingerprint()
    check(bar.isVisible() and bar.context[2]==child,'technique detail exposes source copy controls')
    for envelope in (False,True):
        QtTest.QTest.mouseMove(bar.buttons[envelope],QtCore.QPoint(15,12))
        wait(lambda:bar.preview.isVisible() and bar.pending_format==envelope,'hover preview')
        content=json.loads(bar.preview_text.toPlainText())
        check(content==({'objects':[raw],'more':False} if envelope else raw),'hover shows complete '+('envelope' if envelope else 'STIX')+' JSON')
        check(bar.preview_text.isReadOnly(),'hover JSON is read only '+str(envelope))
        check(bar.preview.frameGeometry().intersected(bar.screen().availableGeometry())==bar.preview.frameGeometry(),'hover stays inside available screen '+str(envelope))
        QtTest.QTest.mouseMove(bar.preview_text.viewport(),QtCore.QPoint(20,30))
        QtTest.QTest.qWait(350)
        check(bar.preview.isVisible(),'moving into hover popup keeps it open '+str(envelope))
        viewport=bar.preview_text.viewport()
        point=viewport.rect().center()
        wheel=QtGui.QWheelEvent(QtCore.QPointF(point),QtCore.QPointF(viewport.mapToGlobal(point)),QtCore.QPoint(),QtCore.QPoint(0,-240),
            QtCore.Qt.MouseButton.NoButton,QtCore.Qt.KeyboardModifier.NoModifier,QtCore.Qt.ScrollPhase.ScrollUpdate,False)
        app.sendEvent(viewport,wheel)
        check(bar.preview_text.verticalScrollBar().value()>0,'actual mouse wheel scrolls long hover JSON '+str(envelope))
        bar.buttons[envelope].click()
        check(json.loads(app.clipboard().text())==content,'clipboard contains complete preview JSON '+str(envelope))
        paste=QtWidgets.QPlainTextEdit();paste.paste()
        check(json.loads(paste.toPlainText())==content,'clipboard pastes into a native text editor '+str(envelope))
        bar.pending_format=not envelope
        bar.preview_copy.click()
        check(json.loads(app.clipboard().text())==content,'preview copy uses the displayed format during a pending hover transition '+str(envelope))
        bar.pending_format=envelope
        check(bar.preview.grab().save(str(OUT/('taxii-hover.png' if envelope else 'stix-hover.png'))),'hover screenshot saved '+str(envelope))
        QtTest.QTest.mouseMove(w.crumb,QtCore.QPoint(3,3));QtTest.QTest.qWait(350)
        check(bar.preview.isHidden(),'leaving buttons and hover window dismisses preview '+str(envelope))
    check(doc.fingerprint()==token and doc.selected==selected,'preview/copy do not edit annotations or selection')
    check(catalog.all_objects_by_domain[catalog.domain][child]==raw,'copy leaves raw source object unchanged')
    w.details.setHtml('<h1>Index page</h1>')
    check(not bar.context and bar.preview.isHidden() and bar.isHidden(),'non-object page clears old preview and copy context')
    for category in ('Groups','Software','Mitigations','Detections'):
        w.switch_category(category)
        entry=next(i for i in w.library_items[category] if i.data(ROLE_CONTEXT)[0]==catalog.domain)
        index=w.library_proxy.mapFromSource(entry.index());w.show_library_index(index)
        check(bar.context[2]==entry.data(ROLE_ID),category+' detail copies the browsed object')
        bar.buttons[False].click()
        check(json.loads(app.clipboard().text())==catalog.all_objects_by_domain[catalog.domain][entry.data(ROLE_ID)],category+' copied source fields are exact')
    official_doc=TTPDocument('Official browsing',official)
    w.install_imported_document(official_doc);wait(lambda:w.loaded_ok)
    mobile=official.for_domain('mobile-attack')
    mobile_key=next(iter(mobile.records))
    w.show_domain_technique('mobile-attack',mobile_key)
    bar.buttons[True].click()
    check(json.loads(app.clipboard().text())['objects'][0]==official.all_objects_by_domain['mobile-attack'][mobile_key],'cross-domain detail copies Mobile source rather than active Enterprise domain')
    for category in ('Campaigns','Assets'):
        w.switch_category(category)
        entry=w.library_items[category][0]
        domain,_,key=entry.data(ROLE_CONTEXT)
        w.show_library_index(w.library_proxy.mapFromSource(entry.index()))
        bar.buttons[False].click()
        check(json.loads(app.clipboard().text())==official.all_objects_by_domain[domain][key],category+' source clipboard supports its own domain')
    w.select_navigator_layer(doc.document_id);wait(lambda:w.loaded_ok and not m.building)
    w.open_matrix();wait(lambda:not m.building)
    log('[Interaction Audit 6/7] Studio/Navigator/recovery and expanded-only SVG persistence',5,7)
    saved=save_studio(doc,OUT/'state.studio.json',log,save_as=True)
    reopened=open_studio(DATA,OUT/'state.studio.json',log)
    layer=document_layer(doc);(OUT/'state.navigator.json').write_text(json.dumps(layer,indent=2),encoding='utf-8')
    imported=imported_document(layer,catalog)
    for label,candidate in [('Studio',reopened),('Navigator',imported)]:
        check(candidate.search_fields==['detection_strategies'],label+' restores strategy search preference')
        appearance=LayerAppearance(document_layer(candidate),candidate.catalog)
        check(not appearance.cell('T1000','execution')['showSubtechniques'] and appearance.cell('T1000','initial-access')['showSubtechniques'],label+' restores independent tactic expansion flags')
        check(candidate.selected==doc.selected,label+' expansion rows do not widen selection')
    write_session(session_payload([saved],0,{}),OUT/'session.json',log)
    recovered=read_session(DATA,OUT/'session.json',log)['documents'][0]
    check(not recovered.dirty and recovered.navigator_layer==saved.navigator_layer,'session restores exact clean expansion baseline')
    scene=matrix_scene(doc,subtechniques='expanded')
    shown={(c['id'],col['slug']) for col in scene['columns'] for c in col['cells']}
    check(('T1000.001','execution') not in shown and ('T1000.002','initial-access') in shown,'expanded-only export follows individual scope flags')
    export_matrix(doc,OUT/'matrix.svg','svg',log,svg_options={'subtechniques':'expanded'})
    export_document_csv(doc,OUT/'state.csv',log)
    check(all(path.read_bytes()==value for path,value in pointers.items()),'official dataset pointers unchanged')
    with patch.object(w,'confirm_studio_changes',return_value='discard'): w.close()
    app.clipboard().setText(previous_clip)
    log('[Interaction Audit 7/7] Publishing report',6,7)
    (OUT/'audit.json').write_text(json.dumps({'status':'PASS','checks':CHECKS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log(f'[Interaction Audit] PASS: {len(CHECKS)} checks',7,7)


if __name__=='__main__': main()
