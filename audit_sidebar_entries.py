"""Real Qt sidebar row opening regression. Workflow: README.md."""
import json
from pathlib import Path
from unittest.mock import patch

from PySide6 import QtCore, QtTest, QtWidgets
from main import MainWindow, configure_application
from atlas_matrix import KEY
from atlas_catalog import DOMAIN
from car_views import REF
from audit_export_options import wait

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts' / 'sidebar-entries'


def main():
    for path in ('attack', 'atlas', 'car'):
        print('Input dataset root: ' + str(ROOT / 'data' / path), flush=True)
    print('Input/output isolated settings: ' + str(OUT / 'settings.ini'), flush=True)
    print('Output report/previews: ' + str(OUT), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    checks = []

    def check(value, label):
        checks.append({'passed': bool(value), 'label': label})
        print(('PASS: ' if value else 'FAIL: ') + label, flush=True)

    print('[Sidebar entries 1/3] Load actual catalogs with recovery disabled', flush=True)
    w = MainWindow(ROOT / 'data/attack', settings_path=OUT / 'settings.ini', session_path=None)
    w.show()
    try:
        wait(lambda: w.loaded_ok and not w.loader.isRunning() and w.car_catalog is not None
             and w.current_atlas_catalog is not None)
        w.set_navigation_scope('both')
        doc = w.current_document
        baseline = doc.content_token()
        print('[Sidebar entries 2/3] Click actual sidebar rows and activate with Enter', flush=True)
        for kind in ('ATLAS Mitigations', 'CAR Analytics', 'CAR Data Model', 'CAR Sensors'):
            w.show_document_page()
            page = w.workspace.currentWidget()
            w.navigation_buttons[kind].click()
            app.processEvents()
            check(w.workspace.currentWidget() is page, kind + ': rail only opens sidebar')
            listing = w.atlas_sidebar if kind == 'ATLAS Mitigations' else w.car_sidebar_list
            check(listing.topLevelItemCount() >= 2, kind + ': real records available')
            for row in (0, 1):
                item = listing.topLevelItem(row)
                listing.scrollToItem(item)
                app.processEvents()
                QtTest.QTest.mouseClick(listing.viewport(), QtCore.Qt.MouseButton.LeftButton,
                                       pos=listing.visualItemRect(item).center())
                app.processEvents()
                verify_record(w, kind, item, check, 'click')
            w.show_document_page()
            listing.setFocus()
            QtTest.QTest.keyClick(listing, QtCore.Qt.Key.Key_Return)
            app.processEvents()
            verify_record(w, kind, listing.currentItem(), check, 'Enter')
            w.show_document_page()
            item = listing.currentItem()
            QtTest.QTest.mouseClick(listing.viewport(), QtCore.Qt.MouseButton.LeftButton,
                                   pos=listing.visualItemRect(item).center())
            app.processEvents()
            verify_record(w, kind, item, check, 'repeated click')
            check(doc.content_token() == baseline, kind + ': browsing preserves document')
            w.grab().save(str(OUT / (kind.lower().replace(' ', '-') + '.png')))
        print('[Sidebar entries 3/3] Publish regression report', flush=True)
        result = {'passed': all(c['passed'] for c in checks), 'checks': checks}
        (OUT / 'audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        assert result['passed'], 'Sidebar row opening failed; see ' + str(OUT / 'audit.json')
        print(f'PASS: {len(checks)} sidebar entry checks', flush=True)
    finally:
        with patch.object(w, 'confirm_studio_changes', return_value='discard'):
            w.close()


def verify_record(w, kind, item, check, trigger):
    if kind == 'ATLAS Mitigations':
        obj = w.current_atlas_catalog.objects_by_domain[DOMAIN][item.data(0, KEY)]
        opened = (w.workspace.currentWidget() is w.details_page
                  and obj['name'] in w.details.toPlainText()
                  and w.atlas_source_context[1] == obj['id'])
    else:
        reference = item.data(0, REF)
        route, key = reference[4:].split('/', 1)
        expected = (w.car_catalog.analytics[key]['id'] if route == 'analytic' else key
                    if route == 'model' else w.car_catalog.sensors[key]['sensor_name'])
        opened = (w.workspace.currentWidget() is w.car_browser
                  and w.car_browser_tab_index >= 0
                  and w.car_browser.stack.currentWidget() is w.car_browser.detail_page
                  and w.car_browser.kind == kind
                  and expected in w.car_browser.details.toPlainText())
    check(opened, kind + ': ' + trigger + ' opens ' + item.text(0))


if __name__ == '__main__':
    main()
