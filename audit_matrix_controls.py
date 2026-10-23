"""Real Qt controls geometry and reference-tab lifecycle. Workflow: README.md."""
import json
from pathlib import Path
from unittest.mock import patch

from PySide6 import QtCore, QtTest, QtWidgets
from main import MainWindow, CatalogLoader, configure_application
from localization import language_manager

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts/matrix-controls'


def main():
    print('Input files: None (catalog loading paused; actual Qt widgets)', flush=True)
    print('Input/output settings: ' + str(OUT / 'settings.ini'), flush=True)
    print('Output screenshots/report: ' + str(OUT), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    protected = {p: p.read_bytes() for p in (ROOT/'data/ui-settings.ini', ROOT/'data/workspace-session.json') if p.exists()}
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    configure_application(app)
    checks = []

    def check(ok, label):
        assert ok, label
        checks.append(label)
        print('[Check] ' + label, flush=True)

    print('[Controls audit 1/3] Geometry, real toggles and input preservation', flush=True)
    with patch.object(CatalogLoader, 'start', return_value=None):
        w = MainWindow(ROOT/'data/attack', settings_path=OUT/'settings.ini', session_path=None)
    w.resize(1440, 920)
    w.show()
    w.tabs.setTabEnabled(w.matrix_tab_index, True)
    w.workspace.setCurrentWidget(w.tabs)
    w.tabs.setCurrentIndex(w.matrix_tab_index)
    m = w.matrix_view
    m.search.setText('saved search')
    m.source_picker.setEditText('saved source')
    for size in ((1440, 920), (1000, 650)):
        w.resize(*size)
        m.set_controls_expanded(True)
        QtTest.QTest.qWait(30)
        height = m.scroll.viewport().height()
        check(m.controls_toggle.isVisible() and m.controls_panel.isVisible(), 'expanded controls available ' + str(size))
        QtTest.QTest.mouseClick(m.controls_toggle, QtCore.Qt.MouseButton.LeftButton)
        QtTest.QTest.qWait(30)
        check(m.scroll.viewport().height() > height + 150, 'collapse reclaims matrix height ' + str(size))
        check(m.summary.isVisible() and m.controls_toggle.isVisible(), 'summary and reopen control remain visible ' + str(size))
        check(all(not obj.isVisible() for obj in (m.layer_selector, m.search, m.source_picker, m.batch_edit_button,
              w.matrix_source_fields_button)), 'all control rows, including injected search preferences, collapse ' + str(size))
        check(m.search.text() == 'saved search' and m.source_picker.currentText() == 'saved source', 'queries retained ' + str(size))
        w.grab().save(str(OUT/f'collapsed-{size[0]}.png'))
        QtTest.QTest.mouseClick(m.controls_toggle, QtCore.Qt.MouseButton.LeftButton)
        QtTest.QTest.qWait(20)
        check(m.controls_panel.isVisible() and m.search.text() == 'saved search', 'reopen preserves controls ' + str(size))
    print('[Controls audit 2/3] Independent upper reference tabs and dynamic indices', flush=True)
    details = w.ensure_details_tab()
    case = w.ensure_atlas_cases_tab()
    check(w.document_tabs.tabData(details) == '__details__' and w.document_tabs.tabData(case) == '__atlas_cases__', 'reference tabs have separate stable identities')
    check(w.workspace.indexOf(w.atlas_cases_page) >= 0 and w.tabs.indexOf(w.atlas_cases_page) == -1, 'case page is at the same stack level as technique details')
    count = w.document_tabs.count()
    w.ensure_atlas_cases_tab()
    check(w.document_tabs.count() == count, 'repeated ensure does not duplicate case tab')
    with QtCore.QSignalBlocker(w.document_tabs):
        w.document_tabs.insertTab(0, 'Temporary document')
    check(w.atlas_cases_tab_index == case + 1, 'reference index follows file insertion')
    w.workspace.setCurrentWidget(w.details_page)
    w.document_tabs.setEnabled(True)
    w.document_tabs.setTabEnabled(w.atlas_cases_tab_index, True)
    with QtCore.QSignalBlocker(w.document_tabs):
        w.document_tabs.setCurrentIndex(w.details_tab_index)
    close = w.document_tabs.tabButton(w.atlas_cases_tab_index, QtWidgets.QTabBar.ButtonPosition.RightSide)
    QtTest.QTest.mouseClick(close, QtCore.Qt.MouseButton.LeftButton)
    check(w.atlas_cases_tab_index == -1 and w.workspace.currentWidget() is w.details_page, 'closing inactive case reference preserves active technique details')
    w.ensure_atlas_cases_tab()
    w.workspace.setCurrentWidget(w.atlas_cases_page)
    w.close_details_page()
    check(w.workspace.currentWidget() is w.atlas_cases_page and w.atlas_cases_tab_index >= 0, 'closing inactive technique reference preserves case page')
    w.close_atlas_cases()
    check(w.workspace.currentWidget() is w.tabs, 'closing active case returns to document area')
    print('[Controls audit 3/3] Bilingual state and read-only preservation', flush=True)
    m.set_controls_expanded(False)
    manager = language_manager()
    manager.set_language('zh_TW'); manager.refresh_all(); app.processEvents()
    check(m.controls_toggle.text() == '矩陣控制區' and not m.controls_toggle.isChecked(), 'Traditional Chinese label retains collapsed state')
    manager.set_language('en'); manager.refresh_all(); app.processEvents()
    check(m.controls_toggle.text() == 'Matrix controls' and not m.controls_panel.isVisible(), 'English switch retains collapsed state')
    check(all(p.read_bytes() == raw for p, raw in protected.items()), 'production settings and session preserved')
    with patch.object(w, 'finish_studio_exit', return_value=True):
        w.close()
    (OUT/'audit.json').write_text(json.dumps({'passed': True, 'count': len(checks), 'checks': checks}, indent=2)+'\n', encoding='utf-8')
    print(f'[Controls audit] PASS: {len(checks)} checks', flush=True)


if __name__ == '__main__':
    main()
