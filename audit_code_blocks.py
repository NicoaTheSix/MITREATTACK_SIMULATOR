"""Real Qt checks for collapsed CAR code panels and exact clipboard text. Flow: README.md."""
from copy import deepcopy
import json
from pathlib import Path
from PySide6 import QtCore,QtGui,QtWidgets,QtTest
from code_blocks import CodeDetailView,CollapsibleCodeBlock,code_html
from car_catalog import load_car,ROOT as CAR_ROOT
from car_documents import empty_catalog
from car_views import CarBrowser
from ttp_documents import TTPDocument
from main import configure_application
from localization import language_manager

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/code-blocks'
CHECKS=[]


def log(message,*_): print(message,flush=True)


def check(value,label):
    assert value,label
    CHECKS.append(label)


def click(widget):
    QtTest.QTest.mouseClick(widget,QtCore.Qt.MouseButton.LeftButton)
    QtWidgets.QApplication.processEvents()


class Host(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.current_document=TTPDocument('Code-panel audit',empty_catalog())
        self.workspace=QtWidgets.QStackedWidget()
        layout=QtWidgets.QVBoxLayout(self);layout.addWidget(self.workspace)
        self.browser=CarBrowser(self);self.workspace.addWidget(self.browser)
        self.targets=[]

    operation_report=staticmethod(log)

    def show_car_technique(self,key):self.targets.append(key)

    def reveal_car_browser(self):self.workspace.setCurrentWidget(self.browser)


def main():
    print('Input verified CAR manifest: '+str(CAR_ROOT/'source.json'),flush=True)
    print('Output previews/report: '+str(OUT),flush=True)
    print('Settings/session outputs: None (isolated Qt fixture; no production window)',flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    print('[Code panels 1/4] Native frame defaults, exact clipboard and bounded geometry',flush=True)
    value='  α = "<&>"\r\n\tpath = r"C:\\研究\\sample.exe"\r\n  trailing spaces  \n\n'
    record={'description':'<script>literal text</script>','code':value,'zero':0,'enabled':False}
    raw_json=json.dumps(record,ensure_ascii=False,indent=2)
    view=CodeDetailView(log);view.resize(510,420)
    view.setHtml('<p><a href="car:technique/T1059">Technique link</a></p>'+
        code_html('Implementation code',value,'DNIF')+code_html('Complete native record — tests are reference text only',raw_json))
    view.show();QtTest.QTest.qWait(40)
    check(len(view.blocks)==2,'two independent native code panels')
    for i,block in enumerate(view.blocks):
        check(not block.toggle.isChecked() and block.editor.isHidden(),'collapsed by default '+str(i))
        check(block.copy_button.isVisible() and block.editor.isReadOnly(),'copy remains available and editor read-only '+str(i))
        view.ensureWidgetVisible(block);app.processEvents();click(block.copy_button)
        check(app.clipboard().text()==[value,raw_json][i],'collapsed Copy preserves complete original whitespace/escapes/Unicode '+str(i))
    first,second=view.blocks
    click(first.toggle)
    check(first.toggle.isChecked() and not first.editor.isHidden() and second.editor.isHidden(),'expanding one panel leaves the other collapsed')
    check(first.editor.lineWrapMode()==QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap,'long code uses horizontal scrolling')
    first.editor.setFocus();before=first.editor.toPlainText();QtTest.QTest.keyClicks(first.editor,'Overwrite')
    check(first.editor.toPlainText()==before and first.code==value,'typing cannot change code or stored copy text')
    click(first.copy_button);check(app.clipboard().text()==value,'expanded Copy uses full original text')
    click(first.toggle);check(first.editor.isHidden(),'header collapses expanded editor')
    positions=[];view.anchorClicked.connect(lambda url:positions.append(url.toString()))
    view.verticalScrollBar().setValue(0);app.processEvents()
    rich=view.sections[0];cursor=rich.document().find('Technique link');cursor.setPosition(cursor.selectionStart()+2)
    point=rich.cursorRect(cursor).center();QtTest.QTest.mouseClick(rich.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=point)
    check(positions==['car:technique/T1059'],'real rich-text anchor click forwards existing internal route')
    second.toggle.setChecked(True);view.ensureWidgetVisible(second);app.processEvents()
    check(second.copy_button.mapTo(view.viewport(),QtCore.QPoint()).x()>=0 and
        second.copy_button.mapTo(view.viewport(),second.copy_button.rect().topRight()).x()<=view.viewport().width(),
        'long header retains visible Copy button at narrow width')
    check(json.loads(second.code)==record,'native JSON copied without HTML interpretation')
    second.toggle.setChecked(False);QtTest.QTest.qWait(20);view.grab().save(str(OUT/'collapsed-en.png'))
    first.toggle.setChecked(True);view.ensureWidgetVisible(first);QtTest.QTest.qWait(20);view.grab().save(str(OUT/'expanded-en.png'))
    print('[Code panels 2/4] Bilingual state, empty/long text and re-entry defaults',flush=True)
    manager=language_manager();manager.set_language('zh_TW');manager.refresh_all();app.processEvents()
    check(first.toggle.text()=='實作程式碼' and first.toggle.isChecked(),'language switch translates title and retains expanded state')
    click(first.copy_button);check(app.clipboard().text()==value and first.copy_button.text()=='已複製','Chinese copied confirmation retains original code')
    view.grab().save(str(OUT/'expanded-zh.png'));manager.set_language('en')
    view.setHtml(code_html('Implementation code','')+code_html('JSON','X'*12000));QtTest.QTest.qWait(30)
    check(all(b.editor.isHidden() for b in view.blocks),'new entry resets every block to collapsed')
    click(view.blocks[0].copy_button);check(app.clipboard().text()=='','empty block copies exactly empty text')
    block=view.blocks[1];view.ensureWidgetVisible(block);click(block.toggle);app.processEvents()
    check(block.editor.height()<=360 and block.editor.horizontalScrollBar().maximum()>0,'very long line stays inside bounded editor')
    click(block.copy_button);check(app.clipboard().text()=='X'*12000,'long text Copy is not truncated')
    view.close()
    print('[Code panels 3/4] Real CAR analytic, model, sensor and archived native records',flush=True)
    car=load_car(notify=log);host=Host();host.resize(1100,850);host.show()
    browser=host.browser;browser.set_catalog(car);browser.refresh();baseline=host.current_document.content_token()
    original=deepcopy(car.analytics)
    analytic=car.analytics['CAR-2013-04-002'];browser.open_analytic(analytic['id']);QtTest.QTest.qWait(40)
    blocks=browser.details.blocks
    check(blocks and all(b.editor.isHidden() for b in blocks),'real pictured analytic opens with every panel collapsed')
    codes=[b for b in blocks if b.toggle.text()=='Implementation code']
    implementations=[i for i in analytic.get('implementations',[]) if isinstance(i.get('code'),str)]
    check([b.code for b in codes]==[i['code'] for i in implementations],'all native implementation code is rendered as original multiline text')
    for block,implementation in zip(codes,implementations):
        browser.details.ensureWidgetVisible(block);app.processEvents();click(block.copy_button)
        check(app.clipboard().text()==implementation['code'],'real implementation copies original '+implementation['type'])
    metadata=[b for b in blocks if b.toggle.text()=='Implementation metadata (JSON)']
    check([json.loads(b.code) for b in metadata]==[{k:v for k,v in i.items() if k!='code'} for i in analytic['implementations']],
        'all implementation metadata, including link-only records, retained')
    full=next(b for b in blocks if b.toggle.text().startswith('Complete native record'))
    browser.details.ensureWidgetVisible(full);click(full.copy_button)
    check(json.loads(app.clipboard().text())==analytic,'complete native record Copy retains every original field')
    code=codes[-1];code.toggle.setChecked(True);QtTest.QTest.qWait(80)
    browser.details.ensureWidgetVisible(code,0,0);QtTest.QTest.qWait(60)
    check(code.editor.isVisible() and code.editor.mapTo(browser.details.viewport(),QtCore.QPoint()).y()<browser.details.viewport().height(),
        'expanded native implementation editor is reachable in shared page scroll')
    host.grab().save(str(OUT/'analytic-expanded.png'))
    browser.open_analytic('CAR-2013-01-002');QtTest.QTest.qWait(20)
    check(all(b.editor.isHidden() for b in browser.details.blocks),'analytic without implementation opens normally and collapsed')
    browser.open_analytic(analytic['id']);QtTest.QTest.qWait(20)
    check(all(not b.toggle.isChecked() for b in browser.details.blocks),'returning to an analytic defaults to collapsed again')
    QtTest.QTest.qWait(80);browser.details.ensureWidgetVisible(browser.details.blocks[-1],0,0);QtTest.QTest.qWait(60)
    host.grab().save(str(OUT/'analytic-collapsed.png'))
    browser.show_model('process/create/exe');QtTest.QTest.qWait(20)
    check(len(browser.details.blocks)==1 and json.loads(browser.details.blocks[0].code)==car.models['process'],'model native JSON uses same collapsed component')
    browser.show_sensor('sysmon_13');QtTest.QTest.qWait(20)
    check(len(browser.details.blocks)==1 and json.loads(browser.details.blocks[0].code)==car.sensors['sysmon_13'],'sensor native JSON uses same collapsed component')
    browser.render_detail('<h1>Unresolved technique</h1><pre>{"status":"Unresolved"}</pre>')
    check(len(browser.details.blocks)==1 and browser.details.blocks[0].editor.isHidden(),'generic unresolved JSON also collapses safely')
    print('[Code panels 4/4] Read-only state and source preservation',flush=True)
    check(host.current_document.content_token()==baseline,'expanding/copying/navigation never edits Workspace content or dirty baseline')
    check(car.analytics==original,'native source records unchanged')
    host.close()
    (OUT/'audit.json').write_text(json.dumps({'passed':True,'count':len(CHECKS),'checks':CHECKS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'[Code panels] PASS: {len(CHECKS)} checks',flush=True)


if __name__=='__main__':main()
