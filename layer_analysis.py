"""Bounded formulas and explicit property inheritance. Workflow: README.md."""
from copy import copy, deepcopy
import string

from attack_catalog import external_id, tactic_phases, supports_navigator
from navigator_integration import document_layer, validate_layer, SELECTION_MARKER
from navigator_visuals import LayerAppearance
from score_expression import ScoreExpression
from ttp_documents import TTPDocument, validate_document_name
from ttp_selection import is_selected, assign_cells

INHERITANCE_FIELDS = ('gradient', 'color', 'comment', 'links', 'metadata', 'enabled', 'filters', 'legendItems')
NAVIGATOR_FORMULA_GRADIENT = {'colors': ['#ff6666ff', '#ffe766ff', '#8ec843ff'], 'minValue': 0, 'maxValue': 100}


def automatic_formula_gradient(scores, source_gradient, mode):
    """Choose serialized gradient settings; explicit inheritance is handled by the caller."""
    if mode == 'studio':
        gradient = deepcopy(source_gradient)
        gradient.update(minValue=min(0, min(scores)) if scores else 0, maxValue=max(1, max(scores)) if scores else 1)
        return gradient
    if mode != 'navigator':
        raise ValueError('Choose Studio or Navigator automatic gradient mode.')
    gradient = deepcopy(NAVIGATOR_FORMULA_GRADIENT)
    if scores and min(scores) != max(scores):
        low, high = min(scores), max(scores)
        gradient.update(minValue=low, maxValue=high)
        if low == 0 and high == 1:
            gradient['colors'] = ['#ffffff00', '#66b1ffff']
    return gradient


def navigator_formula_rows(layer, catalog):
    """Project serialized rows as Navigator does: expand globals, then replace in file order."""
    phases = {external_id(obj): set(tactic_phases(obj, catalog.domain)) & set(catalog.tactics)
              for obj in catalog.records.values()}
    rows = {}
    for row in layer.get('techniques', []):
        attack_id = row['techniqueID']
        scopes = phases.get(attack_id, set())
        for slug in ([row['tactic']] if 'tactic' in row else scopes):
            if slug in scopes:
                rows[attack_id, slug] = row
    return rows


def snapshot_document(document):
    snapshot = copy(document)
    snapshot.selected = set(document.selected)
    snapshot.navigator_layer = deepcopy(document.navigator_layer)
    snapshot.navigator_import_selected = set(document.navigator_import_selected)
    snapshot.navigator_snapshots = deepcopy(document.navigator_snapshots)
    snapshot.domain_snapshots = deepcopy(document.domain_snapshots)
    snapshot.migration_archives = deepcopy(document.migration_archives)
    snapshot.selection_scopes = deepcopy(document.selection_scopes)
    snapshot.selection_preferences = dict(document.selection_preferences)
    snapshot.search_fields = list(document.search_fields)
    snapshot.atlas_document = snapshot_document(document.atlas_document) if document.atlas_document else None
    snapshot.car_workspace = deepcopy(document.car_workspace)
    return snapshot


