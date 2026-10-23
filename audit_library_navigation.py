"""End-to-end sidebar versus Workplace contracts. Workflow: README.md."""
import json
from pathlib import Path
from unittest.mock import patch
from PySide6 import QtCore,QtTest,QtWidgets
from main import MainWindow,configure_application
from audit_export_options import wait
from navigation_scope import ATLAS_CATEGORIES,ATTACK_CATEGORIES,CAR_CATEGORIES
from atlas_cases import CASE_KEY

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/library-navigation'


def main():
    print('Input dataset root: '+str(ROOT/'data/attack'),flush=True)
    print('Input/output isolated settings: '+str(OUT/'settings.ini'),flush=True)
    print('Output report/previews: '+str(OUT),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    checks=[]
    def check(value,label):
        checks.append({'passed':bool(value),'label':label})
        print(('PASS: ' if value else 'FAIL: ')+label,flush=True)
    print('[Library navigation 1/4] Load real catalogs; verify scope layout',flush=True)
    w=MainWindow(ROOT/'data/attack',settings_path=OUT/'settings.ini',session_path=None);w.show()
    try:
        wait(lambda:w.loaded_ok and not w.loader.isRunning())
        doc=w.current_document;baseline=doc.content_token()
        for scope,excluded in [('attack',ATLAS_CATEGORIES|CAR_CATEGORIES),('atlas',ATTACK_CATEGORIES|CAR_CATEGORIES),('both',set())]:
            w.set_navigation_scope(scope);app.processEvents()
            check(all(w.navigation_buttons[k].isHidden() for k in excluded),'excluded icons hidden: '+scope)
            check(all(not w.navigation_rail.isAncestorOf(w.navigation_buttons[k]) for k in excluded),'excluded icons removed from rail: '+scope)
            check(all(w.navigation_buttons[k].isVisible() for k in set(w.navigation_buttons)-excluded),'allowed/shared icons restored: '+scope)
        print('[Library navigation 2/4] Mitigations open from Workplace without a prior choice',flush=True)
        w.switch_category('ATLAS TTP');w.atlas_search.setText('AML.T0000')
        w.close_details_page();w.switch_category('Workplace')
        page=w.workspace.currentWidget()
        w.navigation_buttons['ATLAS Mitigations'].click();app.processEvents()
        check(w.sidebar.isVisible() and w.workspace.currentWidget() is page and w.details_tab_index<0,'mitigation rail is sidebar-only')
        check(not w.atlas_search.text() and w.atlas_sidebar.topLevelItemCount()>0,'TTP query cannot mask the mitigation list')
        w.navigation_buttons['Workplace'].click()
        check(w.open_atlas_mitigation_button.isEnabled(),'mitigation Workplace opener is available without prior selection')
        w.open_atlas_mitigation_button.click();app.processEvents()
        check(w.workspace.currentWidget() is w.details_page and w.details_tab_index>=0,'Workplace opens mitigation details')
        check(w.sidebar.isVisible() and w.explorer_stack.currentWidget() is w.atlas_sidebar,'mitigation details retain mitigation list in sidebar')
        w.grab().save(str(OUT/'mitigation-details.png'))
        print('[Library navigation 3/4] CAR icon opens sidebar; rows and Workplace open full page',flush=True)
        w.switch_category('Workplace');page=w.workspace.currentWidget()
        for kind in ('CAR Analytics','CAR Data Model','CAR Sensors'):
            w.navigation_buttons[kind].click();app.processEvents()
            check(w.sidebar.isVisible() and w.explorer_stack.currentWidget() is w.car_sidebar,'CAR sidebar opens: '+kind)
            check(w.workspace.currentWidget() is page,'CAR rail retains current full page: '+kind)
        listing=getattr(w,'car_sidebar_list',None)
        check(listing is not None and listing.topLevelItemCount()>0,'CAR sidebar has actual entries')
        w.switch_category('CAR Analytics')
        w.grab().save(str(OUT/'car-sidebar.png'))
        if listing is not None and listing.topLevelItemCount():
            row=listing.topLevelItem(0);listing.setCurrentItem(row)
            QtTest.QTest.mouseClick(listing.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=listing.visualItemRect(row).center())
            check(w.workspace.currentWidget() is w.car_browser
                  and w.car_browser.stack.currentWidget() is w.car_browser.detail_page,
                  'CAR row click opens its full detail page')
        opener=getattr(w,'open_car_browser_button',None)
        check(opener is not None,'Workplace has a CAR full-page opener')
        if opener is not None:
            w.switch_category('Workplace');opener.click();app.processEvents()
            check(w.workspace.currentWidget() is w.car_browser,'Workplace opens full CAR page')
        print('[Library navigation 4/4] Case list belongs to sidebar; detail is independent',flush=True)
        w.open_atlas_cases();app.processEvents();case=w.atlas_cases_page
        check(w.workspace.currentWidget() is case,'case details remain an upper reference page')
        check(w.sidebar.isVisible() and w.sidebar.isAncestorOf(case.listing),'case results are in sidebar')
        check(not case.isAncestorOf(case.listing),'case results are outside the detail page')
        if case.listing.topLevelItemCount():
            row=case.listing.topLevelItem(0);case.listing.scrollToItem(row);app.processEvents()
            QtTest.QTest.mouseClick(case.listing.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=case.listing.visualItemRect(row).center())
            check(case.key==row.data(0,CASE_KEY),'sidebar case click populates case details')
        check(doc.content_token()==baseline,'all browsing retains document content')
        w.grab().save(str(OUT/'case-sidebar.png'))
        w.set_navigation_scope('attack');app.processEvents()
        check(all(not w.navigation_buttons[k].isVisible() for k in ATLAS_CATEGORIES),'scope remains enforced with a case page open')
        w.set_navigation_scope('both');w.switch_category('CAR Analytics')
        row=w.car_sidebar_list.topLevelItem(0);w.car_sidebar_list.setCurrentItem(row)
        w.switch_category('Workplace');w.open_car_browser_button.click()
        check(w.car_browser.stack.currentWidget() is w.car_browser.detail_page,'Workplace opens the chosen CAR analytic')
        w.new_document();wait(lambda:w.loaded_ok and not w.loader.isRunning())
        check(w.workspace.currentWidget() is w.tabs and w.pending_car_entry is None,'document switch cannot reopen cached CAR detail in the background')
        result={'passed':all(c['passed'] for c in checks),'checks':checks,'count':len(checks)}
        (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        assert result['passed'],'Library navigation contract failures: '+str([c['label'] for c in checks if not c['passed']])
        print(f'PASS: {len(checks)} library navigation checks',flush=True)
    finally:
        with patch.object(w,'confirm_studio_changes',return_value='discard'):w.close()


if __name__=='__main__':main()
