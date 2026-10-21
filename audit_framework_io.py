"""Verify actual framework choices and selective file IO. Workflow: README.md."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import time
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets

from framework_dialog import FrameworkOptionsDialog
from framework_io import framework_payload, read_framework_document, selection
from layer_analysis import snapshot_document
from main import MainWindow, configure_application
from navigator_dialogs import ImportLayerDialog
from navigator_integration import update_annotation
from localization import language_manager
from studio_files import open_studio, save_studio, StudioReader
from ttp_documents import document_payload, export_document_csv, export_document_json

ROOT = Path(__file__).resolve().parent
DATA = ROOT/'data'/'attack'
OUT = ROOT/'artifacts'/'framework-io'
CHECKS = []


def log(message,*args):
    print(message,flush=True)


def check(value,label):
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)
    log('[Check] '+label)


def wait(condition,label):
    deadline = time.monotonic()+60
    while not condition():
        if time.monotonic()>deadline:
            raise TimeoutError(label)
        QtWidgets.QApplication.processEvents()
        time.sleep(.01)
    QtWidgets.QApplication.processEvents()


def drive_choices(choices, cancel=False):
    def act():
        dialog = QtWidgets.QApplication.activeModalWidget()
        if not isinstance(dialog, FrameworkOptionsDialog):
            QtCore.QTimer.singleShot(20,act)
            return
        check(dialog.attack.isChecked() and dialog.atlas.isChecked(),'interactive options default both frameworks on')
        if cancel:
            dialog.reject()
        else:
            dialog.attack.setChecked(choices[0])
            dialog.atlas.setChecked(choices[1])
            dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).click()
    QtCore.QTimer.singleShot(0,act)


def main():
    log(f'Input directory: {DATA.resolve()}')
    log(f'Output directory: {OUT.resolve()}')
    OUT.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    log('[Framework audit 1/5] Defaults and independent choices')
    for mode in ('read','write'):
        dialog=FrameworkOptionsDialog(mode,OUT/'sample.json')
        check(dialog.choices()==(True,True),mode+' defaults to both frameworks')
        dialog.attack.setChecked(False)
        check(dialog.choices()==(False,True),mode+' supports ATLAS only')
        dialog.atlas.setChecked(False)
        check(not dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).isEnabled(),mode+' prevents empty choice')
        dialog.reject()
    try:
        selection((False,False))
    except ValueError:
        check(True,'empty choice rejected by file IO as well as UI')
    else:
        raise AssertionError('empty selection accepted')
    w=MainWindow(DATA,settings_path=OUT/'settings.ini',session_path=None)
    w.show()
    wait(lambda:w.loaded_ok and not w.loader.isRunning(),'initial catalogs')
    attack_key=next(iter(w.catalog.records))
    atlas_key=next(iter(w.atlas_catalog.records))
    w.choose_technique_occurrence(attack_key,True)
    w.choose_atlas_technique(atlas_key,'',True)
    source=w.current_document
    update_annotation(source,attack_key,'','ATT&CK\ncomment',1,'#112233')
    update_annotation(source.atlas_document,atlas_key,'','ATLAS\ncomment',2,'#ffffff')
    source_token=source.content_token()
    log('[Framework audit 2/5] JSON/CSV/Studio projections and filtered reads')
    paths={}
    for opts,label in [((True,True),'both'),((True,False),'attack'),((False,True),'atlas')]:
        output=save_studio(snapshot_document(source),OUT/(label+'.studio.json'),log,save_as=True,frameworks=opts)
        paths[label]=output.save_path
        payload=json.loads(output.save_path.read_text(encoding='utf-8'))
        check(('atlas_workspace' in payload)==(opts==(True,True)),label+' Studio payload framework layout')
        if label=='atlas':
            check('attack' not in payload and set(payload['frameworks'])=={'atlas'},'ATLAS-only JSON contains no ATT&CK block')
        reopened=open_studio(DATA,output.save_path,log,fallback_catalog=w.catalog)
        check(reopened.selected==({attack_key} if opts[0] else set()),label+' Studio file reopens with only requested ATT&CK data')
        check(bool(reopened.atlas_document and atlas_key in reopened.atlas_document.selected)==opts[1],label+' Studio file reopens with requested ATLAS data')
        check(not reopened.dirty,label+' selected file opens clean')
        check(source.content_token()==source_token,label+' output preserves full source Workplace')
        check(output.dirty==(opts!=(True,True)),label+' partial save does not mark complete Workplace clean')
        draft=snapshot_document(source)
        csvpath=export_document_csv(draft,OUT/(label+'.csv'),log,opts)
        with csvpath.open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream))
        expected=({'atlas-atlas'} if opts[1] else set()) | ({source.catalog.domain} if opts[0] else set())
        check({row['attack_domain'] for row in rows}==expected,label+' CSV includes only chosen frameworks')
        check(len(rows)==sum(opts) and all('\n' in row['comment'] for row in rows),label+' CSV retains multiline comments and row counts')
    for opts,label in [((True,False),'attack'),((False,True),'atlas')]:
        filtered=open_studio(DATA,paths['both'],log,frameworks=opts,fallback_catalog=w.catalog)
        check(filtered.save_path is None and filtered.document_id!=source.document_id,label+' filtered read is independent and does not own the source file')
        check(bool(filtered.selected)==opts[0] and bool(filtered.atlas_document)==opts[1],label+' filtered read includes exactly requested frameworks')
    payload=document_payload(source)
    payload['attack']['version']='9999.0'
    reader=StudioReader(DATA,log)
    with patch('studio_files.load_catalog',side_effect=AssertionError('Do not reload excluded ATT&CK catalog')):
        filtered=read_framework_document(reader,payload,(False,True),w.catalog)
    check(atlas_key in filtered.atlas_document.selected,'ATLAS-only read skips unavailable ATT&CK dataset')
    check(('',w.catalog.version) in reader.catalogs,'ATLAS-only read reuses current catalog without reading ATT&CK data files')
    payload=document_payload(source)
    payload['atlas_workspace']['attack']['dataset_sha256']='f'*64
    filtered=read_framework_document(StudioReader(DATA,log),payload,(True,False),w.catalog)
    check(attack_key in filtered.selected and filtered.atlas_document is None,'ATT&CK-only read skips unavailable ATLAS cache')

    log('[Framework audit 3/5] Interactive Open, Save, Export and cancellation')
    drive_choices((False,True))
    with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(paths['both']),'Studio JSON (*.json)')):
        imported=w.open_studio_document()
    wait(lambda:w.loaded_ok,'filtered import')
    check(not imported.selected and atlas_key in imported.atlas_document.selected,'Open menu uses actual ATLAS-only checkbox choice')
    check(source.content_token()==source_token,'filtered Open does not modify original document')
    w.activate_document(0)
    wait(lambda:w.loaded_ok,'original workplace')
    drive_choices((True,False))
    ui_output=OUT/'ui-save.json'
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(ui_output),'Studio JSON (*.json)')):
        check(w.save_studio_document(save_as=True)==ui_output.resolve(),'Save As honors actual framework dialog')
    check('atlas_workspace' not in json.loads(ui_output.read_text(encoding='utf-8')) and source.dirty,
          'partial Save leaves omitted ATLAS selected and the full document dirty')
    before=source.content_token(),source.saved_fingerprint,ui_output.read_bytes()
    drive_choices((True,True),cancel=True)
    check(w.save_studio_document() is None,'cancel framework choice cancels Save')
    check(before==(source.content_token(),source.saved_fingerprint,ui_output.read_bytes()),'cancel does not modify disk, selections or save baseline')
    export_path=OUT/'ui-atlas.json'
    drive_choices((False,True))
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(export_path),'JSON files (*.json)')):
        check(w.export_current_document()==export_path.resolve(),'Export menu honors actual framework dialog')
    check(set(json.loads(export_path.read_text(encoding='utf-8'))['frameworks'])=={'atlas'},'interactive JSON export omits ATT&CK')

    log('[Framework audit 4/5] Navigator per-framework layers and import checkboxes')
    workbook=w.export_all_layers_workbook(OUT/'preview-both.xlsx')
    check({d.catalog.domain for d in workbook.documents}=={source.catalog.domain,'atlas-atlas'},
          'Excel default includes both frameworks')
    workbook.reject()
    workbook=w.export_all_layers_workbook(OUT/'atlas.xlsx',frameworks=(False,True))
    check(all(d.catalog.domain=='atlas-atlas' for d in workbook.documents),'Excel framework choice excludes ATT&CK sheets')
    workbook.export_button.click()
    wait(lambda:workbook.output_path is not None and not workbook.running_worker(),'ATLAS Excel export')
    check((OUT/'atlas.xlsx').stat().st_size>0,'ATLAS-only Excel writes a real workbook')
    workbook.reject()
    nav=OUT/'both.navigator.json'
    w.export_current_document(nav,'navigator',visible_only=False)
    layers=json.loads(nav.read_text(encoding='utf-8'))
    check(isinstance(layers,list) and {p['domain'] for p in layers}=={source.catalog.domain,'atlas-atlas'},'Navigator default exports both as separate layers')
    for opts,label in [((True,False),'attack'),((False,True),'atlas')]:
        target=OUT/(label+'.navigator.json')
        w.export_current_document(target,'navigator',visible_only=False,frameworks=opts)
        layer=json.loads(target.read_text(encoding='utf-8'))
        check(layer['domain']==('atlas-atlas' if opts[1] else source.catalog.domain),label+' Navigator export honors framework choice')
    importer=ImportLayerDialog(DATA,nav,w.catalog,w,install=w.install_imported_documents)
    importer.show()
    wait(lambda:not importer.busy and importer.results and not importer.running_worker(),'Navigator previews')
    check(importer.read_attack.isChecked() and importer.read_atlas.isChecked(),'Navigator import defaults both frameworks on')
    importer.read_attack.setChecked(False)
    wait(lambda:not importer.busy,'Navigator choice')
    indices=importer.selected_indices()
    check(len(indices)==1 and importer.layers[indices[0]]['domain']=='atlas-atlas','Navigator import excludes ATT&CK when unchecked')
    importer.read_atlas.setChecked(False)
    check(not importer.import_button.isEnabled(),'Navigator import blocks both frameworks off')
    importer.read_atlas.setChecked(True)
    wait(lambda:importer.import_button.isEnabled(),'ATLAS import ready')
    importer.import_button.click()
    wait(lambda:not importer.isVisible() and w.loaded_ok,'ATLAS layer installed')
    check(not w.current_document.selected and atlas_key in w.current_document.atlas_document.selected,
          'ATLAS Navigator imports into the ATLAS group of its Workplace')
    log('[Framework audit 5/5] Preview and report')
    dialog=FrameworkOptionsDialog('write',OUT/'example.json',w)
    dialog.show()
    language_manager().set_language('zh_TW')
    app.processEvents()
    check('輸出' in dialog.windowTitle() and dialog.choices()==(True,True),'framework dialog localizes while preserving default choices')
    dialog.grab().save(str(OUT/'framework-options.png'))
    dialog.reject()
    language_manager().set_language('en')
    (OUT/'checks.json').write_text(json.dumps({'passed':len(CHECKS),'checks':CHECKS},ensure_ascii=False,indent=2),encoding='utf-8')
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Discard):
        w.close()
    app.processEvents()
    log(f'PASS: {len(CHECKS)} checks')


if __name__=='__main__':
    main()