def calculate_layer(documents, expression, name, missing='unscored', notify=lambda *args: None,
                    scope='selected', inheritance=None, syntax=None, mode='studio', gradient_mode='auto'):
    """Build an independent draft; selected scope is the backwards-compatible default."""
    notify('Input files: None; output files: None (source layers in memory)', 0, 0)
    notify('[Formula 1/5] Validating formula, scope and inheritance sources', 0, 5)
    if not 1 <= len(documents) <= 26 or missing not in ('unscored', 'zero'):
        raise ValueError('Choose 1–26 layers and a supported missing-score policy.')
    if scope not in ('selected', 'matrix'):
        raise ValueError('Choose selected-source union or entire matrix.')
    if mode not in ('studio', 'navigator'):
        raise ValueError('Choose Studio or Navigator missing-score/scope mode.')
    if gradient_mode not in ('auto', 'studio', 'navigator'):
        raise ValueError('Choose automatic, Studio or Navigator formula gradient mode.')
    gradient_mode = mode if gradient_mode == 'auto' else gradient_mode
    if syntax is None:
        syntax = 'navigator' if mode == 'navigator' else 'studio'
    if mode == 'navigator' and syntax != 'navigator':
        raise ValueError('Navigator missing-score/scope mode requires Navigator scalar syntax.')
    name = validate_document_name(name)
    catalog = documents[0].catalog
    if not supports_navigator(catalog) or any(doc.catalog.domain != catalog.domain or doc.catalog.version != catalog.version
                                      or doc.catalog.dataset_id != catalog.dataset_id for doc in documents):
        raise ValueError('Formula sources require the same domain/version/dataset and ATT&CK v4 or later.')
    aliases = dict(zip(string.ascii_lowercase, documents))
    formula = ScoreExpression(expression, aliases, syntax)
    constant = None
    if mode == 'navigator':
        # The official service probes the expression without source scores first.
        # In that probe e means Euler's constant even when source layer e exists.
        try:
            constant = ScoreExpression(expression, set(aliases) - {'e'}, syntax).evaluate({})
        except ValueError:
            if not formula.variables:
                raise
    inheritance = {} if inheritance is None else deepcopy(inheritance)
    if not isinstance(inheritance, dict) or set(inheritance) - set(INHERITANCE_FIELDS):
        raise ValueError('Unknown inheritance property.')
    if any(not isinstance(alias, str) or alias not in aliases for alias in inheritance.values()):
        raise ValueError('Inheritance sources must name one of the listed layer variables.')
    used = formula.variables or set(aliases)
    if any(not doc.selected <= catalog.records.keys() for doc in documents):
        raise ValueError('Source selection contains unavailable TTPs.')
    keys = set(catalog.records) if mode == 'navigator' or scope == 'matrix' else set().union(*(aliases[alias].selected for alias in used))
    if not keys:
        raise ValueError('Select TTPs in a referenced source or choose Entire matrix.')
    notify('[Formula 2/5] Reading immutable source annotations', 1, 5)
    needed = used | set(inheritance.values())
    sources = {alias: LayerAppearance(document_layer(aliases[alias])) for alias in sorted(needed)}
    normalized = {alias: navigator_formula_rows(source.layer, catalog) for alias, source in sources.items()} if mode == 'navigator' else {}
    rows, scores, scored_cells = [], [], set()
    for number, key in enumerate(sorted(keys, key=lambda key: external_id(catalog.records[key])), 1):
        attack_id = external_id(catalog.records[key])
        phases = tactic_phases(catalog.records[key], catalog.domain)
        for slug in catalog.tactic_order:
            if slug not in phases:
                continue
            if mode == 'studio' and scope == 'selected' and not any(is_selected(aliases[alias].selected, aliases[alias].selection_scopes, key, slug)
                                               for alias in used):
                continue
            values = {}
            for alias in formula.variables:
                if mode == 'navigator':
                    value = normalized[alias].get((attack_id, slug), {}).get('score')
                else:
                    cell = sources[alias].cell(attack_id, slug)
                    value = cell['score'] if cell['enabled'] else None
                values[alias] = 0 if value is None and mode == 'studio' and missing == 'zero' else value
            score = constant
            # Preserve the explicit missing-score policy even in conditional expressions.
            if mode == 'navigator':
                evaluate = constant is None and any(value is not None for value in values.values())
                values = {alias: 0 if value is None else value for alias, value in values.items()}
            else:
                evaluate = all(value is not None for value in values.values())
            if evaluate:
                try:
                    score = formula.evaluate(values)
                except ValueError as error:
                    raise ValueError(f'{attack_id} / {slug}: {error}') from error
            row = {'techniqueID': attack_id, 'tactic': slug, 'enabled': mode == 'navigator' or score is not None}
            if score is not None:
                row['score'] = score
                scored_cells.add((key, slug))
                scores.append(score)
            for field in ('color', 'comment', 'links', 'metadata', 'enabled'):
                if field not in inheritance:
                    continue
                source = sources[inheritance[field]]
                original = (normalized[inheritance[field]].get((attack_id, slug), {}) if mode == 'navigator' else
                            source.rows.get((attack_id, slug), source.rows.get((attack_id, ''), {})))
                if field == 'enabled':
                    row['enabled'] = original.get('enabled', True)
                elif field in original:
                    row[field] = deepcopy(original[field])
                    if field == 'metadata':
                        row[field] = [entry for entry in row[field] if entry.get('name') != SELECTION_MARKER]
            if mode == 'studio' or score is not None or not row['enabled'] or any(row.get(field) for field in ('color', 'comment', 'links', 'metadata')):
                rows.append(row)
        if number % 50 == 0 or number == len(keys):
            notify('[Formula 3/5] Calculating technique/tactic cells and inheriting annotations', number, len(keys))
    if not rows and mode == 'studio':
        raise ValueError('The calculation scope contains no mapped technique/tactic cells.')
    notify('[Formula 4/5] Validating the complete independent result', 3, 5)
    gradient = deepcopy(sources[inheritance.get('gradient', sorted(used)[0])].gradient)
    if 'gradient' not in inheritance:
        gradient = automatic_formula_gradient(scores, gradient, gradient_mode)
    effective_scope = 'navigator' if mode == 'navigator' else scope
    effective_missing = 'zero-if-any-score' if mode == 'navigator' else missing
    provenance = [{'name': 'Score expression', 'value': expression.strip()}, {'name': 'Calculation mode', 'value': mode},
                  {'name': 'Missing scores', 'value': effective_missing}, {'name': 'Calculation scope', 'value': effective_scope}] + [
                  {'name': 'Source ' + alias, 'value': f'{aliases[alias].name} ({aliases[alias].document_id})'} for alias in sorted(needed)]
    layer = {'name': name, 'domain': catalog.domain, 'versions': {'attack': catalog.version, 'layer': '4.5', 'navigator': '5.2.0'},
             'description': 'Score expression: ' + expression.strip(), 'techniques': rows, 'gradient': gradient,
             'selectSubtechniquesWithParent': False, 'metadata': provenance,
             'x_ttp_studio_formula': {'expression': expression.strip(), 'missing': effective_missing, 'scope': effective_scope,
                 'inheritance': inheritance, 'sources': {alias: {'name': aliases[alias].name, 'document_id': aliases[alias].document_id}
                                                        for alias in sorted(needed)}}}
    layer['x_ttp_studio_formula']['syntax'] = syntax
    layer['x_ttp_studio_formula']['mode'] = mode
    layer['x_ttp_studio_formula']['gradient_mode'] = gradient_mode
    if mode == 'navigator':
        layer['x_ttp_studio_formula']['evaluation'] = 'constant' if constant is not None else 'scored-union'
    for field in ('links', 'metadata', 'filters', 'legendItems'):
        if field in inheritance:
            source_layer = sources[inheritance[field]].layer
            if field in source_layer:
                layer[field] = deepcopy(source_layer[field])
            elif field == 'metadata':
                layer.pop(field, None)
            if field == 'filters' and 'hideDisabled' in source_layer:
                layer['hideDisabled'] = source_layer['hideDisabled']
    result = TTPDocument(name, catalog, navigator_layer=validate_layer(layer, catalog))
    assign_cells(result, scored_cells)
    result.navigator_import_selected = {external_id(catalog.records[key]) for key in result.selected}
    notify(f'[Formula 5/5] Ready: {len(scores)} scored cells; {len(result.selected)} selected TTPs', 5, 5)
    return result
