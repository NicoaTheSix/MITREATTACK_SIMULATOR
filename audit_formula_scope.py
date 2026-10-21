"""NAV-019 official missing-score/scope, native UI and persistence audit. Flow: README.md."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import math
import uuid
from dataclasses import replace
from PySide6 import QtWidgets
from attack_catalog import external_id, load_catalog, tactic_phases
from audit_formula_features import Harness, wait
from custom_sources import load_custom
from layer_analysis import calculate_layer
from layer_analysis_dialogs import FormulaDialog
from localization import language_manager
from main import configure_application
from navigator_integration import document_layer, imported_document
from navigator_visuals import LayerAppearance
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument
from ttp_selection import assign_cells, selected_cells

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'/'attack'
REF=ROOT/'scripts'/'formula-reference'
OUT=ROOT/'artifacts'/'formula-scope'
CACHE=OUT/'cache'
CHECKS=[]


def log(message,current=0,total=0):
    print(message+(f' ({current}/{total})' if total else ''),flush=True)


def check(value,label):
    if not value: raise AssertionError(label)
    CHECKS.append(label)


def bad(task,label):
    try: task()
    except ValueError: check(True,label)
    else: raise AssertionError(label)


def fixture(matrix):
    domain,chain='formula-lab','formula-lab-chain'
    def obj(kind,name,**fields):
        return {'id':kind+'--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'formula-lab/'+name)),
                'type':kind,'name':name,'x_mitre_domains':[domain],**fields}
    slugs=list(dict.fromkeys(cell['tactic'] for cell in matrix))
    tactics=[obj('x-mitre-tactic',slug,x_mitre_shortname=slug,
                 external_references=[{'source_name':domain,'external_id':'TACTIC-'+slug}]) for slug in slugs]
    objects=[*tactics,obj('x-mitre-matrix','Scope Matrix',tactic_refs=[o['id'] for o in tactics])]
    for identity in dict.fromkeys(cell['techniqueID'] for cell in matrix):
        objects.append(obj('attack-pattern',identity,external_references=[{'source_name':domain,'external_id':identity}],
            x_mitre_platforms=['ResearchOS'],kill_chain_phases=[{'kill_chain_name':chain,'phase_name':c['tactic']}
            for c in matrix if c['techniqueID']==identity]))
    return {'type':'bundle','id':'bundle--'+str(uuid.uuid5(uuid.NAMESPACE_DNS,'formula-scope')),
        'x_ttp_studio_domains':[{'id':domain,'name':'Formula Lab','kill_chain_name':chain,'reference_source':domain}],
        'objects':objects}


def documents(catalog,sources):
    result=[]
    for index,source in enumerate(sources):
        doc=TTPDocument('Source '+chr(97+index),catalog)
        doc.navigator_layer={'name':doc.name,'domain':catalog.domain,'techniques':deepcopy(source['rows']),
            'filters':{'platforms':[]},'hideDisabled':True,'layout':{'expandedSubtechniques':'none'}}
        result.append(doc)
    return result


def main():
    for path in (DATA/'latest.json',REF/'scope-cases.json',REF/'scope-golden.json'):
        log('Input file: '+str(path.resolve()))
    log('Input directory: '+str(DATA.resolve()))
    log('Output cache directory: '+str(CACHE.resolve()))
    for name in ('audit.json','scope-bundle.json','navigator.studio.json','session.json','navigator.png','navigator-zh.png'):
        log('Output file: '+str((OUT/name).resolve()))
    OUT.mkdir(parents=True,exist_ok=True)
    pointers={p:p.read_bytes() for p in (DATA/'active.json',DATA/'latest.json') if p.exists()}
    log('[Scope Audit 1/7] Verify golden source and isolated custom catalog',0,7)
    cases=json.loads((REF/'scope-cases.json').read_text())
    golden=json.loads((REF/'scope-golden.json').read_text())
    check(golden['inputSHA256']==sha256((REF/'scope-cases.json').read_bytes()).hexdigest(),'case bytes match pinned golden')
    check(golden['serviceSHA256']=='b973f8ef52435c256f30b32766f4a40811ddf32ea35eced03b172df8e85576e9','official method source pinned')
    check(golden['version']=='15.2.0','reference mathjs runtime pinned')
    payload=fixture(cases['matrix'])
    path=OUT/'scope-bundle.json'
    path.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    catalog=load_custom(CACHE,str(path),'1.0',log)['catalog']
    ids={external_id(o):key for key,o in catalog.records.items()}
    all_cells={(ids[c['techniqueID']],c['tactic']) for c in cases['matrix']}
    log('[Scope Audit 2/7] Compare complete per-tactic results with official method',1,7)
    for test,reference in zip(cases['cases'],golden['results'],strict=True):
        docs=documents(catalog,test['sources'])
        before=[doc.fingerprint() for doc in docs]
        result=calculate_layer(docs,test['expression'],'Official result',mode='navigator')
        appearance=LayerAppearance(result.navigator_layer)
        expected_selected=set()
        for cell in reference['cells']:
            actual=appearance.cell(cell['techniqueID'],cell['tactic'])
            expected=cell['score']
            check(actual['score'] is None if expected is None else actual['score'] is not None and
                  math.isclose(actual['score'],expected,rel_tol=1e-13,abs_tol=1e-14),
                  test['name']+': score '+cell['techniqueID']+'/'+cell['tactic'])
            check(actual['enabled']==cell['enabled'],test['name']+': state '+cell['techniqueID']+'/'+cell['tactic'])
            if expected is not None: expected_selected.add((ids[cell['techniqueID']],cell['tactic']))
        check(selected_cells(result)==expected_selected,test['name']+': only computed cells included')
        check([doc.fingerprint() for doc in docs]==before,test['name']+': sources unchanged')
        check(result.navigator_layer['x_ttp_studio_formula']['mode']=='navigator',test['name']+': operation mode recorded')
        log('[Scope Audit 2/7] Reference case',len(CHECKS),len(golden['results'])*11+3)
    log('[Scope Audit 3/7] Scope independence, inheritance, earlier mode and failure/cancel',2,7)
    docs=documents(catalog,cases['cases'][0]['sources'])
    a,b=docs
    reference=calculate_layer(docs,'a+b','Reference',mode='navigator')
    assign_cells(a,{(ids['T0001'],'execution')})
    variant=calculate_layer(docs,'a+b','Variant','zero',scope='matrix',mode='navigator')
    check(variant.navigator_layer['techniques']==reference.navigator_layer['techniques'],'selection/filters/scope/missing controls do not change Navigator results')
    studio=calculate_layer(docs,'a+b','Earlier Studio')
    check(not studio.selected and all('score' not in row for row in studio.navigator_layer['techniques']),'earlier selected/unscored behavior retained')
    studio_zero=calculate_layer(docs,'a+b','Earlier zero','zero')
    check(LayerAppearance(studio_zero.navigator_layer).cell('T0001','execution')['score']==0,'earlier disabled-as-missing zero behavior retained')
    blank=documents(catalog,[{'rows':[]},{'rows':[]}])
    empty=calculate_layer(blank,'a+b','All missing',mode='navigator')
    check(not empty.selected and empty.navigator_layer['techniques']==[],'all-missing operation creates valid empty enabled result')
    unmapped=documents(catalog,[{'rows':[{'techniqueID':'UNRESOLVED','score':99},
        {'techniqueID':'T0001','tactic':'','score':99}, {'techniqueID':'T0001','tactic':'unknown','score':99}]}])
    frozen=unmapped[0].fingerprint()
    check(not calculate_layer(unmapped,'a','Unmapped',mode='navigator').selected,'unresolved and unmapped tactic rows do not create active score targets')
    check(unmapped[0].fingerprint()==frozen,'unresolved original annotations remain intact')
    constant=calculate_layer(blank,'0 ? a : 50','Constant',mode='navigator')
    check(selected_cells(constant)==all_cells,'empty-scope lazy constant covers complete matrix without selection')
    check(constant.navigator_layer['x_ttp_studio_formula']['evaluation']=='constant','constant detection recorded')
    check(calculate_layer(docs,'a+b','Variable',mode='navigator').navigator_layer['x_ttp_studio_formula']['evaluation']=='scored-union','per-cell score union recorded')
    ann=documents(catalog,[{'rows':[]},{'rows':[{'techniqueID':'T0001','comment':'annotation only','score':9,'enabled':False}]}])
    inherited=calculate_layer(ann,'a','Annotations',inheritance={'comment':'b','enabled':'b'},mode='navigator')
    check(not inherited.selected and LayerAppearance(inherited.navigator_layer).cell('T0001','execution')['comment']=='annotation only','inheritance-only source retains notes but adds no computed scores')
    check(not LayerAppearance(inherited.navigator_layer).cell('T0001','execution')['enabled'],'explicit enabled inheritance still applies to unscored cell')
    before=[doc.fingerprint() for doc in docs]
    for expression in ('1/0','a/0','1e301','a**2','a=3','sqrt(-1)','unknown+1'):
        bad(lambda:calculate_layer(docs,expression,'Invalid',mode='navigator'),'bounded failure: '+expression)
    bad(lambda:calculate_layer(docs,'a','Invalid',mode='invalid'),'reject unknown operation mode')
    bad(lambda:calculate_layer(docs,'a','Invalid',syntax='studio',mode='navigator'),'Navigator data policy requires Navigator scalar syntax')
    bad(lambda:calculate_layer(docs,'a','Invalid',syntax=''),'empty syntax is not an implicit default')
    def cancel(message,current=0,total=0):
        if '[Formula 3/5]' in message: raise InterruptedError('cancelled')
    try: calculate_layer(docs,'a+b','Cancelled',notify=cancel,mode='navigator')
    except InterruptedError: check(True,'Navigator operation cancelled before publication')
    else: raise AssertionError('cancellation missing')
    check([doc.fingerprint() for doc in docs]==before,'failure/cancellation leave sources unchanged')
    bad(lambda:calculate_layer([a,TTPDocument('Other',replace(catalog,dataset_id='f'*64))],'a+b','Mixed',mode='navigator'),'mixed exact datasets rejected')
    log('[Scope Audit 4/7] Enterprise, Mobile and ICS without selection',3,7)
    official=load_catalog(DATA,log)
    for domain in ('enterprise-attack','mobile-attack','ics-attack'):
        current=official.for_domain(domain)
        key,obj=next((k,o) for k,o in current.records.items() if len(tactic_phases(o,domain)&current.tactics.keys())>=2)
        identity=external_id(obj)
        slugs=[s for s in current.tactic_order if s in tactic_phases(obj,domain)]
        sources=[{'rows':[{'techniqueID':identity,'tactic':slugs[0],'score':8,'enabled':False}]},
                 {'rows':[{'techniqueID':identity,'tactic':slugs[1],'score':0}]}]
        output=calculate_layer(documents(current,sources),'a+b',domain,mode='navigator')
        view=LayerAppearance(output.navigator_layer)
        check(view.cell(identity,slugs[0])['score']==8,domain+': disabled score used without selection')
        check(view.cell(identity,slugs[1])['score']==0,domain+': genuine zero is a scored candidate')
        check(selected_cells(output)=={(key,slugs[0]),(key,slugs[1])},domain+': independent tactic scope')
        full=calculate_layer(documents(current,[{'rows':[]}]),'0',domain+' constant',mode='navigator')
        expected={(k,s) for k,o in current.records.items() for s in tactic_phases(o,domain)&current.tactics.keys()}
        check(selected_cells(full)==expected,domain+': zero constant initializes every active mapped cell')
    log('[Scope Audit 5/7] Studio/Navigator/recovery provenance including old records',4,7)
    save_studio(reference,OUT/'navigator.studio.json',log,save_as=True)
    record=reference.navigator_layer['x_ttp_studio_formula']
    check(record['missing']=='zero-if-any-score' and record['scope']=='navigator','effective policy recorded instead of ignored Studio controls')
    check(open_studio(CACHE,OUT/'navigator.studio.json',log).navigator_layer['x_ttp_studio_formula']==record,'Studio mode provenance round trip')
    check(imported_document(document_layer(reference),catalog,'enabled').navigator_layer['x_ttp_studio_formula']==record,'Navigator mode provenance round trip')
    write_session(session_payload([reference,empty,constant],0,{}),OUT/'session.json',log)
    recovered=read_session(CACHE,OUT/'session.json',log)['documents']
    check([doc.navigator_layer['x_ttp_studio_formula']['mode'] for doc in recovered]==['navigator']*3,'recovery retains operation mode for populated/empty/constant layers')
    old=deepcopy(document_layer(studio_zero))
    old['x_ttp_studio_formula'].pop('mode')
    check('mode' not in imported_document(old,catalog,'enabled').navigator_layer['x_ttp_studio_formula'],'historical mode omission preserved without recalculation')
    log('[Scope Audit 6/7] Native mode controls, language, worker retry and installation',5,7)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    parent=Harness()
    dialog=FormulaDialog(docs,a,parent)
    dialog.show()
    app.processEvents()
    check(dialog.calculation_mode.currentData()=='studio','new UI retains Studio data policy default')
    dialog.syntax.setCurrentIndex(dialog.syntax.findData('studio'))
    dialog.scope.setCurrentIndex(dialog.scope.findData('matrix'))
    dialog.missing.setCurrentIndex(dialog.missing.findData('zero'))
    dialog.calculation_mode.setCurrentIndex(dialog.calculation_mode.findData('navigator'))
    check(dialog.syntax.currentData()=='navigator' and not dialog.syntax.isEnabled(),'Navigator mode fixes scalar syntax')
    check(not dialog.scope.isEnabled() and not dialog.missing.isEnabled(),'inactive Studio policy controls disabled')
    dialog.calculation_mode.setCurrentIndex(dialog.calculation_mode.findData('studio'))
    check(dialog.syntax.currentData()=='studio' and dialog.syntax.isEnabled(),'previous scalar syntax restored on return')
    check(dialog.scope.currentData()=='matrix' and dialog.missing.currentData()=='zero','previous Studio policy choices preserved')
    dialog.calculation_mode.setCurrentIndex(dialog.calculation_mode.findData('navigator'))
    manager=language_manager()
    manager.set_language('zh_TW')
    manager.refresh_all()
    app.processEvents()
    check(manager.translate(dialog.calculation_mode.currentText())!=dialog.calculation_mode.currentText(),'Navigator mode has Taiwan translation')
    check(dialog.calculation_scroll.widgetResizable(),'calculation page can scroll on smaller displays')
    check(dialog.mode_hint.height()>=dialog.mode_hint.heightForWidth(dialog.mode_hint.width()),'wrapped mode instructions have room for every line')
    check(dialog.grab().save(str(OUT/'navigator-zh.png')),'translated native mode preview')
    manager.set_language('en')
    check(dialog.grab().save(str(OUT/'navigator.png')),'English native mode preview')
    dialog.expression.setText('a/0')
    dialog.calculate()
    wait(lambda:not dialog.worker.isRunning() and dialog.create_button.isEnabled())
    check(not parent.installed and dialog.result_document is None,'native numeric failure installs no partial tab')
    dialog.expression.setText('a+b')
    dialog.calculate()
    check(not dialog.options_tabs.isEnabled(),'mode/settings freeze during background calculation')
    wait(lambda:dialog.result_document is not None and not dialog.worker.isRunning())
    check(dialog.result_document.navigator_layer['techniques']==reference.navigator_layer['techniques'],'native worker installs exact Navigator policy results')
    check(len(parent.installed)==1 and parent.opened,'one independent native result tab')
    check(any('[Formula 5/5]' in row[0] for row in parent.messages),'five-stage operation progress remains visible')
    parent.close()
    app.processEvents()
    check(all(p.read_bytes()==data for p,data in pointers.items()),'official pointers unchanged')
    log('[Scope Audit 7/7] Publish report',6,7)
    (OUT/'audit.json').write_text(json.dumps({'passed':True,'count':len(CHECKS),
        'reference_cases':len(golden['results']),'reference_cells':sum(len(r['cells']) for r in golden['results']),
        'checks':CHECKS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log(f'[Scope Audit] PASS: {len(CHECKS)} checks',7,7)


if __name__=='__main__': main()
