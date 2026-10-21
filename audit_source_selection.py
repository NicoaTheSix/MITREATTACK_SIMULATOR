"""Audit source-result unions and explicit detection/asset mappings. Flow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import csv
import json
import uuid
from unittest.mock import patch
from PySide6 import QtCore, QtWidgets
from audit_visibility_presets import fixture as base_fixture, wait
from attack_catalog import DOMAIN_LABELS, DOMAIN_KILL_CHAINS, external_id, local_path, load_catalog
from attack_versions import snapshot_pointer
from custom_sources import load_custom, custom_catalog
from main import MainWindow, ROLE_CONTEXT, configure_application
from navigator_integration import document_layer, imported_document
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument, export_document_csv
from ttp_selection import selected_cells
from ttp_sources import source_choices, resolve_sources, SOURCE_TYPES

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'attack'
OUT=ROOT/'artifacts'/'source-selection'
CHECKS=[]


def log(text,current=0,total=0): print(text+(f' ({current}/{total})' if total else ''),flush=True)


def check(value,text):
    if not value: raise AssertionError(text)
    CHECKS.append(text)


def bad(task,text):
    try: task()
    except (ValueError,TypeError): check(True,text)
    else: raise AssertionError(text)


def fixture():
    bundle=base_fixture()
    objects=bundle['objects']
    by_id={external_id(o):o for o in objects if external_id(o)}
    root,child,beta,legacy=[by_id[key] for key in ('T1000','T1000.001','T1001','T1002')]
    strategy=next(o for o in objects if o.get('name')=='Strategy fixture')
    analytic=next(o for o in objects if o.get('name')=='Analytic fixture')
    component=next(o for o in objects if o.get('name')=='Proc Sensor Creation')
    source=next(o for o in objects if o.get('name')=='ResearchProcess')
    for obj,identity,tag in [(strategy,'DET1000','strategy'),(analytic,'AN1000','analytic'),
                             (component,'DC1000','component'),(source,'DS1000','source')]:
        obj.update(external_references=[{'source_name':'mitre-attack','external_id':identity}],x_fixture=tag)
    def obj(kind,tag,**fields):
        return {'type':kind,'id':kind+'--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'source selection '+tag)),
                'name':tag,'x_mitre_domains':['enterprise-attack'],'x_fixture':tag,**fields}
    def edge(kind,a,b,tag,**fields):
        return obj('relationship',tag,relationship_type=kind,source_ref=a['id'],target_ref=b['id'],**fields)
    asset=obj('x-mitre-asset','asset',external_references=[{'source_name':'mitre-attack','external_id':'A1000'}])
    second=obj('x-mitre-detection-strategy','second-strategy',name=strategy['name'],
               x_mitre_analytic_refs=[analytic['id']],description='Shared result phrase with spaces',
               external_references=[{'source_name':'mitre-attack','external_id':'DET1001'}])
    strategy['description']='Shared result phrase with spaces'
    duplicate=obj('x-mitre-data-component','same-label-component',name=component['name'],
                  x_mitre_data_source_ref=source['id'],external_references=deepcopy(component['external_references']))
    group=obj('intrusion-set','second-group',name='Research G1001',description='Batch group phrase',
              external_references=[{'source_name':'mitre-attack','external_id':'G1001'}])
    dead=obj('x-mitre-detection-strategy','revoked-strategy',revoked=True,x_mitre_analytic_refs=[analytic['id']])
    dead_analytic=obj('x-mitre-analytic','deprecated-analytic',x_mitre_deprecated=True,
                      x_mitre_log_source_references=[{'x_mitre_data_component_ref':component['id']}])
    orphan=obj('x-mitre-detection-strategy','orphan-strategy',x_mitre_analytic_refs=[dead_analytic['id'],
                   'x-mitre-analytic--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'missing analytic'))])
    objects.extend([asset,second,duplicate,group,dead,dead_analytic,orphan,
        edge('targets',root,asset,'asset-target'),edge('targets',legacy,asset,'revoked-target',revoked=True),
        edge('targets',asset,beta,'wrong-direction'),edge('uses',asset,beta,'wrong-uses'),
        edge('detects',component,child,'legacy-component-detects',description='Legacy direct observation'),
        edge('detects',second,root,'second-detects'),edge('detects',dead,legacy,'dead-strategy-detects'),
        edge('detects',orphan,legacy,'orphan-detects'),edge('detects',strategy,legacy,'deprecated-detects',x_mitre_deprecated=True),
        edge('uses',group,root,'shared-group-target'),edge('uses',group,child,'group-child')])
    # Identical ATT&CK IDs across different domains must never bridge STIX refs.
    original=deepcopy(objects)
    for domain in ('mobile-attack','ics-attack'):
        remap={o['id']:o['type']+'--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,domain+o['id'])) for o in original}
        def convert(value):
            if isinstance(value,str): return remap.get(value,value)
            if isinstance(value,list): return [convert(v) for v in value]
            if isinstance(value,dict): return {k:convert(v) for k,v in value.items()}
            return value
        for raw in original:
            clone=convert(raw)
            clone['x_mitre_domains']=[domain]
            for phase in clone.get('kill_chain_phases',[]): phase['kill_chain_name']=DOMAIN_KILL_CHAINS[domain]
            objects.append(clone)
    return bundle


def main():
    log('Input directory: '+str(DATA.resolve()))
    log('Output directory: '+str(OUT.resolve()))
    for name in ('fixture.json','settings.ini','state.studio.json','session.json','state.csv','batch.png','component.png','audit.json'):
        log('Output file: '+str((OUT/name).resolve()))
    log('[Source Audit 1/7] Loading isolated multi-domain mappings',0,7)
    OUT.mkdir(parents=True,exist_ok=True)
    pointers={p:p.read_bytes() for p in (DATA/'latest.json',DATA/'active.json') if p.exists()}
    payload=fixture()
    path=OUT/'fixture.json';path.write_text(json.dumps(payload),encoding='utf-8')
    catalog=load_custom(DATA,str(path),'19.2',log)['catalog']
    for domain in DOMAIN_LABELS:
        scoped=catalog.for_domain(domain)
        store=scoped.objects_by_domain[domain]
        tags={o.get('x_fixture'):key for key,o in store.items() if o.get('x_fixture')}
        ids={external_id(o):key for key,o in scoped.records.items()}
        root,child,beta,legacy=[ids[i] for i in ('T1000','T1000.001','T1001','T1002')]
        for tag,expected in [('asset',{root}),('strategy',{beta}),('second-strategy',{root}),
                             ('component',{root,child,beta}),('source',{root,child,beta}),
                             ('same-label-component',set()),('orphan-strategy',{legacy})]:
            check(resolve_sources(scoped,{tags[tag]})==expected,domain+' exact mappings: '+tag)
        rows=scoped.techniques_by_source[domain][tags['component']]
        check({row['mapping_type'] for row in rows}=={'detects','strategy-analytic-component'},domain+' keeps direct vs derived provenance')
        check(legacy not in resolve_sources(scoped,{tags['component']}),domain+' missing/deprecated analytics do not leak mappings')
        labels=source_choices(scoped,'Data Component',['name','id','description'])
        check(len(labels)==len({r['label'] for r in labels}) and all('ResearchProcess :' in r['label'] for r in labels),domain+' grouped component labels are unambiguous')
        check(all('DS1000' in row['search'] for row in labels),domain+' component search includes exact parent source')
        for tag in ('revoked-strategy','deprecated-analytic'):
            key=next(o['id'] for o in payload['objects'] if o.get('x_fixture')==tag and domain in o['x_mitre_domains'])
            bad(lambda key=key:resolve_sources(scoped,{tags['strategy'],key}),domain+' rejects mixed inactive source batch atomically')
    for field,value,kind in [('x_mitre_analytic_refs',[{}],'x-mitre-detection-strategy'),
                             ('x_mitre_data_source_ref',{},'x-mitre-data-component'),
                             ('x_mitre_log_source_references',[{'x_mitre_data_component_ref':[]}],'x-mitre-analytic')]:
        draft=deepcopy(payload);next(o for o in draft['objects'] if o['type']==kind)[field]=value
        bad(lambda draft=draft:custom_catalog(draft,'f'*64,'in-memory','19.2',lambda *args:None),'malformed reference rejected: '+field)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    w=MainWindow(DATA,DATA/'latest.json',settings_path=OUT/'settings.ini');w.resize(1850,1100);w.show()
    try:
        wait(lambda:w.loaded_ok and not w.loader.isRunning())
        official=w.catalog
        log('[Source Audit 2/7] Independent official relationship reference checks',1,7)
        pointer=json.loads((DATA/'latest.json').read_text(encoding='utf-8-sig'))
        for domain,field in [('enterprise-attack','enterprise_bundle'),('mobile-attack','mobile_bundle'),('ics-attack','ics_bundle')]:
            source_path=local_path(DATA,pointer[field]);log('Input file: '+str(source_path))
            raw=json.loads(source_path.read_text(encoding='utf-8-sig'))['objects']
            current=official.for_domain(domain);store=current.objects_by_domain[domain]
            expected={}
            for edge in raw:
                if edge.get('type')!='relationship' or edge.get('revoked') or edge.get('x_mitre_deprecated'): continue
                a,b=store.get(edge.get('source_ref'),{}),store.get(edge.get('target_ref'),{})
                if edge.get('relationship_type')=='targets' and a.get('type')=='attack-pattern' and b.get('type')=='x-mitre-asset':
                    expected.setdefault(b['id'],set()).add(a['id'])
                if edge.get('relationship_type')=='detects' and a.get('type') in ('x-mitre-detection-strategy','x-mitre-data-component') and b.get('type')=='attack-pattern':
                    expected.setdefault(a['id'],set()).add(b['id'])
            for key,targets in expected.items():
                indexed=resolve_sources(current,{key})
                check(targets <= indexed if store[key]['type']=='x-mitre-data-component' else targets==indexed,domain+' official direct mappings '+key)
            # Independent reverse traversal: each component gathers strategy targets
            # only when an active analytic explicitly references that component.
            components={key:set(expected.get(key,set())) for key,obj in store.items() if obj.get('type')=='x-mitre-data-component'}
            for strategy in store.values():
                if strategy.get('type')!='x-mitre-detection-strategy': continue
                for ref in strategy.get('x_mitre_analytic_refs',[]):
                    analytic=store.get(ref,{})
                    if analytic.get('type')!='x-mitre-analytic': continue
                    for field_name in ('x_mitre_log_source_references','x_mitre_log_sources'):
                        for row in analytic.get(field_name,[]):
                            key=row.get('x_mitre_data_component_ref')
                            if key in components: components[key].update(expected.get(strategy['id'],set()))
            for key,targets in components.items():
                check(resolve_sources(current,{key})==targets,domain+' official component full path union '+key)
            for key,obj in store.items():
                if obj.get('type')!='x-mitre-data-source': continue
                targets=set().union(*(targets for component,targets in components.items() if store[component].get('x_mitre_data_source_ref')==key))
                check(resolve_sources(current,{key})==targets,domain+' official data source component union '+key)
            check(bool(expected),domain+' contains official new source mappings')
        if (DATA/'v11.3'/'manifest.json').exists():
            old=load_catalog(DATA,log,snapshot_pointer(DATA,'11.3'))
            check(not source_choices(old,'Detection Strategy',['name','id','description']),'cached v11.3 has an empty strategy picker without borrowing newer objects')
            check(any(o.get('type')=='x-mitre-data-component' for o in old.objects_by_domain[old.domain].values()),'cached v11.3 exercises legacy components')
        doc=TTPDocument('Source unions',catalog,navigator_layer={'name':'Source unions','domain':catalog.domain,
            'techniques':[{'techniqueID':'T1000.001','score':0,'color':'#123456','enabled':False,'comment':'Keep this note',
                           'links':[{'label':'Reference','url':'https://example.org/'}],'metadata':[{'name':'Owner','value':'Blue'}]}]})
        w.install_imported_document(doc);wait(lambda:w.loaded_ok)
        w.open_matrix();m=w.matrix_view;wait(lambda:not m.building)
        store=catalog.objects_by_domain[catalog.domain]
        tags={o.get('x_fixture'):key for key,o in store.items() if o.get('x_fixture')}
        ids={external_id(o):key for key,o in catalog.records.items()}
        root,child,beta,legacy=[ids[i] for i in ('T1000','T1000.001','T1001','T1002')]
        log('[Source Audit 3/7] Sidebar result unions, overlap and empty queries',2,7)
        w.switch_category('Groups');w.search.setText('Research G');w.apply_search()
        check(len(w.library_result_keys())==2,'sidebar result count excludes other domains')
        w.choose_technique_occurrence(legacy,True)
        annotations=deepcopy(doc.navigator_layer)
        w.add_library_results_button.click()
        check(w.selected=={root,child,legacy},'sidebar union deduplicates overlap and preserves unrelated choices')
        w.remove_library_results_button.click()
        check(w.selected=={legacy},'sidebar removes union once, leaving unrelated choices')
        check(doc.navigator_layer==annotations,'source union preserves annotations')
        before=doc.fingerprint();w.search.setText('no such source');w.apply_search()
        check(not w.add_library_results_button.isEnabled() and not w.change_library_results('add') and doc.fingerprint()==before,'empty source results are a no-op')
        w.search.clear();w.apply_search()
        check(len(w.library_result_keys())==2,'blank query means all supported sources in active category/domain')
        stale=replace(catalog,dataset_id='e'*64)
        check(not w.change_sources_ttps(stale,{tags['strategy']},'add') and doc.fingerprint()==before,'stale dataset batch rejected')
        check(not w.change_sources_ttps(catalog,{tags['strategy'],'missing'},'add') and doc.fingerprint()==before,'one invalid source prevents partial commit')
        check(not w.change_source_ttps('ics-attack',tags['strategy'],'add'),'different domain action rejected')
        w.change_source_search_field('name',False);w.change_source_search_field('id',False)
        w.search.setText('Batch group phrase');w.apply_search()
        check(w.library_result_keys()=={tags['second-group']},'sidebar batch follows Description-only fields and literal spaces')
        w.change_source_search_field('name',True);w.change_source_search_field('id',True)
        log('[Source Audit 4/7] Matrix result batches and per-source details',3,7)
        w.open_matrix();wait(lambda:not m.building)
        m.source_kind.setCurrentText('Detection Strategy');m.source_picker.setEditText('shared result PHRASE with spaces')
        m.update_source_state()
        check(len(m.source_result_keys())==2 and not m.add_source_button.isEnabled() and m.add_source_results_button.isEnabled(),'partial description query enables only matching-results batch')
        m.add_source_results_button.click()
        check(w.selected=={root,beta,legacy},'matrix result union handles same-name strategy IDs separately')
        m.remove_source_results_button.click();check(w.selected=={legacy},'matrix result remove round trip')
        for kind,tag,targets in [('Asset','asset',{root}),('Detection Strategy','strategy',{beta}),
                                  ('Data Component','component',{root,child,beta}),('Data Source','source',{root,child,beta})]:
            w.clear_selection();w.open_matrix();wait(lambda:not m.building)
            m.source_kind.setCurrentText(kind)
            index=next(i for i in range(m.source_picker.count()) if m.source_picker.itemData(i)==tags[tag])
            m.source_picker.setCurrentIndex(index);m.update_source_state()
            check(m.source_selection()[1]==targets,kind+' exact source selection')
            m.add_source_button.click();check(w.selected==targets,kind+' Add button')
            m.remove_source_button.click();check(not w.selected,kind+' Remove button')
            m.source_details_button.click()
            check(w.library_detail_context==(catalog.domain,tags[tag]) and w.bulk_add_button.isEnabled(),kind+' opens exact source details with add/remove')
            if kind=='Data Component':
                check('Explicit reference path (derived mapping)' in w.details.toPlainText(),'component details distinguish derived paths')
                check('Data Source: ResearchProcess' in w.details.toPlainText(),'component details link source group')
                check(w.details.grab().save(str(OUT/'component.png')),'component screenshot')
            w.bulk_add_button.click();check(w.selected==targets,kind+' detail Add button')
            w.bulk_remove_button.click();check(not w.selected,kind+' detail Remove button')
        w.switch_category('Detections');w.search.setText('Analytic fixture');w.apply_search()
        check(not w.library_result_keys() and not w.add_library_results_button.isEnabled(),'Analytics remain browse-only, not ambiguous source results')
        log('[Source Audit 5/7] Visibility/family preferences and stale UI protection',4,7)
        w.open_matrix();wait(lambda:not m.building)
        m.view_layout.setCurrentText('Flat');m.platform.setCurrentText('Windows');wait(lambda:not m.building)
        m.collapse_button.click();w.clear_selection()
        doc.selection_preferences.update(with_family=True,visible_only=True,across_tactics=False)
        w.change_source_ttps(catalog.domain,tags['component'],'add')
        check(w.selected=={root} and (child,'execution') not in selected_cells(doc),'visible-only runs after family expansion, excluding collapsed children and Linux')
        doc.selection_preferences.update(with_family=False,visible_only=False,across_tactics=True)
        w.clear_selection();w.change_source_ttps(catalog.domain,tags['component'],'add')
        m.source_kind.setCurrentText('Asset');m.source_picker.setCurrentIndex(0)
        other=TTPDocument('Other domain',catalog.for_domain('ics-attack'))
        w.install_imported_document(other);wait(lambda:w.loaded_ok)
        w.open_matrix();wait(lambda:not m.building)
        check(not m.source_picker.currentText() and not m.add_source_button.isEnabled(),'domain switch clears previous source choice')
        check(not w.change_sources_ttps(catalog,{tags['component']},'remove') and not other.selected,'old source catalog cannot modify new document')
        w.select_navigator_layer(doc.document_id);wait(lambda:w.loaded_ok and not m.building)
        check(w.selected=={root,child,beta},'document switch preserves independent source choices')
        row=next(row for row in doc.navigator_layer['techniques'] if row['techniqueID']=='T1000.001' and not row.get('tactic'))
        preserved={key:row.get(key) for key in annotations['techniques'][0]}
        preserved['metadata']=[entry for entry in preserved['metadata'] if entry.get('name')!='TTP Selection Studio selected']
        check(preserved==annotations['techniques'][0],'all source operations preserve disabled state, zero score, color, note, links and metadata')
        m.source_kind.setCurrentText('Data Component');m.source_picker.setEditText('researchprocess');m.update_source_state()
        check(m.grab().save(str(OUT/'batch.png')),'source batch screenshot')
        log('[Source Audit 6/7] Studio/Navigator/CSV/recovery persistence',5,7)
        save_studio(doc,OUT/'state.studio.json',log)
        restored=open_studio(DATA,OUT/'state.studio.json',log)
        check(restored.selected==doc.selected and restored.selection_scopes==doc.selection_scopes,'Studio source-derived selection round trip')
        exchanged=imported_document(document_layer(doc),catalog)
        check(exchanged.selected==doc.selected,'Navigator source-derived selection round trip')
        export_document_csv(doc,OUT/'state.csv',log)
        with (OUT/'state.csv').open(encoding='utf-8-sig',newline='') as stream:
            check({row['technique_id'] for row in csv.DictReader(stream)}=={'T1000','T1000.001','T1001'},'CSV exports deduplicated selected IDs')
        write_session(session_payload([doc,other],0,{}),OUT/'session.json',log)
        recovered=read_session(DATA,OUT/'session.json',log)
        check(recovered['documents'][0].selected==doc.selected and not recovered['documents'][1].selected,'session preserves isolated domain documents')
        log('[Source Audit 7/7] Pointer preservation and verified report',6,7)
        check(all(p.read_bytes()==value for p,value in pointers.items()),'official snapshot pointers unchanged')
        (OUT/'audit.json').write_text(json.dumps({'passed':len(CHECKS),'checks':CHECKS},indent=2),encoding='utf-8')
        log(f'[Source Audit] PASS: {len(CHECKS)} checks',7,7)
    finally:
        with patch.object(w,'confirm_studio_changes',return_value='discard'): w.close()
        QtWidgets.QApplication.processEvents()


if __name__=='__main__': main()
