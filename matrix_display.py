"""Shared labels, annotation indicators and source Notes. Workflow: README.md."""
from attack_catalog import external_id

SELECTION_MARKER='TTP Selection Studio selected'


def labels(layer):
    layout=layer.get('layout',{})
    return layout.get('showID',False),layout.get('showName',True)


def display_label(identity,name,layer,mini=False):
    if mini: return ''
    show_id,show_name=labels(layer)
    return '  '.join(part for part,show in ((identity,show_id),(name,show_name)) if show and part)


def annotation_flags(row,notes=()):
    metadata=any(entry.get('name')!=SELECTION_MARKER and 'name' in entry for entry in row.get('metadata',[]))
    links=any('label' in entry for entry in row.get('links',[]))
    yellow=bool(row.get('comment') or metadata or notes)
    annotated=yellow or links or row.get('score') is not None or bool(row.get('color')) or row.get('enabled') is False
    return {'noteIndicator':yellow,'linkIndicator':links,'annotated':annotated,
            'commentPresent':bool(row.get('comment') or notes), 'metadataPresent':metadata, 'linkPresent':links}


def marker_colors(style):
    if 'markerColors' in style: return list(style['markerColors'])
    return ([ '#ffcc00' ] if style.get('noteIndicator') else []) + ([ '#4daafc' ] if style.get('linkIndicator') else [])


def source_notes(catalog):
    if catalog is None: return {}
    result={}
    for obj in catalog.all_objects_by_domain.get(catalog.domain,{}).values():
        if (obj.get('type')!='note' or obj.get('revoked') or obj.get('x_mitre_deprecated') or
                not isinstance(obj.get('content'),str) or not obj['content'].strip()):
            continue
        refs=obj.get('object_refs',[])
        if not isinstance(refs,list): continue
        for ref in refs:
            if isinstance(ref,str) and ref in catalog.records:
                title=obj.get('abstract','') if isinstance(obj.get('abstract',''),str) else ''
                result.setdefault(external_id(catalog.records[ref]),[]).append((title,obj['content']))
    return {key:sorted(set(values)) for key,values in result.items()}


def header_color(layer,mini=False):
    return layer.get('tacticRowBackground','#dddddd') if not mini and layer.get('showTacticRowBackground',False) else ''
