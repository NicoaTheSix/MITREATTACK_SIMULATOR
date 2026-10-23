"""Verify independent, closable reference tabs beside document filenames. Flow: README.md."""
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

from PySide6 import QtCore, QtTest, QtWidgets
from attack_catalog import external_id, load_catalog
from attack_versions import snapshot_pointer
from main import MainWindow, configure_application, ROLE_CONTEXT
from navigator_integration import document_layer, imported_document

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "attack"
OUT = ROOT / "artifacts" / "workspace-layout" / "reference-regression"
REPORT = OUT / "workspace-audit.json"
PREVIEW = OUT / "independent-details-preview.png"
CLOSED = OUT / "closed-details-preview.png"
EXPORT = OUT / "workspace-ttps-example.json"
checks = []


def log(message, current=0, total=0):
    print(message + (f" ({current}/{total})" if total else ""), flush=True)


def check(condition, name):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def wait(condition, label):
    end = time.monotonic() + 60
    while not condition():
        if time.monotonic() > end:
            raise TimeoutError(label)
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def fingerprints(window):
    return [(document.document_id, document.fingerprint()) for document in window.documents]


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    log(f"Input file: {DATA / 'latest.json'}")
    for path in (REPORT, PREVIEW, CLOSED, EXPORT):
        log(f"Output file: {path}")
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(DATA, DATA / "latest.json",settings_path=OUT/'settings.ini',session_path=None)
    window.show()
    wait(lambda: window.loaded_ok and not window.loader.isRunning(), "startup")
    catalog = window.catalog
    log("[Workspace audit 1/5] Independent reference page and native close controls", 0, 5)
    first = window.current_document
    key = next(key for key, obj in catalog.records.items() if external_id(obj) == 'T1059.001')
    window.items_by_id[key][0].setCheckState(QtCore.Qt.CheckState.Checked)
    window.show_record(key)
    check(window.details_tab_index == len(window.documents), "reference tab sits beside filenames in the same tab bar")
    check(window.workspace.currentWidget() is window.details_page, "reference content is a separate workspace page")
    check(window.tabs.indexOf(window.details_page) == -1 and window.tabs.count() == 3
          and window.tabs.indexOf(window.atlas_matrix) >= 0 and window.workspace.indexOf(window.atlas_cases_page)>=0 and window.tabs.indexOf(window.atlas_cases_page)==-1,
          "document page contains selection, peer matrices and independent case studies")
    check(window.document_tabs.tabText(window.details_tab_index) == 'Technique Details', "reference tab uses Technique Details title")
    before = fingerprints(window)
    with patch.object(QtWidgets.QMessageBox, 'question') as question:
        button = window.document_tabs.tabButton(window.details_tab_index, QtWidgets.QTabBar.ButtonPosition.RightSide)
        QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        check(not question.called, "closing reference never asks to save a document")
    check(window.details_tab_index == -1 and window.document_tabs.count() == len(window.documents), "close button removes reference tab")
    check(window.workspace.currentWidget() is window.tabs and window.current_document is first, "close returns to the same file")
    check(fingerprints(window) == before and window.selected == {key}, "reference close preserves dirty state, IDs and selected TTPs")
    window.output_panel.hide()
    QtWidgets.QApplication.processEvents()
    check(window.grab().save(str(CLOSED)), "closed-page screenshot saved")
    window.details_action.trigger()
    check(window.details_tab_index >= 0 and window.workspace.currentWidget() is window.details_page, "View action reopens reference")
    check('PowerShell' in window.details.toPlainText() and fingerprints(window) == before, "reopen preserves last content and document data")
    window.open_details_page()
    window.open_details_page()
    check(window.document_tabs.count() == len(window.documents) + 1, "reopening reuses one reference tab")
    position = window.document_tabs.tabRect(window.details_tab_index).center()
    window.show_document_context_menu(position)
    menu = window.document_context_menu
    check([action.text() for action in menu.actions()] == ['Close Details'], "reference context menu has close without filename/domain actions")
    menu.actions()[0].trigger()
    menu.close()
    check(window.details_tab_index == -1 and fingerprints(window) == before, "reference right-click close preserves file state")
    item = window.items_by_id[key][0]
    index = window.proxy.mapFromSource(item.index())
    parent = index.parent()
    while parent.isValid():
        window.tree.expand(parent)
        parent = parent.parent()
    window.tree.setCurrentIndex(index)
    window.close_details_page()
    window.tree.scrollTo(index)
    QtWidgets.QApplication.processEvents()
    rect = window.tree.visualRect(index)
    QtTest.QTest.mouseClick(window.tree.viewport(), QtCore.Qt.MouseButton.LeftButton,
                           pos=QtCore.QPoint(rect.left() + 100, rect.center().y()))
    check(window.details_tab_index >= 0 and 'PowerShell' in window.details.toPlainText(), "clicking the same selected TTP reopens closed reference")
    log("[Workspace audit 2/5] File activation, insertion, rename and closure", 1, 5)
    window.document_tabs.setCurrentIndex(0)
    check(window.workspace.currentWidget() is window.tabs and window.current_document is first, "clicking already-active filename switches away from reference")
    window.new_action.trigger()
    wait(lambda: window.loaded_ok, "second file")
    second = window.current_document
    check(window.workspace.currentWidget() is window.tabs and window.document_tabs.currentIndex() == 1, "Ctrl+N/New activates a file page")
    check(window.details_tab_index == 2 and first.selected == {key} and not second.selected, "new filename inserted before reference without corrupting selections")
    window.show_record(key)
    check(window.current_document is second and window.active_document_index == 1, "reference browsing retains active file")
    with patch.object(QtWidgets.QInputDialog, 'getText', return_value=('Research-A', True)):
        window.rename_document(0)
    check(window.document_tabs.tabText(0).startswith('Research-A') and window.details_tab_index == 2, "inactive rename targets file without overwriting reference label")
    window.close_details_page()
    third_count = len(window.documents)
    window.new_document()
    wait(lambda: window.loaded_ok, "new while reference closed")
    check(len(window.documents) == third_count + 1 and window.details_tab_index == -1, "new file does not reopen closed reference")
    check(window.document_tabs.count() == len(window.documents), "files work with no reference tab")
    check(window.close_document(2), "empty active file closes while reference absent")
    window.show_record(key)
    before = fingerprints(window)
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Cancel):
        check(not window.close_document(0), "cancel closing dirty filename from reference context")
    check(fingerprints(window) == before and window.workspace.currentWidget() is window.details_page, "cancel file close leaves reference and documents intact")
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Discard):
        check(window.close_document(0), "close inactive dirty file with discard")
    check(window.current_document is second and window.active_document_index == 0, "removing earlier file fixes active file index")
    check(window.details_tab_index == 1 and window.document_tabs.currentIndex() == 1 and window.workspace.currentWidget() is window.details_page, "reference selection survives an inactive filename removal")
    window.new_document()
    wait(lambda: window.loaded_ok, "new before import")
    imported = imported_document(document_layer(second), catalog)
    window.install_imported_document(imported)
    wait(lambda: window.loaded_ok, "import file")
    check(window.current_document is imported and window.document_tabs.tabData(window.active_document_index) == imported.document_id, "imported file uses stable identity before reference tab")
    check(window.workspace.currentWidget() is window.tabs and window.details_tab_index == len(window.documents), "import opens file page and preserves reference position")
    log("[Workspace audit 3/5] Closed state across domain/version reloads", 2, 5)
    window.close_details_page()
    window.change_document_domain(window.active_document_index, 'mobile-attack')
    wait(lambda: window.loaded_ok, "Mobile reload")
    check(window.details_tab_index == -1 and window.workspace.currentWidget() is window.tabs, "domain reload does not reopen closed reference")
    mobile = window.catalog
    old = load_catalog(DATA, log, snapshot_pointer(DATA, '1.0')).for_domain('mobile-attack')
    window.apply_version((old, None))
    wait(lambda: window.loaded_ok, "historical Mobile reload")
    check(window.details_tab_index == -1 and window.catalog.domain == 'mobile-attack', "version reload preserves closed reference state")
    window.apply_version((mobile, None))
    wait(lambda: window.loaded_ok, "modern Mobile")
    mobile_key = next(iter(window.catalog.records))
    window.show_record(mobile_key)
    check(window.details_tab_index >= 0 and window.catalog.domain == 'mobile-attack', "Mobile technique opens independent reference")
    window.change_document_domain(window.active_document_index, 'ics-attack')
    wait(lambda: window.loaded_ok, "ICS reload with reference visible")
    check(window.workspace.currentWidget() is window.details_page and window.document_tabs.currentIndex() == window.details_tab_index, "visible reference survives domain rebuild")
    check('ICS' in window.crumb.text() and window.current_document.catalog.domain == 'ics-attack', "rebuilt reference uses active ICS source")
    log("[Workspace audit 4/5] Matrix and library links reopen the independent page", 3, 5)
    window.close_details_page()
    window.open_matrix()
    wait(lambda: not window.matrix_view.building, "ICS matrix")
    check(window.workspace.currentWidget() is window.tabs and window.tabs.currentIndex() == window.matrix_tab_index, "matrix belongs to active filename page")
    key = next(iter(window.matrix_view.items_by_id))
    item = window.matrix_view.items_by_id[key][0]
    window.show_matrix_detail(key, item.data(0, int(QtCore.Qt.ItemDataRole.UserRole) + 2))
    check(window.workspace.currentWidget() is window.details_page and external_id(window.catalog.records[key]) in window.details.toPlainText(), "matrix technique activation reopens reference")
    window.close_details_page()
    window.switch_category('Software')
    item = next(item for item in window.library_items['Software'] if item.data(ROLE_CONTEXT)[0] == 'ics-attack')
    window.show_library_index(window.library_proxy.mapFromSource(item.index()))
    check(window.workspace.currentWidget() is window.details_page and window.document_tabs.tabText(window.details_tab_index) == 'Software Details', "library data opens same independent reference page")
    source_domain, source_key = window.bulk_source_context
    check(source_domain == 'ics-attack' and window.bulk_add_button.isEnabled(), "bulk action remains bound to active ICS file")
    window.add_current_source_ttps()
    check(window.current_document is imported and imported.selected == window.selected, "reference bulk add updates active file")
    target = window.catalog.techniques_by_source[source_domain][source_key][0]['target_ref']
    window.open_detail_link(QtCore.QUrl(f'technique:{source_domain}/{target}'))
    check(window.document_tabs.tabText(window.details_tab_index) == 'Technique Details' and window.workspace.currentWidget() is window.details_page, "library technique link updates reference title/content")
    window.details.copy_title_button.click()
    check(app.clipboard().text() == window.catalog.records[target]['name'], "title copy works in independent reference")
    log("[Workspace audit 5/5] Export and screenshot verification", 4, 5)
    current = window.current_document
    selected = set(window.selected)
    path = window.export_current_document(EXPORT)
    log(f'Input file: {path}')
    payload = json.loads(path.read_text(encoding='utf-8'))
    check(payload['document_id'] == current.document_id and payload['attack']['domain'] == 'ics-attack', "Export from reference uses active file identity/domain")
    check(payload['selected_count'] == len(selected) and 'Technique Details' not in payload['name'], "reference tab never becomes an exported document")
    window.close_details_page()
    window.open_details_page()
    window.show_record(target)
    QtWidgets.QApplication.processEvents()
    check(window.grab().save(str(PREVIEW)), "independent-details screenshot saved")
    while len(window.documents) > 1:
        index = next(index for index, document in enumerate(window.documents) if document is not current)
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Discard):
            window.close_document(index)
    check(window.close_document(0), "last exported file closes without treating reference as a file")
    wait(lambda: window.loaded_ok, "replacement file")
    check(len(window.documents) == 1 and not window.selected and window.current_document.catalog.domain == 'enterprise-attack', "closing last file creates default Enterprise replacement")
    check(window.details_tab_index == 1 and window.workspace.currentWidget() is window.tabs, "last-file replacement retains independent reference tab")
    window.close()
    log(f'Output file: {REPORT}')
    REPORT.write_text(json.dumps({'status': 'PASS', 'checks': checks, 'preview': str(PREVIEW), 'closed_preview': str(CLOSED)}, indent=2) + '\n', encoding='utf-8')
    log(f'[Workspace audit] PASS: {len(checks)} checks', 5, 5)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
