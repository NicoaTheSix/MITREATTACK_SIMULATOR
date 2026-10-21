"""NAV-018 pinned scalar reference, layer/UI and persistence audit. Flow: README.md."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import math
from PySide6 import QtWidgets
from audit_formula_features import Harness, wait
from attack_catalog import load_catalog, external_id, tactic_phases
from layer_analysis import calculate_layer
from layer_analysis_dialogs import FormulaDialog
from main import configure_application
from navigator_integration import document_layer, imported_document
from navigator_visuals import LayerAppearance
from score_expression import ScoreExpression
from studio_files import save_studio, open_studio, session_payload, write_session, read_session
from ttp_documents import TTPDocument
from ttp_selection import assign_cells

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
REFERENCE = ROOT / 'scripts' / 'formula-reference'
OUT = ROOT / 'artifacts' / 'formula-compatibility'
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


def equal(actual, expected):
    return math.isclose(actual, expected, rel_tol=1e-13, abs_tol=1e-14)


def main():
    for path in (DATA / 'latest.json', REFERENCE / 'cases.json', REFERENCE / 'golden.json'):
        log(f'Input file: {path.resolve()}')
    log(f'Input directory: {DATA.resolve()}')
    for name in ('audit.json', 'navigator.studio.json', 'session.json', 'syntax.png'):
        log(f'Output file: {(OUT / name).resolve()}')
    OUT.mkdir(parents=True, exist_ok=True)
    pointers = {p: p.read_bytes() for p in (DATA/'latest.json', DATA/'active.json') if p.exists()}
    log('[Scalar Audit 1/6] Verify provenance and pinned golden scalar results', 0, 6)
    reference = json.loads((REFERENCE/'golden.json').read_text(encoding='utf-8'))
    check(reference['version'] == '15.2.0', 'reference runtime pin')
    check(reference['inputSHA256'] == sha256((REFERENCE/'cases.json').read_bytes()).hexdigest(), 'golden fixture matches exact case bytes')
    check(len(reference['upstream']) == 2, 'recorded Navigator tag URLs and SHA-256 provenance')
    for index, case in enumerate(reference['results']):
        expression, scores, expected = case['expression'], case['scores'], case['result']
        label = f'{index}: {case["syntax"]}: {expression} @ {scores}'
        if expected['kind'] == 'finite':
            actual = ScoreExpression(expression, scores, case['syntax']).evaluate(scores)
            check(equal(actual, expected['value']), label)
        else:
            bad(lambda: ScoreExpression(expression, scores, case['syntax']).evaluate(scores), label)
    log('[Scalar Audit 2/6] Earlier arithmetic and bounded rejection', 1, 6)
    legacy = [('round(2.5)',2),('round(-2.5)',-2),('round(125,-1)',120),
              ('not 0>1',1),('0.1+0.2==0.3',0),('5%-3',-1)]
    for expression, value in legacy:
        check(ScoreExpression(expression, {}).evaluate({}) == value, 'legacy unchanged: '+expression)
    for expression in ('a<b<c','3%0','SIN(0)','round(2,101)'):
        bad(lambda: ScoreExpression(expression, {'a','b','c'}).evaluate({'a':1,'b':2,'c':3}), 'legacy rejects: '+expression)
    check(ScoreExpression('e', {'e'}, 'navigator').evaluate({'e':12}) == 12, 'layer e shadows Euler constant explicitly')
    check(ScoreExpression('EXP(1)', {'e'}, 'navigator').variables == set(), 'exp(1) is an unambiguous Euler constant')
    for expression in ('a=3','a.b','a[0]','[1,2]','{a:1}','__import__("os")','2pi',
                       '3!','50%','a;b','"abc"','1e301','2^10001','pow(2,10001)',
                       'sqrt(-1)','1/0','log(0)','2^-10001','nthRoot(4)',
                       '+'.join(['1']*65),'('*25+'1'+')'*25):
        bad(lambda: ScoreExpression(expression, {'a'}, 'navigator').evaluate({'a':1}), 'bounded Navigator rejection: '+expression[:35])
    bad(lambda: ScoreExpression('1', {}, 'unknown'), 'invalid syntax profile')
    for name in ('sin','cos','tan','asin','acos','atan','sinh','cosh','tanh','asinh','acosh','atanh',
                 'log2','log10','log1p','expm1','cbrt','sign'):
        bad(lambda: ScoreExpression(name+'(1,2)', {}, 'navigator'), 'unary arity: '+name)
    log('[Scalar Audit 3/6] Same source values through the complete per-cell layer calculation', 2, 6)
    catalog = load_catalog(DATA, log)
    key = next(k for k,o in catalog.records.items() if tactic_phases(o,catalog.domain))
    slug = next(s for s in catalog.tactic_order if s in tactic_phases(catalog.records[key],catalog.domain))
    attack_id = external_id(catalog.records[key])
    documents = [TTPDocument('Source '+alias,catalog) for alias in 'abc']
    for doc in documents:
        assign_cells(doc,{(key,slug)})
    layer_count = 0
    for case in reference['results']:
        if case['result']['kind'] != 'finite':
            continue
        for alias, doc in zip('abc',documents):
            doc.navigator_layer = {'name':doc.name,'domain':catalog.domain,
                                  'techniques':[{'techniqueID':attack_id,'tactic':slug,'score':case['scores'][alias]}]}
        before = [doc.fingerprint() for doc in documents]
        result = calculate_layer(documents,case['expression'],'Reference result',syntax=case['syntax'])
        actual = LayerAppearance(result.navigator_layer).cell(attack_id,slug)['score']
        check(equal(actual,case['result']['value']), 'layer cell matches golden: '+case['expression'])
        check([doc.fingerprint() for doc in documents] == before, 'layer inputs immutable: '+case['expression'])
        layer_count += 1
        if layer_count % 50 == 0:
            log('[Scalar Audit 3/6] Per-cell golden comparisons',layer_count, len(reference['results']))
    log('[Scalar Audit 4/6] Syntax provenance and complete document round trips', 3, 6)
    result = calculate_layer(documents,'ROUND(a/2)+sin(pi/2)','Navigator syntax',syntax='navigator')
    expected = deepcopy(result.navigator_layer['x_ttp_studio_formula'])
    check(expected['syntax']=='navigator', 'Navigator syntax persisted in provenance')
    legacy_result = calculate_layer(documents,'round(a/2)','Studio syntax')
    check(legacy_result.navigator_layer['x_ttp_studio_formula']['syntax']=='studio', 'API defaults to earlier Studio syntax')
    save_studio(result,OUT/'navigator.studio.json',log,save_as=True)
    check(open_studio(DATA,OUT/'navigator.studio.json',log).navigator_layer['x_ttp_studio_formula']==expected,'Studio syntax round trip')
    check(imported_document(document_layer(result),catalog,'enabled').navigator_layer['x_ttp_studio_formula']==expected,'Navigator syntax round trip')
    write_session(session_payload([result,legacy_result],0,{}),OUT/'session.json',log)
    restored=read_session(DATA,OUT/'session.json',log)['documents']
    check([doc.navigator_layer['x_ttp_studio_formula']['syntax'] for doc in restored]==['navigator','studio'],'both profiles survive recovery')
    old = deepcopy(result.navigator_layer)
    old['x_ttp_studio_formula'].pop('syntax')
    check('syntax' not in imported_document(old,catalog,'enabled').navigator_layer['x_ttp_studio_formula'],'old provenance is preserved without recomputation')
    log('[Scalar Audit 5/6] Native syntax default, retry, worker and source protection',4,6)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    parent=Harness()
    before=[doc.fingerprint() for doc in documents]
    dialog=FormulaDialog(documents,documents[0],parent)
    dialog.show()
    app.processEvents()
    check(dialog.syntax.currentData()=='navigator','new UI defaults to Navigator scalar')
    check(dialog.syntax.findData('studio')>=0,'UI exposes earlier arithmetic explicitly')
    check(dialog.grab().save(str(OUT/'syntax.png')),'native syntax screenshot')
    dialog.expression.setText('nthRoot(8,3)')
    dialog.calculate()
    wait(lambda:not dialog.worker.isRunning() and dialog.create_button.isEnabled())
    check(not parent.installed and dialog.result_document is None,'invalid lowercase function installs no partial result')
    dialog.syntax.setCurrentIndex(dialog.syntax.findData('studio'))
    dialog.expression.setText('nthRoot(8,3)+round(2.5)')
    dialog.calculate()
    wait(lambda:dialog.result_document is not None and not dialog.worker.isRunning())
    check(equal(LayerAppearance(dialog.result_document.navigator_layer).cell(attack_id,slug)['score'],4),'native Studio extension and previous rounding')
    check([doc.fingerprint() for doc in documents]==before,'native syntax selection and retry preserve sources')
    parent.close()
    app.processEvents()
    check(all(p.read_bytes()==content for p,content in pointers.items()),'official dataset pointers unchanged')
    log('[Scalar Audit 6/6] Publish complete audit report',5,6)
    (OUT/'audit.json').write_text(json.dumps({'passed':True,'count':len(CHECKS),
        'reference_cells':len(reference['results']),'layer_cells':layer_count,'checks':CHECKS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    log(f'[Scalar Audit] PASS: {len(CHECKS)} checks',6,6)


if __name__=='__main__':
    main()
