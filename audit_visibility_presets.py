"""Verify visible selection, saved expansion, source descriptions and presets. Flow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import time
import uuid
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets, QtTest
from audit_selection_search import synthetic
from attack_catalog import external_id
from attack_matrix import SourceCompleter, SOURCE_SEARCH
from custom_sources import load_custom
from main import MainWindow, configure_application, ROLE_CONTEXT
from navigator_integration import document_layer, imported_document, validate_layer, update_annotation
from navigator_dialogs import LayerSettingsDialog
from navigator_visuals import GRADIENT_PRESETS, LayerAppearance, gradient_color
from matrix_exports import matrix_scene, export_matrix
from studio_files import save_studio, open_studio, session_payload, write_session, read_session, StudioReader
from ttp_documents import TTPDocument, document_payload, export_document_csv
from ttp_selection import change_cells, selected_cells, validate_preferences

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'attack'
OUT=ROOT/'artifacts'/'visibility-presets'
CHECKS=[]


def log(text,current=0,total=0):
    print(text+(f' ({current}/{total})' if total else ''),flush=True)


def check(value,text):
    if not value: raise AssertionError(text)
    CHECKS.append(text)


def bad(call,text):
    try: call()
    except (ValueError,TypeError): check(True,text)
    else: raise AssertionError(text)


def wait(condition):
    until=time.monotonic()+90
    while not condition():
        if time.monotonic()>until: raise TimeoutError('UI did not become ready')
        QtWidgets.QApplication.processEvents(); time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def fixture():
    bundle=synthetic()
    objects=bundle['objects']
    mitigation=next(o for o in objects if external_id(o)=='M1000')
    mitigation['description']='Mitigation description needle (literal) with spaces.'
    for kind,identity in [('intrusion-set','G1000'),('tool','S1000')]:
        source={'type':kind,'id':kind+'--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'visibility '+identity)),
                'name':'Research '+identity,'description':identity+' description needle (literal) with spaces.',
                'x_mitre_domains':['enterprise-attack'],
                'external_references':[{'source_name':'mitre-attack','external_id':identity}]}
        target=next(o['id'] for o in objects if external_id(o)=='T1000')
        objects.extend([source,{'type':'relationship','id':'relationship--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,identity)),
                               'relationship_type':'uses','source_ref':source['id'],'target_ref':target}])
    return bundle


def main():
    log('Input directory: '+str(DATA.resolve()))
    log('Output directory: '+str(OUT.resolve()))
    for name in ('fixture.json','state.studio.json','state.navigator.json','state.csv','session.json','matrix.svg','matrix.xlsx','flat.png','source-search.png','presets.png','audit.json'):
        log('Output file: '+str((OUT/name).resolve()))
    log('[Visibility Audit 1/7] Creating isolated catalog and checking compatibility',0,7)
    OUT.mkdir(parents=True,exist_ok=True)
    pointers={p:p.read_bytes() for p in (DATA/'latest.json',DATA/'active.json') if p.exists()}
    source=OUT/'fixture.json'
    source.write_text(json.dumps(fixture(),ensure_ascii=False),encoding='utf-8')
    catalog=load_custom(DATA,str(source),'19.2',log)['catalog']
    ids={external_id(o):key for key,o in catalog.records.items()}
    root,child,sibling,beta=[ids[i] for i in ('T1000','T1000.001','T1000.002','T1001')]
    legacy={'across_tactics':True,'with_family':False}
    check(validate_preferences(legacy)=={**legacy,'visible_only':False},'old two-field preferences load with visible-only off')
    doc=TTPDocument('Visibility example',catalog)
    check(not doc.dirty,'new default document is clean')
    old=TTPDocument('Visibility example',catalog,selection_preferences=legacy)
    check(doc.fingerprint()==old.fingerprint(),'default preference normalization preserves old recovery fingerprints')
    doc.selection_preferences.update(visible_only=True,with_family=True)
    bad(lambda:change_cells(doc,{(root,'execution')},'add'),'visible-only cannot silently broaden when visibility is unavailable')
    change_cells(doc,{(root,'execution')},'add',visible={(root,'execution')})
    check(selected_cells(doc)=={(root,'execution')},'filter runs after family and cross-tactic expansion')
    change_cells(doc,{(root,'execution')},'remove',visible=set())
    check(doc.selected=={root},'hidden occurrences remain unchanged on removal')
    for payload in ({'selectVisibleTechniques':1},{'layout':{'expandedSubtechniques':'invalid'}},{'layout':{'expandedSubtechniques':[]}},
                    {'techniques':[{'techniqueID':'T1000','showSubtechniques':'yes'}]}):
        bad(lambda payload=payload:validate_layer({'name':'Invalid','domain':catalog.domain,**payload}),'invalid setting rejected '+str(payload))
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    w=MainWindow(DATA,settings_path=OUT/'settings.ini');w.resize(1750,1000);w.show()
    wait(lambda:w.loaded_ok and not w.loader.isRunning())
    for domain in ('enterprise-attack','mobile-attack','ics-attack'):
        official=w.catalog.for_domain(domain)
        example=TTPDocument('Domain settings',official)
        example.selection_preferences['visible_only']=True
        example.navigator_layer={'name':example.name,'domain':domain,'layout':{'expandedSubtechniques':'all'}}
        exchanged=imported_document(document_layer(example),official)
        check(exchanged.selection_preferences['visible_only'] and exchanged.navigator_layer['layout']['expandedSubtechniques']=='all',domain+' exchanges standard visibility/expansion fields')
    w.install_imported_document(doc); wait(lambda:w.loaded_ok)
    w.open_matrix(); m=w.matrix_view;wait(lambda:not m.building)
    log('[Visibility Audit 2/7] All layouts, family linking and visible-only batches',1,7)
    for layout in ('Flat','Side','Mini'):
        m.view_layout.setCurrentText(layout);wait(lambda:not m.building)
        m.platform.setCurrentText('Windows');wait(lambda:not m.building)
        m.collapse_button.click();w.clear_selection()
        visible=m.scope_cells('visible')
        check((child,'execution') not in visible and (beta,'execution') not in visible,layout+' excludes collapsed children and other platforms')
        m.request_selection(root,'execution',True)
        check(selected_cells(doc)==visible.intersection({(root,'execution'),(root,'initial-access'),(child,'execution'),(sibling,'initial-access')}),layout+' linked click stays visible')
        w.select_ttp_batch('replace','platform')
        check(selected_cells(doc)==visible,layout+' replace batch cannot reintroduce invisible cells')
        m.expand_button.click()
        check(doc.navigator_layer['layout']['expandedSubtechniques']=='all' and (child,'execution') in m.scope_cells('visible'),layout+' Expand all saves and reveals children')
        w.clear_selection();m.request_selection(root,'execution',True)
        check(child in doc.selected and sibling in doc.selected,layout+' expanded family becomes eligible')
        m.search.setText('Other sibling')
        before=selected_cells(doc);eligible=m.scope_cells('visible')
        w.change_source_ttps(catalog.domain,next(o['id'] for o in catalog.objects_by_domain[catalog.domain].values() if external_id(o)=='M1000'),'remove')
        check(before-selected_cells(doc)<=eligible,layout+' source removal leaves hidden selections intact')
        m.search.clear()
        update_annotation(doc,child,'execution','Keep this note',0,'')
        doc.navigator_layer['hideDisabled']=True
        next(row for row in doc.navigator_layer['techniques'] if row['techniqueID']=='T1000.001')['enabled']=False
        w.refresh_layer_appearance()
        check((child,'execution') not in m.scope_cells('visible'),layout+' hide-disabled rows excluded')
        w.clear_selection();m.request_selection(root,'execution',True)
        check(child not in doc.selected,layout+' family link cannot select hidden disabled child')
        doc.navigator_layer['hideDisabled']=False
        next(row for row in doc.navigator_layer['techniques'] if row['techniqueID']=='T1000.001').pop('enabled')
        w.refresh_layer_appearance()
        m.expand_annotated_button.click()
        check((root,'execution') in m.expansion_snapshot(),layout+' annotated mode restores zero-score/comment family')
        check(doc.navigator_layer['layout']['expandedSubtechniques']=='annotated',layout+' annotated mode saved')
        m.search.setText('Other sibling');m.search.clear()
        check((root,'initial-access') not in m.expansion_snapshot(),layout+' clearing search restores saved annotated policy')
    log('[Visibility Audit 3/7] Sidebar scope and layer switching',2,7)
    w.switch_category('TTP');w.ttp_search.clear();w.apply_ttp_search();w.tree.expandAll()
    visible=w.visible_selection_cells('sidebar')
    w.clear_selection();item=w.items_by_id[child][0];slug=item.data(ROLE_CONTEXT)[1]
    w.choose_technique_occurrence(child,True,slug,surface='sidebar')
    check(selected_cells(doc)<=visible and child in doc.selected,'sidebar uses its own expanded and filtered occurrence scope')
    before=selected_cells(doc)
    w.selection_pref_actions['visible_only'].setChecked(False)
    check(selected_cells(doc)==before,'preference switch preserves current selection')
    w.selection_pref_actions['visible_only'].setChecked(True)
    doc.navigator_layer.setdefault('layout',{})['layout']='flat'
    w.refresh_layer_appearance();wait(lambda:not m.building)
    m.collapse_button.click()
    other=TTPDocument('Other layer',catalog,navigator_layer={'name':'Other layer','domain':catalog.domain,'layout':{'expandedSubtechniques':'all'}})
    w.install_imported_document(other);wait(lambda:w.loaded_ok and not m.building)
    check((root,'execution') in m.expansion_snapshot() and not w.selection_pref_actions['visible_only'].isChecked(),'new layer restores its own expansion/preference')
    w.select_navigator_layer(doc.document_id);wait(lambda:w.loaded_ok and not m.building)
    check(not m.expansion_snapshot() and w.selection_pref_actions['visible_only'].isChecked(),'returning layer restores collapse and visible-only preference')
    legacy_open=TTPDocument('Legacy open',catalog,navigator_layer={'name':'Legacy open','domain':catalog.domain,
        'techniques':[{'techniqueID':'T1000','showSubtechniques':True}]})
    legacy_closed=TTPDocument('Legacy closed',catalog)
    w.install_imported_document(legacy_open);wait(lambda:w.loaded_ok and not m.building)
    check((root,'execution') in m.expansion_snapshot(),'legacy layer restores explicit row expansion')
    w.install_imported_document(legacy_closed);wait(lambda:w.loaded_ok and not m.building)
    check((root,'execution') not in m.expansion_snapshot(),'switching between legacy layers clears previous expansion')
    w.select_navigator_layer(doc.document_id);wait(lambda:w.loaded_ok and not m.building)
    m.expand_annotated_button.click()
    log('[Visibility Audit 4/7] Library and source-completer Description search',3,7)
    for category,kind,identity in [('Groups','Group','G1000'),('Software','Software','S1000'),('Mitigations','Mitigation','M1000')]:
        w.switch_category(category)
        query='description needle (literal) with spaces'
        w.search.setText(query);w.apply_search()
        matching=[item for item in w.library_items[category] if w.library_proxy.mapFromSource(item.index()).isValid()]
        check(len(matching)==1 and identity in matching[0].text(),category+' sidebar matches description-only literal spaces')
        check(w.ttp_search.isHidden() and w.ttp_search_fields_button.isHidden(),category+' hides TTP-only controls')
        check('description' in w.search.placeholderText(),category+' placeholder explains searchable fields')
        m.source_kind.setCurrentText(kind)
        m.source_completer.setCompletionPrefix(query)
        model=m.source_completer.completionModel()
        check(model.rowCount()==1,kind+' completion searches Description role')
        label=model.index(0,0).data()
        check(identity in label and query not in label,kind+' completion still displays short identity label')
        check(m.source_completer.pathFromIndex(model.index(0,0))==label,kind+' completion inserts label instead of Description')
        m.source_completer.setCompletionPrefix('  '+query.upper()+'  ')
        check(m.source_completer.completionModel().rowCount()==1,kind+' completion handles case and outer whitespace')
        m.source_picker.setEditText(query);m.update_source_state()
        check(not m.add_source_button.isEnabled(),kind+' partial Description cannot execute a stale source')
        m.source_completer.activated[str].emit(label)
        check(m.add_source_button.isEnabled(),kind+' exact completed entry enables source operation')
    w.open_matrix();wait(lambda:not m.building)
    m.source_kind.setCurrentText('Group');m.source_picker.setFocus();m.source_picker.lineEdit().clear()
    QtTest.QTest.keyClicks(m.source_picker.lineEdit(),'description needle')
    app.processEvents()
    check(m.source_completer.completionModel().rowCount()==1,'actual typing filters completion by Description')
    QtTest.QTest.keyClick(m.source_picker.lineEdit(),QtCore.Qt.Key.Key_Escape)
    app.processEvents();check(m.grab().save(str(OUT/'source-search.png')),'source search screenshot saved')
    log('[Visibility Audit 5/7] Preset drafts, validation, gradients and cancellation',4,7)
    original=deepcopy(doc.navigator_layer)
    settings=LayerSettingsDialog(doc,w)
    check(doc.navigator_layer==original and settings.gradient_preset.currentIndex()==0,'opening settings retains imported/custom gradient')
    for index,(name,colors,low,high) in enumerate(GRADIENT_PRESETS,1):
        settings.gradient_preset.setCurrentIndex(index);settings.apply_gradient_preset(index)
        check(settings.colors.text()==', '.join(colors) and float(settings.minimum.text())==low and float(settings.maximum.text())==high,name+' fills stops and score bounds')
        gradient={'colors':list(colors),'minValue':low,'maxValue':high}
        validate_layer({'name':'Preset','domain':catalog.domain,'gradient':gradient})
        check(gradient_color(low,gradient,raw=True)[:7]==colors[0][:7],name+' minimum renders first color')
        check(gradient_color(high,gradient,raw=True)[:7]==colors[-1][:7],name+' maximum renders last color')
    settings.reject();check(doc.navigator_layer==original,'Cancel discards all preset draft edits')
    settings=LayerSettingsDialog(doc,w);settings.gradient_preset.setCurrentIndex(4);settings.apply_gradient_preset(4)
    settings.show();app.processEvents()
    check(settings.grab().save(str(OUT/'presets.png')),'preset settings preview saved')
    settings.save();check(settings.result()==QtWidgets.QDialog.DialogCode.Accepted,'preset accepted by standard layer validator')
    doc.navigator_layer=settings.result_layer;w.refresh_layer_appearance()
    custom=LayerSettingsDialog(doc,w)
    custom.gradient_preset.setCurrentIndex(1);custom.apply_gradient_preset(1)
    custom.minimum.setFocus();custom.minimum.selectAll();QtTest.QTest.keyClicks(custom.minimum,'-7')
    check(custom.gradient_preset.currentIndex()==0,'manual gradient edit returns to Custom')
    custom.reject()
    log('[Visibility Audit 6/7] Studio, Navigator, recovery and matrix outputs',5,7)
    saved=save_studio(doc,OUT/'state.studio.json',log,save_as=True)
    restored=open_studio(DATA,OUT/'state.studio.json',log)
    layer=document_layer(doc)
    (OUT/'state.navigator.json').write_text(json.dumps(layer,indent=2),encoding='utf-8')
    imported=imported_document(validate_layer(layer),catalog)
    for name,candidate in [('Studio',restored),('Navigator',imported)]:
        check(candidate.selection_preferences['visible_only'] and candidate.navigator_layer['layout']['expandedSubtechniques']=='annotated',name+' restores saved selection and expansion')
        check(candidate.navigator_layer['gradient']==doc.navigator_layer['gradient'],name+' restores chosen preset values')
    write_session(session_payload([saved],0,{}),OUT/'session.json',log)
    recovered=read_session(DATA,OUT/'session.json',log)['documents'][0]
    check(not recovered.dirty and recovered.selection_preferences['visible_only'],'session restores clean saved baseline and new preference')
    old_payload=document_payload(doc);old_payload['selection_preferences']=legacy
    check(not StudioReader(DATA,log).document(old_payload).selection_preferences['visible_only'],'old Studio two-field preferences remain readable')
    probe=TTPDocument('Legacy expansion',catalog,navigator_layer={'name':'Legacy expansion','domain':catalog.domain,'techniques':[{'techniqueID':'T1000','showSubtechniques':True}]})
    check(any(c['depth'] for col in matrix_scene(probe,subtechniques='expanded')['columns'] for c in col['cells']),'legacy per-technique expansion remains readable')
    for mode in ('none','all','annotated'):
        doc.navigator_layer['layout']['expandedSubtechniques']=mode
        scene=matrix_scene(doc,subtechniques='expanded')
        children=[c for col in scene['columns'] for c in col['cells'] if c['depth']]
        check(bool(children)==(mode!='none'),'matrix export uses saved expansion '+mode)
    w.refresh_layer_appearance();app.processEvents();check(m.grab().save(str(OUT/'flat.png')),'matrix preview saved')
    export_matrix(doc,OUT/'matrix.svg','svg',log,svg_options={'subtechniques':'expanded'})
    export_matrix(doc,OUT/'matrix.xlsx','xlsx',log)
    export_document_csv(doc,OUT/'state.csv',log)
    check('T1000' in (OUT/'state.csv').read_text(encoding='utf-8-sig'),'CSV selection remains intact')
    check(all(p.read_bytes()==value for p,value in pointers.items()),'official dataset pointers unchanged')
    with patch.object(w,'confirm_studio_changes',return_value='discard'): w.close()
    log('[Visibility Audit 7/7] Publishing verified report',6,7)
    (OUT/'audit.json').write_text(json.dumps({'status':'PASS','checks':CHECKS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log(f'[Visibility Audit] PASS: {len(CHECKS)} checks',7,7)


if __name__=='__main__': main()
