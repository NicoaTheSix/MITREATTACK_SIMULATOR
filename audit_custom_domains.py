"""NAV-017 dataset-scoped definitions, matrix unions and complete UI/IO. Flow: README.md."""
from copy import deepcopy
from hashlib import sha256
import csv
import json
from pathlib import Path
import uuid
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id, catalog_identity, tactic_phases, DOMAIN_LABELS
from attack_matrix import matrix_columns
from audit_visibility_presets import wait
from audit_navigator_bundle import ready
from custom_sources import custom_catalog, load_custom
from custom_data_import import inspect_source, accept_source
from domain_model import domain_label
from main import MainWindow, configure_application
from navigator_dialogs import ImportLayerDialog, AnnotationDialog
from navigator_import import LayerImportResolver, build_import_documents
from navigator_integration import document_layer, imported_document, validate_layer, read_layers, export_layers, update_annotation, compare_documents
from source_dialogs import SourceDialog
from stix_clipboard import object_json
from studio_files import save_studio, open_studio, session_payload, write_session, read_session, StudioReader
from ttp_documents import TTPDocument, document_payload, export_document_csv
from ttp_sources import source_choices, resolve_sources
from ttp_selection import change_cells, selected_cells
from ttp_operations import batch_patch
from layer_analysis import calculate_layer
from layer_upgrade import upgrade_preview, migrate_layer
from matrix_exports import export_matrix, matrix_scene

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts' / 'custom-domains'
CACHE = OUT / 'cache'
CHECKS = []


def log(text, current=0, total=0):
    print(text + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, text):
    if not value:
        raise AssertionError(text)
    CHECKS.append(text)


def bad(task, text):
    try:
        task()
    except (ValueError, TypeError, KeyError, OSError):
        check(True, text)
    else:
        raise AssertionError(text)


def write(path, value):
    log('Output file: ' + str(path.resolve()))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def fixture():
    objects, definitions = [], []
    def obj(kind, domain, tag, **fields):
        return {'id': kind + '--' + str(uuid.uuid5(uuid.NAMESPACE_DNS, domain + '/' + tag)), 'type': kind,
                'name': tag, 'x_mitre_domains': [domain], **fields}
    for domain in ('lab-one', 'lab-two'):
        source, chain = domain + '-references', domain + '-chain'
        definitions.append({'id': domain, 'name': 'Research ' + domain, 'kill_chain_name': chain, 'reference_source': source})
        def ref(identity):
            return [{'source_name': 'mitre-attack', 'external_id': 'T1234'}, {'source_name': source, 'external_id': identity}]
        tactics = [obj('x-mitre-tactic', domain, slug, x_mitre_shortname=slug, external_references=ref('TACTIC-' + slug))
                   for slug in ('survey', 'execute', 'observe')]
        root = obj('attack-pattern', domain, 'Root', external_references=ref('LAB-ALPHA'), x_mitre_platforms=['ResearchOS'],
                   kill_chain_phases=[{'kill_chain_name': chain, 'phase_name': 'survey'}])
        child = obj('attack-pattern', domain, 'Child', external_references=ref('LAB-BETA.child'), x_mitre_is_subtechnique=True,
                    x_mitre_platforms=['ResearchOS'], kill_chain_phases=[{'kill_chain_name': chain, 'phase_name': 'execute'}])
        beta = obj('attack-pattern', domain, 'Observer', external_references=ref('LAB-GAMMA'), x_mitre_platforms=['ResearchOS'],
                   kill_chain_phases=[{'kill_chain_name': chain, 'phase_name': 'observe'}])
        group = obj('intrusion-set', domain, 'Research group', external_references=ref('LAB-GROUP'), description='Research group description')
        objects += [*tactics, root, child, beta, group,
            obj('x-mitre-matrix', domain, 'Primary Matrix', tactic_refs=[tactics[1]['id'], tactics[0]['id']]),
            obj('x-mitre-matrix', domain, 'Secondary Matrix', tactic_refs=[tactics[2]['id'], tactics[0]['id']]),
            obj('relationship', domain, 'parent', relationship_type='subtechnique-of', source_ref=child['id'], target_ref=root['id']),
            obj('relationship', domain, 'uses', relationship_type='uses', source_ref=group['id'], target_ref=child['id'], description='Custom procedure')]
    return {'type': 'bundle', 'id': 'bundle--' + str(uuid.uuid4()), 'x_ttp_studio_domains': definitions, 'objects': objects}


