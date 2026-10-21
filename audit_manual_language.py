"""Exercise every actual manual link and language/state isolation. Flow: README.md."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import time
import uuid
from unittest.mock import patch

from PySide6 import QtCore, QtGui, QtTest, QtWidgets
from main import MainWindow, configure_application
from localization import language, tr
from manual_page import manual_home, MANUAL_TAB
from navigator_integration import export_layer, update_annotation
from attack_versions import cached_discovery

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'artifacts' / 'manual-language'


def report(message, *_):
    print(message, flush=True)


def wait(predicate, title, seconds=60):
    deadline = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError('Timed out: ' + title)
        QtTest.QTest.qWait(20)


def fingerprint(window):
    return [(doc.document_id, doc.name, doc.content_token(), doc.dirty,
             str(doc.save_path), doc.saved_fingerprint, doc.saved_file_sha256)
            for doc in window.documents], window.current_document.document_id


def click_feature(page, feature):
    text = page.current_path.read_text(encoding='utf-8')
    label = re.search(r'\[([^]]+)\]\(studio://' + re.escape(feature) + r'\)', text).group(1)
    cursor = page.browser.document().find(label)
    assert not cursor.isNull(), 'Missing rendered link: ' + feature
    cursor.setPosition(cursor.selectionStart() + 1)
    page.browser.setTextCursor(cursor)
    page.browser.ensureCursorVisible()
    QtTest.QTest.qWait(30)
    point = page.browser.cursorRect(cursor).center() + QtCore.QPoint(2, 0)
    assert page.browser.anchorAt(point) == 'studio://' + feature, (feature, page.browser.anchorAt(point))
    QtTest.QTest.mouseClick(page.browser.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=point)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run = OUT / ('run-' + uuid.uuid4().hex)
    run.mkdir()
    settings = run / 'settings.ini'
    fixture = run / 'source.navigator.json'
    for path in (ROOT / 'data/attack/active.json', ROOT / 'locales/zh_TW.json', manual_home()):
        report('Input file: ' + str(path))
    for path in (settings, fixture, OUT / 'audit.json', OUT / 'untranslated.json', OUT / 'manual-en.png', OUT / 'manual-zh-TW.png'):
        report('Output file: ' + str(path))
    report('[Manual/language audit 1/6] Starting isolated workspace')
    pointers = {name: (ROOT / 'data/attack' / name).read_bytes() for name in ('active.json', 'latest.json')}
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(ROOT / 'data/attack', settings_path=settings, session_path=None)
    window.confirm_studio_changes = lambda *args: 'discard'
    window.show()
    wait(lambda: window.loaded_ok, 'initial v20 catalog')
    assert language() == 'en', 'A fresh preference must default to English'
    window.new_document()
    window.current_document.name = 'Manual'
    key = next(iter(window.catalog.records))
    window.choose_technique_occurrence(key, True)
    update_annotation(window.current_document, key, None, 'User note: Save / Name / 中文', 17, '#123456')
    window.refresh_selection()
    export_layer(window.current_document, fixture, report)
    window.current_document.name = 'Manual'
    window.update_document_labels()
    baseline = fingerprint(window)
    assert window.current_document.dirty
    results = []
    missing = set()

    def collect_ui(dialog):
        window.language_manager.refresh_all()
        for widget in [dialog, *dialog.findChildren(QtWidgets.QWidget)]:
            objects = [widget, *widget.actions()]
            for obj in objects:
                for key, pair in (obj.property('_studioLocaleSources') or {}).items():
                    source = pair[0]
                    if (source == tr(source) and re.search(r'[A-Za-z]{3}', source)
                            and not re.search(r'[\u3400-\u9fff]', source)
                            and source not in ('English', 'Navigator', 'TTP', 'Fusion Studio', 'A community toolkit for MITRE ATT&CK® and ATLAS', 'ATT&CK ID', 'ATTCK ID')
                            and not re.search(r'https?://|[A-Z]:[\\/]|^#|^TA?\d|^G\d|^S\d|^ATT&&?CK v\d|Fusion Studio$|^a\+b', source)):
                        missing.add(source)

    expected = {
        'open-file': 'file-picker', 'batch-edit': 'BatchEditDialog',
        'matrix': 'matrix', 'search': 'search', 'selected': 'selection',
        'versions': 'VersionDialog', 'layer-settings': 'LayerSettingsDialog',
        'formula': 'FormulaDialog', 'compare': 'SelectionCompareDialog',
        'compare-versions': 'VersionCompareDialog', 'import-layer': 'ImportLayerDialog',
        'sources': 'SourceDialog', 'upgrade': 'UpgradeDialog',
        'export-svg': 'MatrixExportDialog', 'export-excel': 'MatrixExportDialog',
    }
    pickers = []
    original_open = QtWidgets.QFileDialog.getOpenFileName
    original_save = QtWidgets.QFileDialog.getSaveFileName

    def open_file(parent, title, *args, **kwargs):
        pickers.append(title)
        arguments = list(args)
        arguments[0] = str(run)
        return original_open(parent, title, *arguments, **kwargs)

    def save_file(parent, title, *args, **kwargs):
        pickers.append(title)
        arguments = list(args)
        arguments[0] = str(run)
        return original_save(parent, title, *arguments, **kwargs)

    report('[Manual/language audit 2/6] Clicking every feature in English and zh_TW')
    with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', open_file), \
            patch.object(QtWidgets.QFileDialog, 'getSaveFileName', save_file), \
            patch('version_dialog.discover_versions', cached_discovery):
        for selected in ('en', 'zh_TW'):
            assert window.change_language(selected)
            QtTest.QTest.qWait(100)
            window.open_manual()
            page = window.manual_page
            assert page.current_path == manual_home()
            assert ('資訊' if selected == 'zh_TW' else 'Info') == window.info_menu.title()
            assert fingerprint(window) == baseline
            for number, (feature, target) in enumerate(expected.items(), 1):
                report(f'[Manual/language audit 2/6] {selected} {feature} ({number}/{len(expected)})')
                window.open_manual()
                window.activateWindow()
                page.load_page(manual_home())
                existing_pickers = len(pickers)
                captured = []
                capture_errors = []
                timer = QtCore.QTimer()

                def inspect_dialogs():
                    try:
                        for dialog in app.topLevelWidgets():
                            if not isinstance(dialog, QtWidgets.QDialog) or not dialog.isVisible():
                                continue
                            worker = getattr(dialog, 'worker', None)
                            if worker is not None and worker.isRunning():
                                continue
                            if selected == 'zh_TW':
                                collect_ui(dialog)
                            if isinstance(dialog, QtWidgets.QFileDialog):
                                captured.append('file-picker')
                                if feature == 'open-file':
                                    dialog.reject()
                                else:
                                    path = fixture if feature == 'import-layer' else run / ('preview.svg' if feature == 'export-svg' else 'preview.xlsx')
                                    dialog.selectFile(str(path))
                                    dialog.accept()
                                continue
                            if feature == 'import-layer' and type(dialog).__name__ == 'ImportLayerDialog' and not dialog.layers:
                                # The zero-delay worker start/completion may still be queued.
                                continue
                            captured.append(type(dialog).__name__)
                            if feature == 'layer-settings':
                                dialog.grab().save(str(OUT / ('layer-settings-' + selected + '.png')))
                            if feature == 'import-layer':
                                assert dialog.layers, 'The chosen fixture did not reach the real import dialog'
                            if feature.startswith('export-'):
                                assert dialog.kind == ('svg' if feature == 'export-svg' else 'xlsx')
                            dialog.reject()
                    except Exception as error:
                        capture_errors.append(str(error))
                        for dialog in app.topLevelWidgets():
                            if isinstance(dialog, QtWidgets.QDialog) and dialog.isVisible():
                                dialog.reject()

                timer.timeout.connect(inspect_dialogs)
                timer.start(80)
                click_feature(page, feature)
                if target not in ('matrix', 'search', 'selection', 'file-picker'):
                    wait(lambda: target in captured or capture_errors, 'dialog for ' + feature, seconds=20)
                else:
                    QtTest.QTest.qWait(100)
                timer.stop()
                assert not capture_errors, (feature, capture_errors)
                if target == 'file-picker':
                    assert len(pickers) > existing_pickers and 'Studio' in pickers[-1]
                    assert 'file-picker' in captured, 'Real Qt file picker did not open'
                elif target == 'matrix':
                    assert window.workspace.currentWidget() is window.tabs and window.tabs.currentIndex() == window.matrix_tab_index
                elif target == 'selection':
                    assert window.workspace.currentWidget() is window.tabs and window.tabs.currentIndex() == window.selection_tab_index
                elif target == 'search':
                    assert window.active_category == 'TTP' and window.ttp_search.isVisible() and window.focusWidget() is window.ttp_search
                else:
                    assert target in captured, (feature, target, captured)
                assert fingerprint(window) == baseline, 'Document changed after ' + feature
                results.append({'language': selected, 'feature': feature, 'target': target, 'status': 'PASS'})
            window.open_manual()
            page.load_page(manual_home())
            window.language_manager.refresh_all()
            QtTest.QTest.qWait(60)
            window.grab().save(str(OUT / ('manual-zh-TW.png' if selected == 'zh_TW' else 'manual-en.png')))
            if selected == 'zh_TW':
                collect_ui(window)

    report('[Manual/language audit 3/6] Repeated manual switching, closing and reopening')
    for _ in range(3):
        window.open_manual()
        count = window.document_tabs.count()
        window.open_manual()
        assert window.document_tabs.count() == count
        window.document_tabs.setCurrentIndex(window.active_document_index)
        window.open_manual()
        window.close_manual()
        assert window.manual_tab_index == -1
        assert fingerprint(window) == baseline
    window.open_manual()
    assert window.document_tabs.tabData(window.manual_tab_index) == MANUAL_TAB
    window.activate_document(0)
    empty_state = fingerprint(window)
    window.open_manual()
    window.manual_page.load_page(manual_home())
    click_feature(window.manual_page, 'batch-edit')
    assert 'unavailable' in window.manual_page.status.text().lower() or '無法使用' in window.manual_page.status.text()
    assert fingerprint(window) == empty_state
    window.close_manual()
    assert fingerprint(window) == empty_state
    window.activate_document(1)
    assert fingerprint(window) == baseline
    window.open_manual()

    report('[Manual/language audit 4/6] Preserving source values, headers and every preference round trip')
    combo = window.matrix_view.view_layout
    canonical = combo.currentText(), combo.currentData(), combo.currentIndex()
    signals = []
    combo.currentTextChanged.connect(signals.append)
    for selected in ('en', 'zh_TW', 'en', 'zh_TW'):
        assert window.change_language(selected)
        QtTest.QTest.qWait(40)
        assert (combo.currentText(), combo.currentData(), combo.currentIndex()) == canonical
        assert not signals, 'Language changed a canonical combo value'
        assert fingerprint(window) == baseline
        assert window.manual_page.current_path == manual_home()
        assert window.document_tabs.tabText(window.active_document_index) == 'Manual *'
    assert QtCore.QSettings(str(settings), QtCore.QSettings.Format.IniFormat).value('interface/language') == 'zh_TW'

    report('[Manual/language audit 5/6] Restoring preference in a fresh window')
    window.close()
    reopened = MainWindow(ROOT / 'data/attack', settings_path=settings, session_path=None)
    reopened.show()
    wait(lambda: reopened.loaded_ok, 'reopened catalog')
    assert language() == 'zh_TW'
    reopened.open_manual()
    assert reopened.manual_page.current_path.name.endswith('+_zh.md')
    assert reopened.info_menu.title() == '資訊'
    reopened.close()
    assert all((ROOT / 'data/attack' / name).read_bytes() == value for name, value in pointers.items())
    assert not (run / 'preview.svg').exists() and not (run / 'preview.xlsx').exists()
    report('[Manual/language audit 6/6] Publishing results')
    (OUT / 'untranslated.json').write_text(json.dumps(sorted(missing), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    payload = {'status': 'PASS', 'features': results, 'fixture_directory': str(run.resolve()),
               'source_data_modified': False, 'documents_modified_by_manual_or_language': False,
               'preference_restored': True, 'canonical_combo_values_preserved': True,
               'file_picker_boundary': 'real Qt file pickers in an isolated fixture directory; cancelled or fixture selected; real downstream dialogs exercised',
               'untranslated_candidates': len(missing)}
    (OUT / 'audit.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report(f'[Manual/language audit] PASS: {len(results)} feature/language cases')


if __name__ == '__main__':
    main()
