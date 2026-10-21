"""Verify scoped selection, extended search and mitigation batches. Workflow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from hashlib import sha256
import csv
import json
import time
from unittest.mock import patch
import uuid

from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from attack_matrix import MATRIX_SLUG
from audit_advanced_navigator import fixture
from custom_sources import load_custom
from batch_dialogs import BatchEditDialog
from layer_analysis import snapshot_document, calculate_layer
from layer_upgrade import upgrade_preview, migrate_layer
from main import MainWindow, configure_application, ROLE_CONTEXT
from matrix_exports import matrix_scene
from navigator_integration import document_layer, imported_document, update_annotation, validate_layer
from navigator_dialogs import ImportLayerDialog
from studio_files import open_studio, save_studio, write_session, read_session, session_payload, StudioReader
from ttp_documents import TTPDocument, export_document_csv, document_payload
from ttp_selection import change_cells, selected_cells, validate_selection_scopes, validate_preferences
from ttp_search import search_index, matches, validate_search_fields
from ttp_operations import batch_patch

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'attack'
OUT=ROOT/'artifacts'/'selection-search'
CHECKS=[]


def log(message,current=0,total=0):
    print(message+(f' ({current}/{total})' if total else ''),flush=True)


def check(value,label):
    if not value: raise AssertionError(label)
    CHECKS.append(label)


def bad(task,label):
    try: task()
    except (ValueError,TypeError,KeyError): check(True,label)
    else: raise AssertionError(label)


def wait(condition,label):
    end=time.monotonic()+90
    while not condition():
        if time.monotonic()>end: raise TimeoutError(label)
        QtWidgets.QApplication.processEvents();time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def synthetic():
    bundle=fixture()
    objects=bundle['objects']
    ids={external_id(o):o for o in objects if o['type']=='attack-pattern'}
    root,child,beta,legacy=[ids[i] for i in ('T1000','T1000.001','T1001','T1002')]
    root['kill_chain_phases'].append({'kill_chain_name':'mitre-attack','phase_name':'initial-access'})
    root['description']='Golden description phrase with spaces.'
    root['x_mitre_data_sources']=['Legacy Process: Legacy Creation']
    child['description']='Child-only description needle.'
    sibling=deepcopy(child);sibling.update(id='attack-pattern--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'selection sibling')),name='Other sibling')
    sibling['external_references'][0]['external_id']='T1000.002'
    sibling['kill_chain_phases']=[{'kill_chain_name':'mitre-attack','phase_name':'initial-access'}]
    def obj(kind,name,**fields):
        return {'type':kind,'id':kind+'--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'search '+name)),
                'name':name,'x_mitre_domains':['enterprise-attack'],**fields}
    mitigation=obj('course-of-action','Research Mitigation',external_references=[{'source_name':'mitre-attack','external_id':'M1000'}])
    empty=obj('course-of-action','No active targets',external_references=[{'source_name':'mitre-attack','external_id':'M1001'}])
    source=obj('x-mitre-data-source','ResearchProcess',external_references=[{'source_name':'mitre-attack','external_id':'DS1000'}])
    component=obj('x-mitre-data-component','Proc Sensor Creation',x_mitre_data_source_ref=source['id'])
    analytic=obj('x-mitre-analytic','Analytic fixture',x_mitre_log_source_references=[{
        'x_mitre_data_component_ref':component['id'],'name':'ResearchSensor','channel':'EventCode=7777'}])
    strategy=obj('x-mitre-detection-strategy','Strategy fixture',x_mitre_analytic_refs=[analytic['id']])
    def edge(kind,src,tgt,**fields):
        return obj('relationship',kind+src['id']+tgt['id'],relationship_type=kind,source_ref=src['id'],target_ref=tgt['id'],**fields)
    objects += [sibling,mitigation,empty,source,component,analytic,strategy,
        edge('subtechnique-of',sibling,root),edge('mitigates',mitigation,root),edge('mitigates',mitigation,beta),
        edge('mitigates',empty,legacy,revoked=True),edge('uses',mitigation,child),edge('detects',strategy,beta),
        edge('detects',strategy,legacy,revoked=True)]
    return bundle


def main():
    log(f'Input directory: {DATA.resolve()}');log(f'Output directory: {OUT.resolve()}')
    OUT.mkdir(parents=True,exist_ok=True)
    pointers={p:p.read_bytes() for p in [DATA/'active.json',DATA/'latest.json'] if p.exists()}
    bundle=OUT/'fixture.json';bundle.write_text(json.dumps(synthetic(),ensure_ascii=False),encoding='utf-8')
    catalog=load_custom(DATA,str(bundle),'19.2',log)['catalog']
    ids={external_id(o):k for k,o in catalog.records.items()}
    root,child,sibling,beta,legacy=[ids[i] for i in ('T1000','T1000.001','T1000.002','T1001','T1002')]
    source_ids={external_id(o):k for k,o in catalog.objects_by_domain[catalog.domain].items() if o['type']=='course-of-action'}
    mitigation,empty=source_ids['M1000'],source_ids['M1001']
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)

    log('[Selection/Search 1/6] Exact occurrence and family set operations')
    d=TTPDocument('Selection',catalog)
    change_cells(d,{(root,'execution')},'add')
    check(selected_cells(d)=={(root,'execution'),(root,'initial-access')} and not d.selection_scopes,'default selection spans all tactics')
    d.selection_preferences['across_tactics']=False
    change_cells(d,{(root,'execution')},'remove')
    check(d.selected=={root} and d.selection_scopes=={root:['initial-access']},'single tactic deselection retains other occurrence')
    change_cells(d,{(root,'execution')},'invert')
    check(not d.selection_scopes and root in d.selected,'selecting all occurrences compresses partial override')
    change_cells(d,{(root,'execution')},'replace')
    check(d.selection_scopes=={root:['execution']},'replace operates on tactic instances')
    change_cells(d,{(root,'execution')},'annotated',{(root,'execution')})
    check(selected_cells(d)=={(root,'execution')},'annotated selection preserves scoped result')
    change_cells(d,{(root,'execution')},'unannotated',{(root,'execution')})
    check(not d.selected and not d.selection_scopes,'empty unannotated result clears union and overrides')
    d.selection_preferences['with_family']=True
    change_cells(d,{(child,'execution')},'add')
    check(d.selected=={root,child} and d.selection_scopes[root]==['execution'],'family selection honors mapped tactic when across is off')
    change_cells(d,{(child,'execution')},'remove')
    check(not d.selected,'family deselection removes parent and same-tactic children')
    d.selection_preferences['across_tactics']=True
    change_cells(d,{(child,'execution')},'add')
    check(d.selected=={root,child,sibling} and not d.selection_scopes,'cross-tactic family selection includes siblings')
    change_cells(d,{(sibling,'initial-access')},'remove')
    check(not d.selected,'sibling deselection removes complete family')
    for value in ({root:[]},{root:['invalid']},{beta:['execution']},{root:['execution','execution']}):
        bad(lambda v=value:validate_selection_scopes(v,{root},catalog),'reject malformed partial scopes '+repr(value))
    bad(lambda:validate_preferences({'across_tactics':1,'with_family':False}),'preference booleans validated')
    scoped=TTPDocument('Scope switch',catalog,selected={root},selection_scopes={root:['execution']})
    reduced=replace(catalog,version='19.3',tactics={slug:obj for slug,obj in catalog.tactics.items() if slug!='execution'},tactic_order=['initial-access'])
    scoped.set_catalog(reduced)
    check(not scoped.selected and not scoped.selection_scopes,'version with removed selected tactic never widens partial selection')

    log('[Selection/Search 2/6] Historical and detection-backed search fields')
    idx=search_index(catalog,log)
    for key,query,fields in [(root,'golden description phrase',['description']),
                             (root,'legacy creation',['data_sources']), (beta,'ResearchProcess',['data_sources']),
                             (beta,'Proc Sensor Creation',['data_sources']), (beta,'ResearchSensor',['data_sources']),
                             (beta,'EventCode=7777',['data_sources']), (beta,'DS1000',['data_sources'])]:
        check(matches(catalog,key,query,fields),'search matches '+query)
    check(not matches(catalog,root,'golden description phrase',['name','id']),'Description opt-in excludes default name/ID')
    check(not matches(catalog,legacy,'ResearchSensor',['data_sources']),'revoked detection relationship does not leak data-source match')
    check(not matches(catalog,child,'ResearchSensor',['data_sources']),'data-source matches do not propagate through parent/child')
    check(matches(catalog,root,'T1000',['id']) and matches(catalog,root,'ALPHA',['name']),'ID/name remain literal case-insensitive')
    check(not matches(catalog,root,'Alpha.*',['name']),'query is literal, not regular expression')
    for fields in ([],['other'],['name','name']): bad(lambda f=fields:validate_search_fields(f),'reject search fields '+repr(fields))
    official=load_catalog(DATA,log)
    historical=load_catalog(DATA,log,snapshot_pointer(DATA,'11.3'))
    check(any(v['data_sources'] for v in search_index(historical,log).values()),'historical official legacy data sources indexed')
    check(any('sysmon' in v['data_sources'] for v in search_index(official,log).values()),'ATT&CK 19.2 active detection log sources indexed')
    for domain in ('mobile-attack','ics-attack'):
        dc=official.for_domain(domain)
        check(set(search_index(dc,log))==set(dc.records),domain+' builds independent complete search index')
    official_task=next(k for k,o in official.records.items() if external_id(o)=='T1053.005')
    archived=TTPDocument('Archive scopes',official,selected={official_task},selection_scopes={official_task:['execution']})
    archived.set_catalog(official.for_domain('mobile-attack'));archived.set_catalog(official)
    check(archived.selection_scopes=={official_task:['execution']},'domain switch restores exact partial selection')
    archived.set_catalog(historical);archived.set_catalog(official)
    check(archived.selection_scopes=={official_task:['execution']},'historical version switch retains and restores valid selected tactics')

    log('[Selection/Search 3/6] Native preferences and three matrix layouts')
    w=MainWindow(DATA,settings_path=OUT/'ui.ini');w.resize(1650,1100);w.show()
    wait(lambda:w.loaded_ok and not w.loader.isRunning(),'startup')
    document=TTPDocument('Research fixture',catalog)
    w.install_imported_document(document);wait(lambda:w.loaded_ok,'fixture tree')
    w.open_matrix();wait(lambda:not w.matrix_view.building,'fixture matrix')
    matrix=w.matrix_view
    w.selection_pref_actions['across_tactics'].setChecked(False)
    check(document.selection_preferences=={'across_tactics':False,'with_family':False,'visible_only':False} and document.dirty,'native preference updates only active document and dirty state')
    annotation=deepcopy(document.navigator_layer)
    for layout in ('Flat','Side','Mini'):
        w.clear_selection()
        matrix.view_layout.setCurrentText(layout);wait(lambda:not matrix.building,layout)
        matrix.request_selection(root,'execution',True)
        check(document.selection_scopes=={root:['execution']},layout+' click includes only requested tactic')
        if layout=='Flat':
            checks={item.data(0,MATRIX_SLUG):item.checkState(0)==QtCore.Qt.CheckState.Checked for item in matrix.items_by_id[root]}
        else:
            checks={cell.slug:cell.isChecked() for col in matrix.columns for fam in col['view'].families
                    for cell in [fam['root'],*fam['children']] if cell.key==root}
        check(checks['execution'] and not checks['initial-access'],layout+' displays independent checkboxes')
        check(all((item.checkState()==QtCore.Qt.CheckState.Checked)==(item.data(ROLE_CONTEXT)[1]=='execution') for item in w.items_by_id[root]),layout+' sidebar agrees with matrix occurrences')
        w.select_ttp_batch('remove','platform','execution')
        check(not document.selected,layout+' tactic batch removal respects local occurrences')
        w.select_ttp_batch('add','platform','initial-access')
        check((root,'initial-access') in selected_cells(document) and (root,'execution') not in selected_cells(document),layout+' tactic batch add does not select other tactics')
    w.clear_selection()
    w.selection_pref_actions['with_family'].setChecked(True)
    w.select_matrix_ttp(child,True,'execution')
    check(document.selected=={root,child},'native family selection excludes differently mapped sibling')
    w.selection_pref_actions['across_tactics'].setChecked(True)
    check(document.selection_scopes=={root:['execution']},'changing preference does not retroactively expand existing choice')
    w.select_matrix_ttp(child,True,'execution')
    check(document.selected=={root,child,sibling} and not document.selection_scopes,'next native selection applies cross-tactic family preference')
    check(document.navigator_layer==annotation or document.navigator_layer.get('techniques',[])==annotation.get('techniques',[]),'selection preferences never rewrite annotations')

    log('[Selection/Search 4/6] Native Description/Data Sources filters and Mitigation add/remove')
    w.selection_pref_actions['with_family'].setChecked(False)
    w.selection_pref_actions['across_tactics'].setChecked(False)
    w.clear_selection()
    for field in ('description','data_sources'): w.search_field_actions[field].setChecked(True)
    for field in ('name','id'):w.search_field_actions[field].setChecked(False)
    w.ttp_search.setText('Golden description phrase ');w.apply_ttp_search()
    check(w.ttp_search.text().endswith(' '),'search retains editable trailing space')
    check(all(w.proxy.mapFromSource(item.index()).isValid() for item in w.items_by_id[root]),'sidebar Description search finds matching occurrences')
    check(not w.proxy.mapFromSource(w.items_by_id[beta][0].index()).isValid(),'Description-only sidebar excludes unrelated technique')
    for layout in ('Flat','Side','Mini'):
        matrix.view_layout.setCurrentText(layout);wait(lambda:not matrix.building,'search '+layout)
        matrix.search.setText('ResearchSensor')
        check(matrix.scope_keys('search')=={beta},layout+' search batch targets direct data-source matches')
        w.select_ttp_batch('replace','search','execution')
        check(document.selected=={beta},layout+' search selection follows active fields')
    check(len(matrix_scene(document,query='ResearchSensor')['columns'])==1,'SVG/Excel projection uses same extended search fields')
    w.search_field_actions['description'].setChecked(False)
    w.search_field_actions['data_sources'].setChecked(False)
    check(document.search_fields==['data_sources'] and w.search_field_actions['data_sources'].isChecked(),'last enabled search field cannot be disabled')
    w.switch_category('Mitigations')
    check(w.ttp_search.isHidden() and w.ttp_search_fields_button.isHidden(),'Mitigation sidebar hides TTP-only search controls')
    w.configure_bulk_action(catalog.domain,mitigation)
    check(w.bulk_add_button.isEnabled() and w.bulk_remove_button.isEnabled(),'Mitigation detail offers both add/remove controls')
    w.clear_selection();w.select_matrix_ttp(legacy,True,'execution')
    update_annotation(document,beta,'','Preserve annotation',5,'#55aa33')
    before=deepcopy(document.navigator_layer)
    w.bulk_add_button.click()
    check(document.selected=={legacy,root,beta},'Mitigation add includes active direct targets and keeps unrelated selection')
    w.bulk_remove_button.click()
    check(document.selected=={legacy} and document.navigator_layer==before,'Mitigation remove preserves unrelated selection and all annotations')
    w.open_matrix();wait(lambda:not matrix.building,'source matrix')
    matrix.source_kind.setCurrentText('Mitigation')
    label=next(text for text,key in matrix.source_entries.items() if key==mitigation)
    matrix.source_picker.setEditText(label);matrix.update_source_state()
    check(matrix.source_selection()[1]=={root,beta},'Mitigation dropdown resolves exact active mitigates targets')
    matrix.add_source_button.click();matrix.remove_source_button.click()
    check(document.selected=={legacy},'matrix Mitigation add/remove matches detail controls')
    matrix.source_picker.setEditText('Research');matrix.update_source_state()
    check(not matrix.add_source_button.isEnabled() and not matrix.remove_source_button.isEnabled(),'partial typed source text cannot execute stale entry')
    matrix.source_picker.setEditText(next(text for text,key in matrix.source_entries.items() if key==empty));matrix.update_source_state()
    check(not matrix.add_source_button.isEnabled() and not matrix.remove_source_button.isEnabled(),'Mitigation with only revoked edges cannot change selection')
    before=document.fingerprint()
    check(not w.change_source_ttps('mobile-attack',mitigation,'add') and document.fingerprint()==before,'wrong-domain source operation rejected without mutation')

    log('[Selection/Search 5/6] Scoped batch edits, formulas and persistence')
    w.clear_selection();w.select_matrix_ttp(root,True,'execution')
    update_annotation(document,root,'','Global fallback',4,'#abcdef')
    preserved=deepcopy(document.navigator_layer)
    w.set_technique_states({root},False,respect_selection=True)
    from ttp_operations import effective_row
    check(not effective_row(document,root,'execution')['enabled'] and effective_row(document,root,'initial-access').get('enabled',True),'selected-state action edits only selected occurrences')
    dialog=BatchEditDialog(document,{root},w)
    check(dialog.scope.currentData()=='__selected__','batch editor defaults to selected occurrences for partial selection')
    dialog.reject()
    batch_patch(document,{root},{'comment':'Execution only','score':8,'enabled':True},'__selected__',log)
    check(effective_row(document,root,'execution')['comment']=='Execution only' and effective_row(document,root,'initial-access')['comment']=='Global fallback','atomic partial batch preserves unselected global fallback')
    before=deepcopy(document.navigator_layer)
    bad(lambda:batch_patch(document,{root},{'color':'invalid'},'__selected__',log),'invalid selected-occurrence batch rejected')
    check(document.navigator_layer==before,'failed selected-occurrence batch preserves entire layer')
    formula=calculate_layer([document],'a','Scoped formula',notify=log)
    check(selected_cells(formula)=={(root,'execution')},'score formula does not expand source selection to other tactics')
    layer=document_layer(document)
    restored=imported_document(layer,catalog)
    check(restored.selection_scopes==document.selection_scopes and restored.selection_preferences==document.selection_preferences,'Navigator exchange restores occurrence scopes and standard preferences')
    check(restored.search_fields==document.search_fields,'Navigator exchange restores Studio search fields extension')
    without_extension=deepcopy(layer);without_extension.pop('x_ttp_studio_selection_scopes')
    check(imported_document(without_extension,catalog).selection_scopes==document.selection_scopes,'standard per-tactic Navigator rows restore scopes without Studio extension when across selection is off')
    bad(lambda:validate_layer({**layer,'selectTechniquesAcrossTactics':'false'}),'Navigator validates standard preference booleans')
    invalid_layer=deepcopy(layer);invalid_layer['x_ttp_studio_selection_scopes']={root:['invalid']}
    invalid_path=OUT/'invalid-scope.navigator.json';invalid_path.write_text(json.dumps(invalid_layer),encoding='utf-8')
    import_dialog=ImportLayerDialog(DATA,invalid_path,catalog,w);import_dialog.show()
    wait(lambda:bool(import_dialog.results) and not import_dialog.busy and not import_dialog.pending_resolve,
         'invalid scope preview')
    check(import_dialog.preview is None and not import_dialog.import_button.isEnabled()
          and 'unmapped tactic' in import_dialog.results[0]['error'],
          'invalid Navigator occurrence extension is rejected during preview')
    emitted=[];import_dialog.imported.connect(emitted.append)
    import_dialog.commit()
    check(not emitted and import_dialog.isVisible(),'invalid Navigator occurrence extension cannot commit or close preview')
    import_dialog.reject()
    check(next(row for row in layer['techniques'] if row['techniqueID']=='T1000' and not row.get('tactic'))['metadata'][-1]['value']=='false','global annotation marker does not broaden partial inclusion')
    saved=save_studio(document,OUT/'selection.studio.json',log,True)
    reopened=open_studio(DATA,saved.save_path,log)
    check(saved.content_token()==reopened.content_token() and not reopened.dirty,'Studio save/reopen preserves scopes, fields, preferences and all data')
    export_document_csv(document,OUT/'selection.csv',log)
    with (OUT/'selection.csv').open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    check(json.loads(rows[0]['selected_tactics'])==['execution'],'CSV records selected tactics separately from all mapped tactics')
    session=OUT/'session.json';write_session(session_payload([reopened],0,{'page':'matrix'}),session,log)
    check(read_session(DATA,session,log)['documents'][0].content_token()==reopened.content_token(),'session recovery preserves exact partial selections and preferences')
    snap=snapshot_document(document);snap.selection_scopes[root].append('initial-access')
    check(document.selection_scopes[root]==['execution'],'background snapshot scopes are independently copied')
    payload=document_payload(reopened)
    for field,value in [('selection_scopes',{root:['invalid']}),('selection_preferences',{'across_tactics':1,'with_family':False}),('search_fields',[])]:
        candidate=deepcopy(payload);candidate[field]=value
        bad(lambda p=candidate:StudioReader(DATA,log).document(p),'Studio rejects invalid '+field)
    preview=upgrade_preview(document,catalog)
    decisions=[{k:row[k] for k in ('target_id','target_scope','action','reviewed')} for row in preview['rows']]
    migrated=migrate_layer(document,catalog,decisions,'Scoped migration',log)
    check(selected_cells(migrated)=={(root,'execution')} and migrated.selection_preferences==document.selection_preferences,'reviewed migration preserves scoped selection and preferences')
    duplicate_source=deepcopy(document.selection_scopes)
    w.duplicate_navigator_layer();wait(lambda:w.loaded_ok,'duplicate')
    check(w.current_document.selection_scopes==duplicate_source and w.current_document.selection_scopes is not document.selection_scopes,'duplicate layer copies independent occurrence state')
    w.grab().save(str(OUT/'selection-search-preview.png'))
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Discard):w.close()

    log('[Selection/Search 6/6] Pointer isolation and report')
    check(all(p.read_bytes()==value for p,value in pointers.items()),'all selection/search/source workflows leave official pointers unchanged')
    report=OUT/'audit.json';report.write_text(json.dumps({'passed':True,'assertions':len(CHECKS),'checks':CHECKS},ensure_ascii=False,indent=2),encoding='utf-8')
    log(f'PASS: {len(CHECKS)} assertions; report: {report.resolve()}')


if __name__=='__main__':main()
