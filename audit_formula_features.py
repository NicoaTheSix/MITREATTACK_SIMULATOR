"""Verify advanced expressions, full matrix scope and inheritance. Flow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import json
import time

from PySide6 import QtWidgets
from attack_catalog import external_id, load_catalog, tactic_phases
from layer_analysis import ScoreExpression, calculate_layer, snapshot_document
from layer_analysis_dialogs import FormulaDialog
from main import configure_application
from navigator_integration import document_layer, imported_document, write_json_atomic, SELECTION_MARKER
from navigator_visuals import LayerAppearance
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument
from ttp_selection import assign_cells, selected_cells

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts' / 'formula-features'
CHECKS = []


def log(message, current=0, total=0):
    print(message + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, label):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def bad(task, label):
    try:
        task()
    except ValueError:
        check(True, label)
    else:
        raise AssertionError(label)


def wait(condition):
    end = time.monotonic() + 60
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError('Native formula task did not finish')
        QtWidgets.QApplication.processEvents()
        time.sleep(.01)
    QtWidgets.QApplication.processEvents()


class Harness(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.messages, self.installed = [], []
        self.matrix_view = SimpleNamespace(show_all_layers=QtWidgets.QCheckBox())
        self.loaded_ok, self.opened = True, False

    def operation_report(self, *message):
        self.messages.append(message)

    def install_imported_document(self, document):
        self.installed.append(document)

    def open_matrix(self):
        self.opened = True


def main():
    log(f'Input file: {(DATA / "latest.json").resolve()}')
    log(f'Input directory: {DATA.resolve()}')
    for name in ('audit.json', 'result.studio.json', 'result.navigator.json', 'session.json', 'formula.png', 'inheritance.png'):
        log(f'Output file: {(OUT / name).resolve()}')
    OUT.mkdir(parents=True, exist_ok=True)
    pointers = {p: p.read_bytes() for p in (DATA / 'latest.json', DATA / 'active.json') if p.exists()}
    log('[Formula Audit 1/7] Operator precedence, functions and bounded parsing', 0, 7)
    values = {'a': 80, 'b': 60, 'c': 0}
    examples = [('a+b', 140), ('(a+b)/2', 70), ('-a+2*b', 40), ('a>b', 1), ('a<b', 0),
        ('a>=80', 1), ('a<=b', 0), ('a==80', 1), ('a!=80', 0), ('(a>b) and (a>=75)', 1),
        ('a<b or b>0', 1), ('(a>b) xor (b>0)', 0), ('not a>b', 0), ('not c', 1),
        ('a>b ? 25 : 10', 25), ('a<b ? 10 : b>0 ? 20 : 30', 20), ('(a>b ? a : b)/2', 40),
        ('0 ? 1/0 : 9', 9), ('1 or (1/0)', 1), ('0 and (1/0)', 0), ('2 and -3', 1),
        ('2^3^2', 512), ('-2^2', -4), ('2^-2', .25), ('11%4', 3),
        ('abs(-2.5)', 2.5), ('min(a,b,100)', 60), ('max(a,b)', 80), ('min(7)', 7),
        ('round(2.345,2)', 2.35), ('round(2.5)', 2), ('floor(-1.2)', -2), ('ceil(-1.2)', -1),
        ('sqrt(81)', 9), ('pow(2,4)', 16), ('log(8,2)', 3), ('exp(0)', 1),
        ('max(a>b ? 25 : 10, 20)', 25), ('.25*a + 1e1', 30)]
    for expression, expected in examples:
        check(ScoreExpression(expression, values).evaluate(values) == expected, expression + ': expected numeric result')
    for expression in ('__import__("os")', 'a.__class__', 'a[0]', '[a]', '{a}', 'a=4', 'True', 'unknown+1',
        'sinus(a)', 'min()', 'abs(1,2)', 'max(1,)', 'a+', 'a ? b', 'a ? : b', '(a', 'a)', 'a**2', 'a//2',
        'a < b < c', '1e309', '9' * 320, '+'.join(['a'] * 100), '(' * 25 + 'a' + ')' * 25, 'a; b'):
        bad(lambda expression=expression: ScoreExpression(expression, values), 'reject syntax: ' + expression[:36])
    for expression in ('1/0', '1%0', 'sqrt(-1)', 'log(0)', '(-2)^.5', 'exp(1000)', '10^1000',
                       '2^10001', 'pow(2,10001)', 'round(1, .5)', 'round(1,101)', '1e300*10'):
        bad(lambda expression=expression: ScoreExpression(expression, values).evaluate(values), 'reject numeric error: ' + expression)
    catalog = load_catalog(DATA, log)
    ids = {external_id(obj): key for key, obj in catalog.records.items()}
    key = ids['T1053.005']
    blank = TTPDocument('Blank source', catalog)
    log('[Formula Audit 2/7] Entire matrix, constants, disabled inputs and scoped results', 1, 7)
    all_cells = {(key, slug) for key, obj in catalog.records.items()
                 for slug in tactic_phases(obj, catalog.domain) if slug in catalog.tactics}
    full = calculate_layer([blank], '50', 'Complete matrix', notify=log, scope='matrix')
    check(selected_cells(full) == all_cells, 'full constant covers every active mapped technique/tactic without selection')
    check(all(row['score'] == 50 for row in full.navigator_layer['techniques']), 'every full-matrix score is 50')
    bad(lambda: calculate_layer([blank], '50', 'Empty union'), 'empty selected union has actionable failure')
    full_zero = calculate_layer([blank], 'a>0 ? 100 : 0', 'Zero matrix', 'zero', log, scope='matrix')
    check(selected_cells(full_zero) == all_cells and all(r['score'] == 0 for r in full_zero.navigator_layer['techniques']),
          'whole matrix missing-zero comparison computes zero and includes zero-valued cells')
    unknown = calculate_layer([blank], 'a+1', 'Unknown matrix', notify=log, scope='matrix')
    check(not unknown.selected and len(unknown.navigator_layer['techniques']) == len(all_cells), 'missing default retains all candidate cells unscored')
    a, b = TTPDocument('Capability A', catalog), TTPDocument('Annotations B', catalog)
    assign_cells(a, {(key, 'execution')})
    a.navigator_layer = {'name': a.name, 'domain': catalog.domain, 'techniques': [
        {'techniqueID': 'T1053.005', 'score': 80},
        {'techniqueID': 'T1053.005', 'tactic': 'persistence', 'score': 60}]}
    b.navigator_layer = {'name': b.name, 'domain': catalog.domain,
        'gradient': {'colors': ['#00112200', '#ffeeddff'], 'minValue': 10, 'maxValue': 90},
        'filters': {'platforms': ['Linux']}, 'hideDisabled': True,
        'legendItems': [{'label': 'Research', 'color': '#ff0000'}],
        'links': [{'label': 'Layer link', 'url': 'https://example.com/layer', 'x_note': 'keep'}],
        'metadata': [{'name': 'Layer meta', 'value': 'B'}, {'divider': True}],
        'techniques': [{'techniqueID': 'T1053.005', 'score': 20, 'enabled': True, 'color': '#ff0000', 'comment': 'Global B',
            'links': [{'label': 'Evidence', 'url': 'https://example.com/global'}],
            'metadata': [{'name': 'Evidence', 'value': 'Global'}, {'name': SELECTION_MARKER, 'value': 'false'}, {'divider': True}]},
            {'techniqueID': 'T1053.005', 'tactic': 'execution', 'enabled': False, 'color': '#00ff00',
             'comment': 'Execution B', 'links': [], 'metadata': [{'name': 'Scope', 'value': 'Execution', 'x_note': 'keep'}]}]}
    before = a.fingerprint(), b.fingerprint()
    partial = calculate_layer([a,b], 'a>=75 ? 100 : 0', 'Partial', notify=log)
    check(selected_cells(partial) == {(key,'execution')} and partial.navigator_layer['techniques'][0]['score'] == 100,
          'selected-source formula preserves partial tactic scope')
    disabled = calculate_layer([a,b], 'b+1', 'Disabled', notify=log, scope='matrix')
    check(LayerAppearance(disabled.navigator_layer).cell('T1053.005','execution')['score'] is None,
          'disabled source score remains missing')
    disabled_zero = calculate_layer([a,b], 'b+1', 'Disabled zero', 'zero', log, scope='matrix')
    check(LayerAppearance(disabled_zero.navigator_layer).cell('T1053.005','execution')['score'] == 1, 'disabled input obeys explicit zero policy')
    conditional = calculate_layer([a,b], 'a>0 ? a : b', 'Missing conditional', notify=log)
    check(not conditional.selected, 'default missing policy checks even an unchosen variable branch')

    log('[Formula Audit 3/7] Independent property inheritance, fallback and source isolation', 2, 7)
    fields = ('gradient','color','comment','links','metadata','enabled','filters','legendItems')
    inherited = calculate_layer([a,b], '50', 'Inherited matrix', notify=log, scope='matrix', inheritance=dict.fromkeys(fields,'b'))
    rows = {(r['techniqueID'], r['tactic']):r for r in inherited.navigator_layer['techniques']}
    execution = rows['T1053.005','execution']
    persistence = rows['T1053.005','persistence']
    check(execution['score'] == 50 and execution['enabled'] is False and (key,'execution') in selected_cells(inherited),
          'inherited disabled state is independent of scored inclusion')
    check(execution['color'] == '#00ff00' and execution['comment'] == 'Execution B' and execution['links'] == [],
          'tactic-specific colors/comments/empty links override global source')
    check(execution['metadata'][0].get('x_note') == 'keep', 'structured annotation extensions survive inheritance')
    check(persistence['color'] == '#ff0000' and persistence['comment'] == 'Global B' and persistence['enabled'], 'global source row falls back in other tactics')
    check(not any(m.get('name') == SELECTION_MARKER for r in rows.values() for m in r.get('metadata',[])), 'source selection markers never leak into result')
    for field in ('gradient','filters','legendItems','links','metadata','hideDisabled'):
        check(inherited.navigator_layer[field] == b.navigator_layer[field], field + ': exact layer-level inheritance')
    check(any(r['enabled'] and 'color' not in r for r in rows.values() if r['techniqueID'] != 'T1053.005'),
          'absent source rows inherit default enabled and no synthetic colors')
    combined = calculate_layer([a,b], 'a', 'Mixed properties', notify=log, inheritance={'comment':'b','gradient':'b'})
    mixed = combined.navigator_layer['techniques'][0]
    check(mixed['comment'] == 'Execution B' and mixed['score'] == 80 and mixed['enabled'] and 'color' not in mixed,
          'annotation-only source contributes chosen properties without adding selected targets or state')
    check(set(selected_cells(combined)) == {(key,'execution')}, 'inheritance-only sources do not enlarge calculation scope')
    check(combined.navigator_layer['gradient']['maxValue'] == 90, 'explicit inherited gradient bounds remain unchanged')
    check(combined.navigator_layer['x_ttp_studio_formula']['inheritance']['comment'] == 'b', 'independent inheritance choices recorded')
    snapshot = snapshot_document(inherited)
    snapshot.navigator_layer['techniques'][0]['score'] = 123
    check(inherited.navigator_layer['techniques'][0]['score'] == 50, 'result snapshots are independent')
    for options in ({'scope':'bad'}, {'inheritance':{'bad':'a'}}, {'inheritance':{'color':'z'}}, {'inheritance':[]}):
        bad(lambda options=options: calculate_layer([a,b],'50','Invalid', **options), 'invalid scope/inheritance rejected: ' + str(options))
    bad(lambda: calculate_layer([a,b],'a/(a-a)','Invalid'), 'cell error prevents partial result')
    def cancel(message, current=0, total=0):
        if '[Formula 3/5]' in message:
            raise InterruptedError('Audit cancellation')
    try:
        calculate_layer([a,b],'50','Cancelled',notify=cancel,scope='matrix')
    except InterruptedError:
        check(True,'cancellation interrupts before publication')
    else:
        raise AssertionError('cancellation not observed')
    check((a.fingerprint(),b.fingerprint()) == before, 'success/failure/cancellation preserve every source field')
    bad(lambda: calculate_layer([a,TTPDocument('Foreign',catalog.for_domain('ics-attack'))],'50','Invalid'), 'mixed domains rejected')
    bad(lambda: calculate_layer([a,TTPDocument('Foreign',replace(catalog,dataset_id='f'*64))],'50','Invalid'), 'same-version custom dataset mixing rejected')

    log('[Formula Audit 4/7] Studio, Navigator and recovery round trips', 3, 7)
    save_studio(inherited,OUT/'result.studio.json',log,save_as=True)
    reopened = open_studio(DATA,OUT/'result.studio.json',log)
    check(reopened.navigator_layer == inherited.navigator_layer and selected_cells(reopened) == all_cells, 'Studio reopen retains computed cells, inherited properties and provenance')
    exported = document_layer(inherited)
    write_json_atomic(exported,OUT/'result.navigator.json',log)
    restored = imported_document(exported,catalog,'enabled')
    check(selected_cells(restored) == all_cells and restored.navigator_layer['x_ttp_studio_formula'] == inherited.navigator_layer['x_ttp_studio_formula'], 'Navigator round trip retains selected disabled cells and formula provenance')
    payload = session_payload([inherited],0,{})
    write_session(payload,OUT/'session.json',log)
    session = read_session(DATA,OUT/'session.json',log)
    check(session['documents'][0].navigator_layer == inherited.navigator_layer, 'recovery retains inherited lists and full matrix formula')
    for domain in ('mobile-attack','ics-attack'):
        current = catalog.for_domain(domain)
        result = calculate_layer([TTPDocument('Domain',current)],'max(10, 2^3)',domain,notify=log,scope='matrix')
        expected = {(k,s) for k,o in current.records.items() for s in tactic_phases(o,domain) if s in current.tactics}
        check(selected_cells(result) == expected and all(r['score'] == 10 for r in result.navigator_layer['techniques']), domain + ': entire domain matrix and advanced function')

    log('[Formula Audit 5/7] Native scope, inheritance, validation retry and background installation', 4, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    parent = Harness()
    dialog = FormulaDialog([a,b],a,parent)
    dialog.show()
    app.processEvents()
    check(dialog.scope.currentData() == 'selected' and len(dialog.inheritance) == 8, 'native controls expose backwards-compatible scope and all property choices')
    dialog.scope.setCurrentIndex(dialog.scope.findData('matrix'))
    dialog.expression.setText('1/0')
    dialog.calculate()
    wait(lambda:not dialog.worker.isRunning() and dialog.create_button.isEnabled())
    check(not parent.installed and dialog.result_document is None and 'Failed:' in dialog.status.text(), 'invalid native formula remains reviewable without adding a tab')
    dialog.expression.setText('a>=75 ? max(a,90) : 10')
    dialog.missing.setCurrentIndex(dialog.missing.findData('zero'))
    dialog.name.setText('Native derived matrix')
    for field in fields:
        dialog.inheritance[field].setCurrentIndex(dialog.inheritance[field].findData('b'))
    dialog.report('Ready: review the calculation scope and inherited properties.', 1, 1)
    check(dialog.grab().save(str(OUT/'formula.png')), 'formula UI screenshot')
    dialog.options_tabs.setCurrentIndex(1)
    app.processEvents()
    check(dialog.grab().save(str(OUT/'inheritance.png')), 'inheritance UI screenshot')
    dialog.create_button.click()
    check(not dialog.options_tabs.isEnabled(), 'calculation controls freeze during background work')
    wait(lambda:dialog.result_document is not None and not dialog.worker.isRunning())
    check(parent.installed == [dialog.result_document] and parent.opened, 'native worker installs one independent result')
    check(selected_cells(dialog.result_document) == all_cells, 'native matrix scope computes all cells')
    native = LayerAppearance(dialog.result_document.navigator_layer).cell('T1053.005','execution')
    check(native['score'] == 90 and native['comment'] == 'Execution B' and native['enabled'] is False, 'native conditional formula and independent inheritance applied together')
    check((a.fingerprint(),b.fingerprint()) == before, 'native result never changes sources')
    check(any('[Formula 5/5]' in row[0] for row in parent.messages), 'visible native stage completion is reported')
    parent.close()
    log('[Formula Audit 6/7] Dataset pointer and file integrity', 5, 7)
    check(all(path.read_bytes() == data for path,data in pointers.items()), 'official dataset pointers unchanged')
    log('[Formula Audit 7/7] Publishing report', 6, 7)
    (OUT/'audit.json').write_text(json.dumps({'status':'PASS','checks':CHECKS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log(f'[Formula Audit] PASS: {len(CHECKS)} checks',7,7)


if __name__ == '__main__':
    main()
