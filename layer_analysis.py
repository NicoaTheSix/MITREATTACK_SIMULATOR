"""Bounded arithmetic over independent layer snapshots. Workflow: README.md."""
import ast
from copy import copy, deepcopy
import math
import operator
import string

from attack_catalog import external_id, tactic_phases, supports_navigator
from navigator_integration import document_layer, validate_layer
from navigator_visuals import LayerAppearance
from ttp_documents import TTPDocument, validate_document_name

OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def snapshot_document(document):
    snapshot = copy(document)
    snapshot.selected = set(document.selected)
    snapshot.navigator_layer = deepcopy(document.navigator_layer)
    snapshot.navigator_import_selected = set(document.navigator_import_selected)
    snapshot.navigator_snapshots = deepcopy(document.navigator_snapshots)
    snapshot.domain_snapshots = deepcopy(document.domain_snapshots)
    snapshot.migration_archives = deepcopy(document.migration_archives)
    return snapshot


class ScoreExpression:
    """Parse a small arithmetic grammar; never execute Python expressions."""
    def __init__(self, expression, aliases):
        if not isinstance(expression, str) or not expression.strip() or len(expression) > 512:
            raise ValueError('Enter an arithmetic formula of 1–512 characters.')
        try:
            self.tree = ast.parse(expression.strip(), mode='eval')
        except (SyntaxError, RecursionError) as error:
            raise ValueError('Invalid arithmetic formula.') from error
        nodes = list(ast.walk(self.tree))
        if len(nodes) > 128:
            raise ValueError('Formula is too complex (maximum 128 syntax nodes).')
        self.variables = set()
        for node in nodes:
            if type(node) not in (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load,
                                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.UAdd, ast.USub):
                raise ValueError('Use numbers, layer variables, +, -, *, / and parentheses only.')
            if isinstance(node, ast.Name):
                if node.id not in aliases:
                    raise ValueError('Unknown layer variable: ' + node.id)
                self.variables.add(node.id)
            if isinstance(node, ast.Constant):
                if type(node.value) not in (int, float):
                    raise ValueError('Formula constants must be finite numbers.')
                self.number(node.value)
        self.depth(self.tree)

    @staticmethod
    def number(value):
        if type(value) not in (int, float) or abs(value) > 1e300 or not math.isfinite(value):
            raise ValueError('Formula values must be finite and within ±1e300.')
        return value

    def depth(self, node, level=0):
        if level > 24:
            raise ValueError('Formula nesting exceeds 24 levels.')
        for child in ast.iter_child_nodes(node):
            self.depth(child, level + 1)

    def evaluate(self, scores):
        def visit(node):
            if isinstance(node, ast.Expression):
                return visit(node.body)
            if isinstance(node, ast.Name):
                return self.number(scores[node.id])
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.UnaryOp):
                return self.number((-1 if isinstance(node.op, ast.USub) else 1) * visit(node.operand))
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError('Division by zero.')
            return self.number(OPERATORS[type(node.op)](left, right))
        return visit(self.tree)


def calculate_layer(documents, expression, name, missing='unscored', notify=lambda *args: None):
    notify('Input files: None; output files: None (source layers in memory)', 0, 0)
    notify('[Formula 1/4] Validating sources and arithmetic', 0, 4)
    if not 1 <= len(documents) <= 26 or missing not in ('unscored', 'zero'):
        raise ValueError('Choose 1–26 layers and a supported missing-score policy.')
    name = validate_document_name(name)
    catalog = documents[0].catalog
    if not supports_navigator(catalog) or any(doc.catalog.domain != catalog.domain or doc.catalog.version != catalog.version
                                      or doc.catalog.dataset_id != catalog.dataset_id for doc in documents):
        raise ValueError('Formula sources require the same domain/version and ATT&CK v4 or later.')
    aliases = dict(zip(string.ascii_lowercase, documents))
    formula = ScoreExpression(expression, aliases)
    used = formula.variables or set(aliases)
    keys = set().union(*(aliases[alias].selected for alias in used))
    if not keys or not keys <= catalog.records.keys():
        raise ValueError('Select valid TTPs in at least one referenced source layer.')
    notify('[Formula 2/4] Reading immutable source scores', 1, 4)
    sources = {alias: LayerAppearance(document_layer(aliases[alias])) for alias in used}
    rows, selected, scores = [], set(), []
    for number, key in enumerate(sorted(keys, key=lambda key: external_id(catalog.records[key])), 1):
        attack_id = external_id(catalog.records[key])
        phases = tactic_phases(catalog.records[key], catalog.domain)
        for slug in catalog.tactic_order:
            if slug not in phases:
                continue
            values = {}
            for alias in formula.variables:
                cell = sources[alias].cell(attack_id, slug)
                value = cell['score'] if cell['enabled'] else None
                values[alias] = 0 if value is None and missing == 'zero' else value
            score = None
            if all(value is not None for value in values.values()):
                try:
                    score = formula.evaluate(values)
                except ValueError as error:
                    raise ValueError(f'{attack_id} / {slug}: {error}') from error
            row = {'techniqueID': attack_id, 'tactic': slug, 'enabled': score is not None}
            if score is not None:
                row['score'] = score
                selected.add(key)
                scores.append(score)
            rows.append(row)
        if number % 50 == 0 or number == len(keys):
            notify('[Formula 3/4] Calculating technique/tactic cells', number, len(keys))
    gradient = deepcopy(sources[next(iter(sorted(used)))].gradient)
    gradient.update(minValue=min(0, min(scores)) if scores else 0, maxValue=max(1, max(scores)) if scores else 1)
    layer = {'name': name, 'domain': catalog.domain, 'versions': {'attack': catalog.version, 'layer': '4.5', 'navigator': '5.2.0'},
             'description': 'Score expression: ' + expression.strip(), 'techniques': rows, 'gradient': gradient,
             'selectSubtechniquesWithParent': False,
             'metadata': [{'name': 'Score expression', 'value': expression.strip()}, {'name': 'Missing scores', 'value': missing}] +
                         [{'name': 'Source ' + alias, 'value': f'{doc.name} ({doc.document_id})'} for alias, doc in aliases.items() if alias in used]}
    result = TTPDocument(name, catalog, selected=selected, navigator_layer=validate_layer(layer),
                         navigator_import_selected={external_id(catalog.records[key]) for key in selected})
    notify(f'[Formula 4/4] Ready: {len(scores)} scored cells; {len(selected)} selected TTPs', 4, 4)
    return result
