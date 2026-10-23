"""Independent CAR reference-tab lifecycle and session compatibility. Workflow: README.md."""
import json
from pathlib import Path
from unittest.mock import patch
from PySide6 import QtCore,QtTest,QtWidgets
from main import MainWindow,configure_application
from audit_export_options import wait
from localization import language_manager
from studio_files import session_payload,write_session,read_session

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/car-tabs'


def main():
    print('Input dataset root: '+str(ROOT/'data/attack'),flush=True)
    print('Input/output isolated settings: '+str(OUT/'settings.ini'),flush=True)
    print('Output session/report/preview: '+str(OUT),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    checks=[]
    def check(value,label):
        assert value,label
        checks.append(label);print('[Check] '+label,flush=True)
    print('[CAR tabs 1/4] Real Workplace opening and independent upper reference',flush=True)
    w=MainWindow(ROOT/'data/attack',settings_path=OUT/'settings.ini',session_path=None);w.show()
    try:
        wait(lambda:w.loaded_ok and not w.loader.isRunning())
        w.set_navigation_scope('both');doc=w.current_document;baseline=doc.content_token()
        check(w.car_browser_tab_index<0,'CAR tab starts closed')
        w.switch_category('Workplace');w.open_car_browser_button.click()
        index=w.car_browser_tab_index
        check(index>=len(w.documents) and w.document_tabs.tabData(index)=='__car_browser__','CAR reference shares filenames/Technique Details tab bar')
        check(w.workspace.currentWidget() is w.car_browser and w.tabs.indexOf(w.car_browser)<0,'CAR is independent of lower matrix tabs')
        check(w.details_tab_index>=0 and w.details_tab_index!=index,'Technique Details and CAR coexist')
        count=w.document_tabs.count();w.open_car_browser_button.click()
        check(w.document_tabs.count()==count,'repeated Workplace opening reuses one CAR tab')
        w.car_browser.search.setText('suspicious')
        identity='CAR-2013-04-002';w.car_browser.open_analytic(identity)
        check(w.document_tabs.currentIndex()==index and identity in w.car_browser.details.toPlainText(),'direct analytic opens in CAR reference')
        content=w.car_browser.details.toPlainText()
        w.document_tabs.setCurrentIndex(w.details_tab_index);app.processEvents()
        check(w.workspace.currentWidget() is w.details_page,'Technique Details tab activates its own page')
        w.document_tabs.setCurrentIndex(w.car_browser_tab_index);app.processEvents()
        check(w.workspace.currentWidget() is w.car_browser and w.car_browser.details.toPlainText()==content,'returning to CAR preserves its detail')
        print('[CAR tabs 2/4] Close buttons, context menu, documents and direct links',flush=True)
        close=w.document_tabs.tabButton(w.car_browser_tab_index,QtWidgets.QTabBar.ButtonPosition.RightSide)
        QtTest.QTest.mouseClick(close,QtCore.Qt.MouseButton.LeftButton)
        check(w.car_browser_tab_index<0 and w.workspace.currentWidget() is w.tabs,'CAR close returns to active document')
        check(doc.content_token()==baseline and w.details_tab_index>=0,'closing CAR retains document and Technique Details')
        w.open_car_browser_button.click()
        check(w.car_browser.search.text()=='suspicious' and w.car_browser.details.toPlainText()==content,'Workplace reopening preserves query and current detail')
        w.document_tabs.setCurrentIndex(w.details_tab_index);w.close_car_browser()
        check(w.workspace.currentWidget() is w.details_page,'closing inactive CAR leaves Technique Details active')
        w.car_browser.open_analytic(identity)
        check(w.car_browser_tab_index>=0 and w.workspace.currentWidget() is w.car_browser,'direct analytic recreates a closed CAR tab')
        w.close_details_page()
        check(w.workspace.currentWidget() is w.car_browser and w.car_browser_tab_index>=0,'closing inactive Technique Details leaves CAR active')
        w.show_document_context_menu(w.document_tabs.tabRect(w.car_browser_tab_index).center())
        menu=w.document_context_menu
        check([a.text() for a in menu.actions()]==['Close CAR Browser'],'CAR context menu has no file rename/domain actions')
        menu.actions()[0].trigger();menu.close()
        check(w.car_browser_tab_index<0,'context action closes CAR')
        w.car_browser.navigate('car:model/process');w.car_browser.navigate('car:sensor/sysmon_13')
        check(sum(w.document_tabs.tabData(i)=='__car_browser__' for i in range(w.document_tabs.count()))==1,'model/sensor links reuse the same CAR reference')
        w.ensure_details_tab();old_index=w.car_browser_tab_index
        w.new_document();wait(lambda:w.loaded_ok and not w.loader.isRunning())
        check(w.car_browser_tab_index==old_index+1 and w.workspace.currentWidget() is w.tabs,'file insertion moves reference index without activating it')
        w.reveal_car_browser();w.close_document(0)
        check(w.workspace.currentWidget() is w.car_browser and w.car_browser_tab_index>=0,'closing another file retains CAR reference')
        print('[CAR tabs 3/4] Recovery flags/category, legacy defaults and bilingual title',flush=True)
        w.car_browser.show_category('CAR Sensors');view=w.studio_view()
        check(view['page']=='car' and view['car_browser_open'] and view['car_browser_kind']=='CAR Sensors','session view identifies CAR separately')
        checkpoint=OUT/'session.json';write_session(session_payload(w.documents,w.active_document_index,view),checkpoint,lambda msg,*_:print(msg,flush=True))
        restored=read_session(ROOT/'data/attack',checkpoint,lambda msg,*_:print(msg,flush=True))
        w.close_car_browser();w.car_browser.kind='CAR Analytics'
        w.pending_session_view=restored['view'];w.finish_studio_startup()
        check(w.workspace.currentWidget() is w.car_browser and w.car_browser.kind=='CAR Sensors','session restores CAR tab and category')
        other=MainWindow(ROOT/'data/attack',settings_path=OUT/'restart.ini',session_path=checkpoint);other.show()
        wait(lambda:other.loaded_ok and other.car_browser_tab_index>=0 and other.workspace.currentWidget() is other.car_browser
             and other.car_browser.kind=='CAR Sensors' and other.pending_session_view is None)
        check(other.current_document.document_id==w.current_document.document_id,'fresh window automatically restores the CAR reference and owning document')
        with patch.object(other,'confirm_studio_changes',return_value='discard'):other.close()
        inactive=dict(view,page='selected');w.pending_session_view=inactive;w.finish_studio_startup()
        check(w.car_browser_tab_index>=0 and w.workspace.currentWidget() is w.tabs,'inactive open CAR reference restores without taking focus')
        legacy={k:v for k,v in inactive.items() if k not in ('car_browser_open','car_browser_kind')}
        w.pending_session_view=legacy;w.finish_studio_startup()
        check(w.car_browser_tab_index<0,'old sessions do not create a CAR tab')
        w.reveal_car_browser();manager=language_manager();manager.set_language('zh_TW');manager.refresh_all();app.processEvents()
        check(w.document_tabs.tabText(w.car_browser_tab_index)=='CAR 瀏覽器','CAR reference title localizes')
        manager.set_language('en');manager.refresh_all();w.grab().save(str(OUT/'car-reference.png'))
        print('[CAR tabs 4/4] Publish report',flush=True)
        (OUT/'audit.json').write_text(json.dumps({'passed':True,'count':len(checks),'checks':checks},indent=2)+'\n',encoding='utf-8')
        print(f'PASS: {len(checks)} CAR reference checks',flush=True)
    finally:
        with patch.object(w,'confirm_studio_changes',return_value='discard'):w.close()


if __name__=='__main__':main()