def main():
    log('Input directory: ' + str(DATA)); log('Output directory: ' + str(OUT))
    OUT.mkdir(parents=True, exist_ok=True); CACHE.mkdir(exist_ok=True)
    for p in (DATA/'active.json',DATA/'latest.json'): log('Input file: '+str(p))
    pointers = {p: p.read_bytes() for p in (DATA / 'active.json', DATA / 'latest.json')}
    log('[Domain Audit 1/7] Defining independent custom datasets', 0, 7)
    payload = fixture(); frozen = deepcopy(payload)
    source = OUT / 'research-bundle.json'; write(source, payload)
    loaded = load_custom(CACHE, str(source), '1.0', log)
    catalog = loaded['catalog']; second = catalog.for_domain('lab-two')
    key = lambda c, identity: next(k for k, o in c.records.items() if external_id(o) == identity)
    root, child = key(catalog, 'LAB-ALPHA'), key(catalog, 'LAB-BETA.child')
    check(catalog.domain == 'lab-one' and catalog.version == '1.0', 'non-official domain and independent release are supported')
    check(domain_label('lab-one', catalog) == 'Research lab-one', 'display name is distinct from domain identity')
    check(catalog.tactic_order == ['execute', 'survey', 'observe'], 'multiple matrices use ordered union without silently taking the first matrix')
    check(len(catalog.matrices_by_domain['lab-one']) == 2, 'both original Matrix objects remain addressable')
    check([slug for slug, _ in matrix_columns(catalog)] == catalog.tactic_order, 'matrix UI projection includes techniques from both matrices')
    check(tactic_phases(catalog.records[child], 'lab-one') == {'execute'}, 'configured domain kill chain resolves tactic mappings')
    check(external_id(catalog.records[root]) == 'LAB-ALPHA', 'configured reference source overrides unrelated official references')
    check(catalog.parents[child] == root, 'explicit sub-technique relationship works with non-ATT&CK IDs')
    check(key(second, 'LAB-ALPHA') != root, 'identical external IDs in distinct domains remain separate STIX records')
    check(json.loads(object_json(catalog, 'lab-one', child)) == next(o for o in payload['objects'] if o['id'] == child), 'source JSON excludes derived record-view metadata')
    check(payload == frozen, 'catalog projection never rewrites the Bundle')
    manual_example=ROOT/'manual'/'examples'/'custom_domain_bundle.json'
    example=load_custom(CACHE,str(manual_example),'1.0',log)['catalog']
    check(example.domain=='research-lab' and len(example.records)==2 and example.tactic_order==['observe','review'],
          'the bundled manual example loads with its documented domain and two-matrix order')
    altered = deepcopy(payload)
    altered['x_ttp_studio_domains'][0].update(name='Independent Lab', kill_chain_name='independent-chain', reference_source='independent-source')
    for obj in altered['objects']:
        if 'lab-one' in obj['x_mitre_domains']:
            for phase in obj.get('kill_chain_phases', []): phase['kill_chain_name'] = 'independent-chain'
            for ref in obj.get('external_references', []):
                if ref['source_name'] == 'lab-one-references': ref['source_name'] = 'independent-source'
    altered_path = OUT / 'other-bundle.json'; write(altered_path, altered)
    other = load_custom(CACHE, str(altered_path), '1.0', log)['catalog']
    check(catalog_identity(other) != catalog_identity(catalog), 'same domain/version/STIX IDs at another dataset hash stay isolated')
    check(domain_label('lab-one', other) == 'Independent Lab' and domain_label('lab-one', catalog) == 'Research lab-one', 'loading a same-name domain never modifies another catalog definition')
    check(tactic_phases(catalog.records[child], 'lab-one') == tactic_phases(other.records[child], 'lab-one') == {'execute'}, 'record views retain their own chain mapping after another source is loaded')
    check(set(DOMAIN_LABELS) == {'enterprise-attack', 'mobile-attack', 'ics-attack'}, 'official registry is not mutated by custom domains')
    log('[Domain Audit 2/7] Validation failures and inference', 1, 7)
    def validate(value): return custom_catalog(value, 'a' * 64, 'memory fixture', '1.0', log)
    for mutate, message in [
        (lambda p: p['x_ttp_studio_domains'].append(deepcopy(p['x_ttp_studio_domains'][0])), 'duplicate domain definition rejected'),
        (lambda p: p['x_ttp_studio_domains'][0].update(id='../bad'), 'invalid domain identifier rejected'),
        (lambda p: p['x_ttp_studio_domains'][0].update(reference_source='missing'), 'missing configured external-ID source rejected'),
        (lambda p: p['x_ttp_studio_domains'][0].update(kill_chain_name='missing'), 'missing configured kill chain rejected'),
        (lambda p: next(o for o in p['objects'] if o['id'] == child)['external_references'][-1].update(external_id='LAB-ALPHA'), 'ID collisions inside one domain rejected'),
        (lambda p: next(o for o in p['objects'] if o['id'] == child)['external_references'].append({'source_name':'lab-one-references','external_id':'CONFLICT'}), 'conflicting IDs in the same configured source rejected'),
        (lambda p: next(o for o in p['objects'] if o['type'] == 'x-mitre-matrix')['tactic_refs'].append('missing'), 'unresolved Matrix tactic reference rejected'),
        (lambda p: next(o for o in p['objects'] if o['type'] == 'x-mitre-matrix').update(tactic_refs=[]), 'empty Matrix rejected'),
        (lambda p: p['objects'].remove(next(o for o in p['objects'] if o['name']=='Secondary Matrix' and o['x_mitre_domains']==['lab-one'])), 'uncovered technique tactic cannot disappear when a Matrix is removed'),
        (lambda p: next(o for o in p['objects'] if o['type'] == 'relationship').update(target_ref=key(second,'LAB-ALPHA')), 'cross-domain parent references rejected'),
    ]:
        broken = deepcopy(payload); mutate(broken); bad(lambda: validate(broken), message)
    inferred = deepcopy(payload); inferred.pop('x_ttp_studio_domains')
    bad(lambda: validate(inferred), 'ambiguous inference requires an explicit domain definition')
    for obj in inferred['objects']:
        obj['external_references'] = [r for r in obj.get('external_references', []) if r['source_name'] != 'mitre-attack']
    inferred_catalog = validate(inferred)
    check(inferred_catalog.domain == 'lab-one' and domain_label('lab-one', inferred_catalog) == 'lab-one', 'unique chain/source can be inferred without extra metadata')
    shared = deepcopy(payload)
    shared_root = next(o for o in shared['objects'] if o['id'] == root)
    shared_root['x_mitre_domains'].append('lab-two')
    shared_root['external_references'].append({'source_name':'lab-two-references','external_id':'SHARED-OTHER'})
    shared_root['kill_chain_phases'].append({'kill_chain_name':'lab-two-chain','phase_name':'observe'})
    shared_catalog = validate(shared)
    check(external_id(shared_catalog.records[root])=='LAB-ALPHA'
          and external_id(shared_catalog.for_domain('lab-two').records[root])=='SHARED-OTHER',
          'a shared STIX object can have distinct configured IDs in two domains without global mutation')
    check(tactic_phases(shared_catalog.records[root],'lab-one')=={'survey'}
          and tactic_phases(shared_catalog.for_domain('lab-two').records[root],'lab-two')=={'observe'},
          'shared-object kill chain mappings remain scoped to each domain view')
    shared_child=next(o for o in shared['objects'] if o['id']==child)
    shared_child['x_mitre_domains'].append('lab-two')
    shared_child['external_references'].append({'source_name':'lab-two-references','external_id':'SHARED-CHILD'})
    shared_child['kill_chain_phases'].append({'kill_chain_name':'lab-two-chain','phase_name':'execute'})
    shared['objects'].append({'type':'relationship','id':'relationship--'+str(uuid.uuid4()),'name':'Scoped second parent',
        'relationship_type':'subtechnique-of','source_ref':child,'target_ref':key(second,'LAB-ALPHA'),'x_mitre_domains':['lab-two']})
    shared_catalog=validate(shared)
    check(shared_catalog.parents[child]==root and shared_catalog.for_domain('lab-two').parents[child]==key(second,'LAB-ALPHA'),
          'explicitly scoped parent edges allow a shared child to retain a different parent in each domain')
    prefixed = deepcopy(payload)
    prefixed['x_ttp_studio_domains'][0]['id']='mitre-research'
    for obj in prefixed['objects']:
        obj['x_mitre_domains']=['mitre-research' if d=='lab-one' else d for d in obj['x_mitre_domains']]
    prefixed_catalog=validate(prefixed)
    prefixed_layer=document_layer(TTPDocument('Prefixed',prefixed_catalog))
    check(validate_layer(prefixed_layer)['domain']=='mitre-research', 'custom mitre-prefixed domain is not rewritten as a legacy official alias')
    log('[Domain Audit 3/7] Selection, annotation, formulas and IO', 2, 7)
    doc = TTPDocument('Custom Domain', catalog)
    change_cells(doc, {(child, 'execute')}, 'add')
    update_annotation(doc, child, 'execute', 'Custom domain note', 4.5, '#2255aa')
    layer = document_layer(doc)
    check(layer['domain'] == 'lab-one' and layer['x_ttp_studio_domain']['name'] == 'Research lab-one', 'Navigator export preserves domain definition with canonical domain ID')
    check(validate_layer(layer) == layer, 'SDK structure probe preserves actual custom IDs/domain and finite decimal scores')
    check(imported_document(layer, catalog).selected == {child}, 'Navigator import restores custom ID selection')
    invalid = deepcopy(layer); invalid['x_ttp_studio_domain']['name'] = 'Forged name'
    bad(lambda: imported_document(invalid, catalog), 'layer definition cannot override its exact Bundle definition')
    bare = deepcopy(layer); bare.pop('customDataURL'); bare.pop('x_ttp_studio_dataset')
    bad(lambda: validate_layer(bare), 'custom domain cannot silently request an official catalog')
    invalid = deepcopy(layer); invalid['techniques'][0]['techniqueID'] = '<script>'
    bad(lambda: validate_layer(invalid), 'custom technique IDs are bounded safe tokens')
    native = document_payload(doc)
    check(native['selected_ttps'][0]['parent_technique_id'] == 'LAB-ALPHA' and native['selected_ttps'][0]['tactics'][0]['tactic_id'] == 'TACTIC-execute', 'native export preserves custom parent and tactic IDs')
    doc.set_catalog(second); doc.selected.add(key(second,'LAB-GAMMA')); doc.set_catalog(catalog)
    check(doc.selected == {child} and 'lab-two' in doc.domain_snapshots, 'domain switching restores independent selections and annotations')
    target = OUT / 'custom.studio.json'; save_studio(doc, target, log)
    restored = open_studio(CACHE, target, log)
    check(restored.navigator_layer == doc.navigator_layer and restored.domain_snapshots == doc.domain_snapshots, 'Studio reopening preserves custom domain archives and annotations')
    check(restored.catalog.domain_definitions == catalog.domain_definitions, 'custom definitions reconstruct exactly from cached Bundle')
    forged = document_payload(doc); forged['navigator_layer']=deepcopy(forged['navigator_layer'])
    forged['navigator_layer']['x_ttp_studio_domain']['reference_source']='forged'
    bad(lambda: StudioReader(CACHE,log).document(forged), 'Studio reopening rejects a forged domain definition')
    fresh = TTPDocument('Fresh custom edit',catalog)
    check(not batch_patch(fresh,{root},{'color':None},notify=log)['changed'] and not fresh.navigator_layer,
          'clearing absent custom technique color remains a no-op')
    batch_patch(fresh,{root},{'comment':'Batch custom note','enabled':False},notify=log)
    check(fresh.navigator_layer['x_ttp_studio_dataset']==catalog.dataset_id
          and fresh.navigator_layer['techniques'][0]['techniqueID']=='LAB-ALPHA',
          'fresh batch editing supplies custom dataset identity without renaming IDs')
    export_layers([doc, TTPDocument('Second', second)], OUT / 'layers.navigator.json', log)
    layers = read_layers(OUT / 'layers.navigator.json', log)
    result = LayerImportResolver(CACHE).preview(layers, [0,1], {0:'1.0',1:'1.0'}, {0:'enabled',1:'enabled'}, log)
    check(all(r['catalog'] for r in result.values()), 'multi-layer custom-domain batch resolves exact cache without loaded catalogs')
    drafts = build_import_documents(layers, [0,1], {0:'1.0',1:'1.0'}, {0:'enabled',1:'enabled'}, {i:r['catalog'] for i,r in result.items()}, log)
    check(drafts[0].selected == doc.selected and drafts[1].catalog.domain == 'lab-two', 'batch drafts retain independent custom domains')
    write_session(session_payload([doc],0,{'page':'selected'}),OUT/'session.json',log)
    check(read_session(CACHE,OUT/'session.json',log)['documents'][0].content_token() == doc.content_token(), 'session restores custom domain selection and archives')
    export_document_csv(doc, OUT/'custom.csv', log)
    with (OUT/'custom.csv').open(encoding='utf-8-sig',newline='') as stream: row=next(csv.DictReader(stream))
    check(row['attack_domain']=='lab-one' and row['technique_id']=='LAB-BETA.child' and row['parent_technique_id']=='LAB-ALPHA'
          and 'Custom domain note' in row['tactic_comments'], 'CSV preserves custom identity, parent and scoped annotations')
    calculated = calculate_layer([doc], 'a*2', 'Calculated', scope='matrix', notify=log)
    check(calculated.catalog is catalog and any(r.get('score')==9 for r in calculated.navigator_layer['techniques']), 'score formulas work on the custom domain matrix')
    bad(lambda: calculate_layer([doc,TTPDocument('Other',other)], 'a+b','Invalid',notify=log), 'formulas reject same-domain/version sources with a different dataset hash')
    compared, counts=compare_documents(doc,doc)
    check(compared['domain']=='lab-one' and counts['Both']==1 and compared['techniques'][0]['techniqueID']=='LAB-BETA.child',
          'selection comparison exports the actual custom domain and external IDs')
    preview=upgrade_preview(doc,other,log)
    decisions=[{'action':'Copy','reviewed':True,'target_id':row['source_id'],'target_scope':row['source_scope']} for row in preview['rows']]
    migrated=migrate_layer(doc,other,decisions,'Migrated custom domain',log,
                           reviews=[{'id':item['id'],'reviewed':True} for item in preview['items']])
    check(migrated.navigator_layer['x_ttp_studio_domain']['name']=='Independent Lab'
          and migrated.migration_archives[0]['layer']['x_ttp_studio_domain']['name']=='Research lab-one',
          'reviewed source migration binds the target definition and archives the original definition')
    saved_migration=OUT/'migration.studio.json'; save_studio(migrated,saved_migration,log)
    check(open_studio(CACHE,saved_migration,log).migration_archives==migrated.migration_archives,
          'migration archives reopen against their original custom-domain source')
    choices = source_choices(catalog,'Group',['name','id'])
    check(len(choices)==1 and external_id(catalog.objects_by_domain['lab-one'][choices[0]['key']])=='LAB-GROUP', 'source picker uses configured custom source IDs')
    check(resolve_sources(catalog,[choices[0]['key']])=={child}, 'custom source relationships resolve by STIX identity')
    candidate = inspect_source(CACHE,layer,'1.0',str(source),OUT/'layers.navigator.json',log)
    check(accept_source(CACHE,candidate,log)['catalog'].domain=='lab-one', 'NAV-016 acquisition supports custom domains and identifiers')
    log('[Domain Audit 4/7] Native source/domain/tree/matrix interfaces', 3, 7)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); configure_application(app)
    QtCore.QSettings(str(OUT/'settings.ini'),QtCore.QSettings.Format.IniFormat).clear()
    w=MainWindow(DATA,DATA/'latest.json',settings_path=OUT/'settings.ini'); w.resize(1700,1000); w.show()
    try:
        wait(lambda:w.loaded_ok and not w.loader.isRunning())
        official=w.catalog
        source_dialog=SourceDialog(CACHE,'1.0',w); source_dialog.show(); source_dialog.kind.setCurrentIndex(1); source_dialog.location.setText(str(source))
        source_dialog.load_button.click(); wait(lambda:source_dialog.result is not None and not source_dialog.worker.isRunning())
        check([source_dialog.domain.itemData(i) for i in range(source_dialog.domain.count())]==['lab-one','lab-two'], 'custom source preview offers the two available domain choices')
        check('Primary Matrix' in source_dialog.preview.toPlainText() and 'Secondary Matrix' in source_dialog.preview.toPlainText(), 'source preview discloses both matrices')
        source_dialog.imported.connect(w.install_imported_document); source_dialog.commit_button.click(); wait(lambda:w.loaded_ok and w.catalog.dataset_id==catalog.dataset_id)
        check(w.catalog.domain=='lab-one' and 'Research lab-one' in w.version_label.text(), 'custom source installs into the complete main UI with its own display name')
        w.show_document_context_menu(w.document_tabs.tabRect(w.active_document_index).center())
        domain_menu=next(a.menu() for a in w.document_context_menu.actions() if a.text()=='ATT&CK Domain')
        check({a.text() for a in domain_menu.actions() if a.isEnabled()}=={'Research lab-one','Research lab-two'},
              'file context menu offers the custom domains and disables unavailable official domains')
        w.document_context_menu.close()
        w.open_matrix(); wait(lambda:not w.matrix_view.building)
        check(set(w.items_by_id)==set(catalog.records), 'sidebar tree contains all custom matrix techniques')
        check(w.change_document_domain(w.active_document_index,'lab-two'), 'file context domain action supports another custom domain')
        wait(lambda:w.loaded_ok and w.catalog.domain=='lab-two')
        check(w.change_document_domain(w.active_document_index,'lab-one'), 'custom domain switching can return to the first domain')
        wait(lambda:w.loaded_ok and w.catalog.domain=='lab-one')
        w.install_imported_document(doc); wait(lambda:w.loaded_ok); w.open_matrix(); wait(lambda:not w.matrix_view.building)
        check(w.matrix_view.grab().save(str(OUT/'matrix.png')), 'custom multi-matrix UI screenshot')
        w.ttp_search.setText('LAB-BETA.child'); w.ttp_search_timer.stop(); w.apply_ttp_search()
        check(w.proxy.rowCount()>0, 'TTP search accepts custom external IDs')
        w.ttp_search.clear(); w.ttp_search_timer.stop(); w.apply_ttp_search()
        w.import_navigator_layer(OUT/'layers.navigator.json'); batch=w.integration_dialog; ready(batch)
        # Main import uses production data root; verified open catalogs still provide exact data.
        check(batch.import_button.isEnabled(), 'native multi-layer import accepts loaded custom domains')
        check('Research lab-one' in batch.layers_table.item(0,2).text(), 'batch preview uses dataset-scoped domain labels')
        check(batch.grab().save(str(OUT/'import.png')), 'custom-domain batch preview screenshot')
        batch.reject()
        from localization import language_manager
        manager=language_manager(); manager.set_language('zh_TW'); app.processEvents()
        check(w.catalog.domain=='lab-one' and external_id(w.catalog.records[child])=='LAB-BETA.child',
              'Traditional Chinese UI switching preserves custom domain and technique identity')
        check(w.matrix_view.grab().save(str(OUT/'matrix-zh.png')), 'Traditional Chinese custom-domain matrix screenshot')
        manager.set_language('en')
        w.open_manual()
        check(w.manual_page.load_page(ROOT/'manual'/'custom_domains_en.md')
              and 'x_ttp_studio_domains' in w.manual_page.browser.toPlainText(), 'English custom-domain guide renders in the actual Manual tab')
        manager.set_language('zh_TW'); app.processEvents()
        check(w.manual_page.load_page(ROOT/'manual'/'custom_domains+_zh.md')
              and '有序聯集' in w.manual_page.browser.toPlainText(), 'Traditional Chinese custom-domain guide renders in the actual Manual tab')
        manager.set_language('en'); w.close_manual()
        log('[Domain Audit 5/7] Matrix export',4,7)
        for kind in ('svg','xlsx'):
            export_matrix(doc,OUT/('matrix.'+kind),kind,notify=log)
            check((OUT/('matrix.'+kind)).stat().st_size>0,'custom domain '+kind+' export')
        log('[Domain Audit 6/7] Source isolation and pointer protection',5,7)
        check(all(p.read_bytes()==data for p,data in pointers.items()),'custom domains never modify official active/latest pointers')
        check(payload==frozen,'complete UI/IO leaves original Bundle dictionaries untouched')
        log('[Domain Audit 7/7] Writing report',6,7)
        write(OUT/'audit.json',{'passed':True,'count':len(CHECKS),'checks':CHECKS})
        log(f'[Domain Audit] PASS: {len(CHECKS)} checks',7,7)
    finally:
        with patch.object(w,'confirm_studio_changes',return_value='discard'): w.close()
        app.processEvents()


if __name__=='__main__': main()
