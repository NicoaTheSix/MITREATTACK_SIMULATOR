"""Real Qt mitigation sidebar opening and Workplace details. Flow: README.md."""
import json
from pathlib import Path
from unittest.mock import patch
from PySide6 import QtCore,QtTest,QtWidgets
from main import MainWindow,configure_application
from atlas_matrix import KEY
from attack_catalog import external_id
from atlas_catalog import DOMAIN
from audit_export_options import wait
from localization import language_manager

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/mitigation-navigation'


def main():
    print('Input dataset root: '+str(ROOT/'data/attack'),flush=True)
    print('Input/output isolated settings: '+str(OUT/'settings.ini'),flush=True)
    print('Output report/screenshots: '+str(OUT),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    checks=[]
    def check(value,label):
        assert value,label
        checks.append(label);print('[Check] '+label,flush=True)
    print('[Mitigation audit 1/4] Load and click actual sidebar navigation',flush=True)
    w=MainWindow(ROOT/'data/attack',settings_path=OUT/'settings.ini',session_path=None);w.show()
    try:
        wait(lambda:w.loaded_ok and not w.loader.isRunning())
        w.set_navigation_scope('both');doc=w.current_document;baseline=doc.content_token()
        w.close_details_page();w.show_document_page();page=w.workspace.currentWidget()
        w.navigation_buttons['ATLAS Mitigations'].click();app.processEvents()
        check(w.sidebar.isVisible() and w.explorer_stack.currentWidget() is w.atlas_sidebar,'navigation opens mitigation sidebar')
        check(w.details_tab_index<0 and w.workspace.currentWidget() is page,'navigation does not create or activate Details')
        check(w.open_atlas_mitigation_button.isEnabled(),'Workplace button can browse without a prior choice')
        node=w.atlas_sidebar.topLevelItem(0);key=node.data(0,KEY)
        obj=w.current_atlas_catalog.objects_by_domain[DOMAIN][key]
        w.atlas_sidebar.scrollToItem(node);app.processEvents()
        QtTest.QTest.mouseClick(w.atlas_sidebar.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=w.atlas_sidebar.visualItemRect(node).center())
        check(w.selected_atlas_mitigation()['id']==key and w.open_atlas_mitigation_button.isEnabled(),'single click selects a mitigation for Workplace')
        check(w.details_tab_index>=0 and w.workspace.currentWidget() is w.details_page
              and obj['name'] in w.details.toPlainText(),'item click opens matching mitigation Details')
        check(doc.content_token()==baseline,'navigation and choice do not edit the document')
        print('[Mitigation audit 2/4] Explicit Workplace action and retained details',flush=True)
        w.navigation_buttons['Workplace'].click();app.processEvents()
        check(w.open_atlas_mitigation_button.isVisible() and external_id(obj) in w.atlas_mitigation_choice.text(),'Workplace shows chosen mitigation and open button')
        w.open_atlas_mitigation_button.click();app.processEvents()
        check(w.workspace.currentWidget() is w.details_page and obj['name'] in w.details.toPlainText(),'Workplace button opens selected mitigation details')
        check(w.atlas_source_context[1]==key and w.object_copy_bar.isVisible(),'source actions and copy controls remain available')
        content=w.details.toHtml();title=w.document_tabs.tabText(w.details_tab_index)
        w.navigation_buttons['ATLAS Mitigations'].click();app.processEvents()
        check(w.details.toHtml()==content and w.document_tabs.tabText(w.details_tab_index)==title,'navigation preserves an existing reference page and title')
        w.atlas_sidebar.setFocus();QtTest.QTest.keyClick(w.atlas_sidebar,QtCore.Qt.Key.Key_Down);app.processEvents()
        next_obj=w.selected_atlas_mitigation()
        check(next_obj['id']!=key and w.details.toHtml()==content,'keyboard choice does not replace existing details')
        chosen=next_obj['id'];w.atlas_search.setText('no-matching-mitigation-123');app.processEvents()
        check(w.selected_atlas_mitigation()['id']==chosen and w.details.toHtml()==content,'filtering preserves choice and reference content')
        w.atlas_search.clear();w.navigation_buttons['Workplace'].click();w.open_atlas_mitigation_button.click()
        check(next_obj['name'] in w.details.toPlainText() and doc.content_token()==baseline,'Workplace opens latest choice without changing selections')
        print('[Mitigation audit 3/4] Bilingual presentation and document isolation',flush=True)
        manager=language_manager();manager.set_language('zh_TW');manager.refresh_all();app.processEvents()
        check('緩解措施' in w.open_atlas_mitigation_button.text() and external_id(next_obj) in w.atlas_mitigation_choice.text(),'button localizes while chosen ID remains literal')
        manager.set_language('en');manager.refresh_all()
        w.navigation_buttons['Workplace'].click();w.grab().save(str(OUT/'workplace-choice.png'))
        w.new_document();wait(lambda:w.loaded_ok and not w.loader.isRunning())
        check(w.pending_atlas_mitigation is None and w.open_atlas_mitigation_button.isEnabled(),'new document clears the previous choice and keeps browsing available')
        w.open_selected_atlas_mitigation()
        check(w.selected_atlas_mitigation()['id']!=chosen and w.pending_atlas_mitigation[0]==w.current_document.document_id,'fresh browse resolves against the new document')
        print('[Mitigation audit 4/4] Publish report',flush=True)
        (OUT/'audit.json').write_text(json.dumps({'passed':True,'count':len(checks),'checks':checks},indent=2)+'\n',encoding='utf-8')
        print(f'[Mitigation audit] PASS: {len(checks)} checks',flush=True)
    finally:
        with patch.object(w,'confirm_studio_changes',return_value='discard'):w.close()


if __name__=='__main__':main()
