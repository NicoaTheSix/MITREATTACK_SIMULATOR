"""Eight independent sidebar combinations, real menus and recovery of preferences. Flow: README.md."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
from unittest.mock import patch
from PySide6 import QtCore,QtTest,QtWidgets
from main import CatalogLoader,MainWindow,configure_application
from navigation_scope import FAMILIES,FAMILY_CATEGORIES

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/sidebar-groups'


def main(loaded=False,hidden=False):
    print('Input catalog: '+(str(ROOT/'data/attack') if loaded else 'None (catalog worker paused)'),flush=True)
    print('Input/output isolated settings: '+str(OUT/'settings.ini'),flush=True)
    print('Output report/previews: '+str(OUT),flush=True)
    OUT.mkdir(parents=True,exist_ok=True)
    settings=OUT/'settings.ini';settings.unlink(missing_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);configure_application(app)
    checks=[]
    def check(ok,label):
        assert ok,label
        checks.append(label);print('[Check] '+label,flush=True)
    def show(w):
        if hidden:w.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen,True)
        w.show();app.processEvents()
    def close(w):
        with patch.object(w,'finish_studio_exit',return_value=True):w.close()
    print('[Sidebar groups 1/4] Fresh defaults and independent menu',flush=True)
    with (nullcontext() if loaded else patch.object(CatalogLoader,'start',return_value=None)):
        w=MainWindow(ROOT/'data/attack',settings_path=settings,session_path=None)
    show(w)
    try:
        if loaded:
            from audit_export_options import wait
            wait(lambda:w.loaded_ok and not w.loader.isRunning())
        baseline=w.current_document.content_token() if loaded else None
        check(all(w.navigation_families.values()),'all three groups enabled by default')
        check([a.text().replace('&&','&') for a in w.navigation_family_actions.values()]==list(FAMILIES.values()),'menu has ATT&CK, ATLAS and CAR switches')
        check(all(a.isCheckable() and a.actionGroup() is None for a in w.navigation_family_actions.values()),'switches are independent, not exclusive')
        if loaded:
            for family,category in [('attack','TTP'),('atlas','ATLAS TTP'),('car','CAR Analytics')]:
                w.set_navigation_families(set(FAMILIES));w.switch_category(category)
                page=w.workspace.currentWidget()
                w.navigation_family_actions[family].trigger()
                check(w.active_category=='Workplace' and w.explorer_stack.currentWidget() is w.workplace_tree,'disabling active family returns explorer to Workplace: '+family)
                check(w.workspace.currentWidget() is page,'disabling active family retains right page: '+family)
            w.set_navigation_families(set(FAMILIES))
        print('[Sidebar groups 2/4] Real menu clicks for all eight combinations and both label layouts',flush=True)
        for labels in (True,False):
            w.set_navigation_labels_visible(labels)
            for mask in range(8):
                expected={key:bool(mask&(1<<i)) for i,key in enumerate(FAMILIES)}
                for family,enabled in expected.items():
                    action=w.navigation_family_actions[family]
                    if action.isChecked()!=enabled:
                        menu=action.parent()
                        if hidden:menu.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen,True)
                        menu.popup(w.mapToGlobal(QtCore.QPoint(100,50)));QtTest.QTest.qWait(10)
                        QtTest.QTest.mouseClick(menu,QtCore.Qt.MouseButton.LeftButton,pos=menu.actionGeometry(action).center())
                        app.processEvents()
                suffix=str((labels,mask))
                check(w.navigation_families==expected,'exact independent switches '+suffix)
                for family,categories in FAMILY_CATEGORIES.items():
                    check(all(w.navigation_buttons[k].isVisible()==expected[family] for k in categories),'actual icon visibility '+family+' '+suffix)
                    if not expected[family]:
                        for k in categories:w.navigation_buttons[k].show()
                        app.processEvents()
                        check(all(not w.navigation_buttons[k].isVisible() and not w.navigation_rail.isAncestorOf(w.navigation_buttons[k]) for k in categories),'excluded family cannot reappear '+family+' '+suffix)
                check(w.navigation_buttons['Workplace'].isVisible(),'Workplace survives all-off '+suffix)
                actual=[w.navigation_rail.layout().itemAt(i).widget() for i in range(w.navigation_rail.layout().count())]
                actual=[obj for obj in actual if obj in w.navigation_buttons.values()]
                check(actual==[b for k,b in w.navigation_buttons.items() if w.navigation_category_visible(k)],'canonical rail order '+suffix)
                with patch.object(CatalogLoader,'start',return_value=None):
                    other=MainWindow(ROOT/'data/attack',settings_path=settings,session_path=None)
                show(other)
                check(other.navigation_families==expected,'restart preserves exact combination '+suffix)
                close(other)
                if labels and mask in (0,1,2,4,7):
                    menu=next(iter(w.navigation_family_actions.values())).parent()
                    if hidden:menu.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen,True)
                    menu.popup(w.mapToGlobal(QtCore.QPoint(100,50)));QtTest.QTest.qWait(10)
                    w.grab().save(str(OUT/f'groups-{mask}.png'))
                    menu.grab().save(str(OUT/f'groups-{mask}-menu.png'));menu.close()
        if loaded:check(w.current_document.content_token()==baseline,'group changes preserve document selections and annotations')
        print('[Sidebar groups 3/4] Old settings migration, invalid data and empty groups',flush=True)
        fixtures=[('both',None,set(FAMILIES)),('attack',None,{'attack'}),('atlas',None,{'atlas'}),
                  ('unknown',None,set(FAMILIES)),(None,'bad-json',set(FAMILIES)),(None,'[]',set()),
                  (None,'["car"]',{'car'}),(None,'["unknown"]',set(FAMILIES))]
        for i,(legacy,raw,expected) in enumerate(fixtures):
            path=OUT/f'legacy-{i}.ini';print('Input/output migration fixture: '+str(path),flush=True)
            path.unlink(missing_ok=True)
            config=QtCore.QSettings(str(path),QtCore.QSettings.Format.IniFormat)
            if legacy is not None:config.setValue('navigation/frameworks',legacy)
            if raw is not None:config.setValue('navigation/families',raw)
            config.sync()
            with patch.object(CatalogLoader,'start',return_value=None):
                other=MainWindow(ROOT/'data/attack',settings_path=path,session_path=None)
            check({f for f,v in other.navigation_families.items() if v}==expected,'migration/validation '+str(i))
            close(other)
        print('[Sidebar groups 4/4] Publish report',flush=True)
        report=OUT/('audit-loaded.json' if loaded else 'audit.json')
        report.write_text(json.dumps({'passed':True,'count':len(checks),'platform':app.platformName(),'checks':checks},indent=2)+'\n',encoding='utf-8')
        print(f'PASS: {len(checks)} sidebar group checks ({app.platformName()})',flush=True)
    finally:close(w)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--loaded',action='store_true');parser.add_argument('--native-hidden',action='store_true')
    args=parser.parse_args();main(args.loaded,args.native_hidden)
