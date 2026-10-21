"""Version-aware upgrade content and annotation edits. Workflow: README.md."""
from copy import deepcopy
import html
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from attack_catalog import DOMAIN_LABELS, external_id, tactic_phases
from navigator_integration import SELECTION_MARKER
from navigator_fields import validate_fields, web_url

EDIT_FIELDS = frozenset(('comment', 'score', 'color', 'enabled', 'links', 'metadata'))


def technique_record(catalog, identity):
    """Include inactive raw records for readable removed/revoked comparisons."""
    return next((obj for obj in catalog.records.values() if external_id(obj) == identity), None) or next(
        (obj for obj in catalog.all_objects_by_domain.get(catalog.domain, {}).values()
         if obj.get('type') == 'attack-pattern' and external_id(obj) == identity), {})


def mapped_annotation(source, decision):
    row = deepcopy(source['annotation'])
    row['techniqueID'] = decision.get('target_id')
    row.pop('tactic', None)
    if decision.get('target_scope'):
        row['tactic'] = decision['target_scope']
    if 'metadata' in row:
        row['metadata'] = [entry for entry in row['metadata'] if entry.get('name') != SELECTION_MARKER]
        if not row['metadata']:
            row.pop('metadata')
    patch = decision.get('annotation_patch', {})
    if not isinstance(patch, dict) or patch.keys() - EDIT_FIELDS:
        raise ValueError('Target annotation edits accept only comment, score, color, enabled, links and metadata.')
    validate_fields({field: patch[field] for field in ('links', 'metadata') if patch.get(field) is not None})
    for link in patch.get('links') or []:
        if link.get('divider') is not True:
            web_url(link['url'])
    for field, value in patch.items():
        if value is None:
            row.pop(field, None)
        else:
            row[field] = deepcopy(value)
    return row


def annotation_patch(row):
    return {field: deepcopy(row.get(field)) for field in EDIT_FIELDS}


def version_page(catalog, identity):
    if catalog.dataset_id or catalog.custom_source or catalog.domain not in DOMAIN_LABELS:
        return ''
    if not technique_record(catalog, identity) or not re.fullmatch(r'T\d{4}(?:\.\d{3})?', identity):
        return ''
    if not re.fullmatch(r'\d+(?:\.\d+)?', catalog.version):
        return ''
    return 'https://attack.mitre.org/versions/v' + catalog.version.split('.')[0] + '/techniques/' + identity.replace('.', '/') + '/'


def checked_version_page(url, notify):
    """Check only the requested archive; never follow a redirect to latest or another ID."""
    expected = urlsplit(url)
    if (expected.scheme != 'https' or expected.netloc != 'attack.mitre.org' or expected.query or expected.fragment or
            not re.fullmatch(r'/versions/v\d+/techniques/T\d{4}(?:/\d{3})?/', expected.path)):
        raise ValueError('Expected an official version-specific technique URL.')
    notify('Input URL: ' + url + '; output files: None (version-page check in memory)', 0, 0)
    notify('[Upgrade page 1/2] Checking the requested website archive', 0, 2)
    def matches(candidate):
        parsed = urlsplit(candidate)
        return (parsed.scheme == 'https' and parsed.netloc == expected.netloc and not parsed.query and not parsed.fragment
                and parsed.path.removesuffix('index.html').rstrip('/') == expected.path.rstrip('/'))
    class ArchiveRedirect(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, newurl):
            if not matches(newurl):
                raise ValueError('The version page redirected away from the requested archive. No latest-page fallback was opened.')
            return super().redirect_request(request, fp, code, message, headers, newurl)
    with build_opener(ArchiveRedirect()).open(Request(url, headers={'User-Agent': 'Fusion-Studio'}), timeout=15) as response:
        if response.status != 200 or not matches(response.geturl()):
            raise ValueError('The requested version page is unavailable. The cached record remains available here.')
    notify('[Upgrade page 2/2] Version archive verified', 2, 2)
    return url


def content_html(catalog, identity, annotations, *, selection=()):
    """Escape all catalog/user content; the viewer never loads embedded remote resources."""
    from localization import tr
    esc = lambda value: html.escape(str(value))
    heading = lambda text: '<h3>' + esc(tr(text)) + '</h3>'
    record = technique_record(catalog, identity)
    pieces = ['<h2>' + esc(identity or tr('No target technique')) + ' ' + esc(record.get('name', '')) + '</h2>',
              '<p>' + esc(tr('Dataset version')) + ': ' + esc(catalog.version) + ' · ' + esc(catalog.domain) + '</p>']
    if catalog.dataset_id:
        pieces.append('<p>SHA-256: ' + esc(catalog.dataset_id) + '</p>')
    if not record:
        pieces.append('<p>' + esc(tr('No technique record in this snapshot.')) + '</p>')
    else:
        state = 'Revoked' if record.get('revoked') else 'Deprecated' if record.get('x_mitre_deprecated') else 'Active'
        pieces.extend(['<p>' + esc(tr(state)) + ' · STIX: ' + esc(record.get('id', '')) + '</p>',
                       heading('Description'), '<p style="white-space:pre-wrap">' + esc(record.get('description', '')) + '</p>',
                       heading('Tactics'), '<p>' + esc(', '.join(catalog.tactics.get(slug, {}).get('name', slug) + ' [' + slug + ']'
                            for slug in sorted(tactic_phases(record, catalog.domain)))) + '</p>',
                       heading('Platforms'), '<p>' + esc(', '.join(record.get('x_mitre_platforms', []))) + '</p>'])
    pieces.extend([heading('Annotations'), '<p>' + esc(tr('Selected tactics')) + ': ' + esc(', '.join(sorted(selection))) + '</p>'])
    for row in annotations:
        pieces.extend(['<h4>' + esc(row.get('tactic') or tr('All tactics')) + '</h4>',
                       '<p style="white-space:pre-wrap">' + esc(row.get('comment', '')) + '</p>',
                       '<p>' + esc(json.dumps(row, ensure_ascii=False, indent=2)).replace('\n', '<br>') + '</p>'])
    if not annotations:
        pieces.append('<p>' + esc(tr('No annotations.')) + '</p>')
    pieces.extend([heading('Complete STIX record'), '<p>' + esc(json.dumps(record, ensure_ascii=False, indent=2)).replace('\n', '<br>') + '</p>'])
    return ''.join(pieces)
