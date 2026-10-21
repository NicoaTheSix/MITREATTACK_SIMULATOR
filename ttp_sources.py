"""Exact-catalog source mappings and result unions. Operation flow: README.md."""
from collections import Counter, defaultdict

SOURCE_KINDS = {'Campaign': {'campaign'}, 'Software': {'malware', 'tool'}, 'Group': {'intrusion-set'},
                'Mitigation': {'course-of-action'}, 'Asset': {'x-mitre-asset'},
                'Detection Strategy': {'x-mitre-detection-strategy'},
                'Data Component': {'x-mitre-data-component'}, 'Data Source': {'x-mitre-data-source'}}
SOURCE_TYPES = set().union(*SOURCE_KINDS.values())
SOURCE_HEADINGS = {'course-of-action':'Techniques Addressed by Mitigation',
                   'malware':'Techniques Used by Software', 'tool':'Techniques Used by Software',
                   'campaign':'Techniques Used by Campaign', 'intrusion-set':'Techniques Used by Group',
                   'x-mitre-asset':'Techniques Targeting Asset',
                   'x-mitre-detection-strategy':'Techniques Detected by Strategy',
                   'x-mitre-data-component':'Techniques Related to Data Component',
                   'x-mitre-data-source':'Techniques Related to Data Source'}


def active(obj):
    return bool(obj) and not obj.get('revoked') and not obj.get('x_mitre_deprecated')


def build_source_rows(objects, records, notify, domain):
    """Only supplied-domain active records resolve; never infer edges from names."""
    from attack_catalog import external_id, domain_label
    rows = defaultdict(list)
    parents = {}
    label = domain_label(domain)
    notify(f'[3/4 Related TTPs] Input files: None; output files: None ({label} objects in memory)',0,0)
    notify(f'[3/4 Related TTPs] Indexing {label} direct source relationships',0,len(objects))
    for number,edge in enumerate(objects,1):
        if number % 4000 == 0: notify('[3/4 Related TTPs] Reading relationships',number,len(objects))
        if edge.get('type') != 'relationship' or not active(edge): continue
        source, target = records.get(edge.get('source_ref')), records.get(edge.get('target_ref'))
        if not active(source) or not active(target): continue
        kind = edge.get('relationship_type')
        if kind == 'subtechnique-of':
            if source.get('type') == target.get('type') == 'attack-pattern': parents[source['id']] = target['id']
            continue
        origin, technique = source, target
        expected = ('mitigates' if source.get('type') == 'course-of-action' else
                    'detects' if source.get('type') in ('x-mitre-detection-strategy','x-mitre-data-component') else 'uses')
        if kind == 'targets' and source.get('type') == 'attack-pattern' and target.get('type') == 'x-mitre-asset':
            origin, technique, expected = target, source, 'targets'
        if origin.get('type') not in SOURCE_TYPES or technique.get('type') != 'attack-pattern' or kind != expected:
            continue
        # Assets/data sources never use the generic "uses" direction.
        if origin.get('type') == 'x-mitre-asset' and kind != 'targets': continue
        if origin.get('type') == 'x-mitre-data-source': continue
        entry = {'relationship_id':edge['id'], 'target_ref':technique['id'],
                 'description':edge.get('description',''), 'references':edge.get('external_references',[])}
        if kind in ('detects','targets'): entry.update(mapping_type=kind,via_refs=[edge['id']])
        rows[origin['id']].append(entry)
    notify(f'[3/4 Related TTPs] Resolving {label} strategy/analytic/component paths',0,0)
    for strategy in records.values():
        if strategy.get('type') != 'x-mitre-detection-strategy' or not active(strategy): continue
        for analytic_ref in dict.fromkeys(strategy.get('x_mitre_analytic_refs',[])):
            analytic = records.get(analytic_ref,{})
            if analytic.get('type') != 'x-mitre-analytic' or not active(analytic): continue
            components = set()
            for field in ('x_mitre_log_source_references','x_mitre_log_sources'):
                entries = analytic.get(field,[])
                if not isinstance(entries,list): continue
                components.update(entry['x_mitre_data_component_ref'] for entry in entries if isinstance(entry,dict)
                                  and isinstance(entry.get('x_mitre_data_component_ref'),str))
            for component_ref in sorted(components):
                component = records.get(component_ref,{})
                if component.get('type') != 'x-mitre-data-component' or not active(component): continue
                for entry in rows.get(strategy['id'],[]):
                    route = f"Via strategy {external_id(strategy) or strategy['id']} ({strategy['name']}) / analytic {analytic.get('name',analytic_ref)}"
                    rows[component_ref].append({**entry, 'mapping_type':'strategy-analytic-component',
                        'via_refs':[*entry['via_refs'],strategy['id'],analytic_ref,component_ref],
                        'description':route+('\n'+entry['description'] if entry['description'] else '')})
    # Data Source is the union of components with an exact source reference.
    for component in records.values():
        if component.get('type') != 'x-mitre-data-component' or not active(component): continue
        source_ref = component.get('x_mitre_data_source_ref')
        source = records.get(source_ref,{})
        if source.get('type') != 'x-mitre-data-source' or not active(source): continue
        for entry in rows.get(component['id'],[]):
            rows[source_ref].append({**entry,'mapping_type':'data-source-component',
                'via_refs':[*entry['via_refs'],component['id'],source_ref],
                'description':f"Via data component {component['name']}\n"+entry['description']})
    for entries in rows.values():
        entries.sort(key=lambda entry:(external_id(records[entry['target_ref']]),entry['relationship_id'],entry.get('via_refs',[])))
    notify(f'[3/4 Related TTPs] Complete: {label} {sum(map(len,rows.values()))} direct/derived mappings',1,1)
    return dict(rows), parents


def source_choices(catalog, kind, fields):
    """Unambiguous display labels plus a separate literal search projection."""
    from attack_catalog import external_id
    from ttp_search import source_search_text
    store = catalog.objects_by_domain[catalog.domain]
    result = []
    for obj in store.values():
        if obj.get('type') not in SOURCE_KINDS[kind] or not active(obj): continue
        label = f"{external_id(obj)}  {obj.get('name',obj['id'])}".strip()
        text = source_search_text(obj,fields=fields)
        if obj['type'] == 'x-mitre-data-component':
            parent = store.get(obj.get('x_mitre_data_source_ref'),{})
            if parent.get('type') == 'x-mitre-data-source' and active(parent):
                label = f"{external_id(parent)} {parent['name']} : {label}".strip()
                text += '\n'+source_search_text(parent,fields=fields)
        result.append({'key':obj['id'],'label':label,'search':text,'description':obj.get('description','')})
    counts = Counter(row['label'] for row in result)
    for row in result:
        if counts[row['label']] > 1: row['label'] += ' ['+row['key']+']'
    return sorted(result,key=lambda row:(row['label'].casefold(),row['key']))


def resolve_sources(catalog, keys):
    """Reject stale/unsupported IDs atomically, then deduplicate mapped techniques."""
    store = catalog.objects_by_domain[catalog.domain]
    keys = set(keys)
    if any(not active(store.get(key)) or store[key].get('type') not in SOURCE_TYPES for key in keys):
        raise ValueError('Source results no longer belong to the active catalog or include unsupported entries.')
    return {entry['target_ref'] for key in keys for entry in catalog.techniques_by_source[catalog.domain].get(key,[])
            if entry['target_ref'] in catalog.records}


def source_cells(catalog, keys):
    from attack_catalog import tactic_phases
    return {(key,slug) for key in resolve_sources(catalog,keys)
            for slug in tactic_phases(catalog.records[key],catalog.domain) & catalog.tactics.keys()}
