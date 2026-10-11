"""Exercise official version downloads and actual Qt switching. Workflow: README.md."""
from pathlib import Path
import json
import os
import sys
import time
import uuid
from PySide6 import QtCore, QtTest, QtWidgets
from attack_catalog import external_id
from attack_versions import cached_discovery, discover_versions, parse_versions, prepare_version, snapshot_pointer
from main import MainWindow, configure_application
from version_dialog import VersionDialog, VersionWorker
from scripts.download_attack_data import write_json

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'attack'
OUT = ROOT / 'artifacts'
TEST = OUT / ('version-audit-data-' + uuid.uuid4().hex)
RESULT = OUT / 'version-audit.json'
SCREEN = OUT / 'version-preview.png'
checks = []


def report(message, current=0, total=0):
    print(message + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, name):
    if not value:
        raise AssertionError(name)
    checks.append(name)


def wait(predicate, description, timeout=120):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise TimeoutError(description)
        QtTest.QTest.qWait(20)


def switch(window, version, discovery, persist=True):
    previous = window.catalog.version
    errors = []
    worker = VersionWorker(TEST, version, discovery, window, persist=persist)
    worker.progress.connect(window.report)
    worker.failed.connect(errors.append)
    worker.completed.connect(window.apply_version)
    worker.start()
    wait(lambda: not worker.isRunning(), 'worker download/load')
    QtWidgets.QApplication.processEvents()
    if errors:
        return errors
    wait(lambda: window.loaded_ok and window.catalog.version == version and window.version_action.isEnabled(), 'tree switch')
    return errors


def audit_picker():
    import attack_versions
    output = OUT / 'version-picker-audit.json'
    print(f'Input root: {DATA.resolve()}\nOutput report: {output.resolve()}\nOutput preview: {SCREEN.resolve()}', flush=True)
    report('[Picker audit 1/3] Cached versions and display')
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    picker = VersionDialog(DATA, '19.2', auto_refresh=False)
    picker.show()
    check(picker.table.rowCount() == 41, 'all indexed releases available offline')
    check(picker.table.horizontalHeaderItem(2).text() == 'Updated (UTC)', 'index modification date labelled accurately')
    report('[Picker audit 2/3] Offline refresh preserves cached list and finishes progress')
    fetch = attack_versions.fetch
    def unavailable(*args, **kwargs):
        raise OSError('Simulated offline network')
    attack_versions.fetch = unavailable
    try:
        picker.refresh_button.click()
        wait(lambda: not picker.worker.isRunning(), 'offline refresh')
        QtWidgets.QApplication.processEvents()
        check('Offline / refresh failed' in picker.source.text(), 'offline fallback visibly identified')
        check(picker.table.rowCount() == 41, 'cached list retained after failed refresh')
        check(picker.progress.maximum() == 1 and picker.progress.value() == 1, 'progress finishes after background operation')
        check(picker.status.text().startswith('Ready'), 'finished status does not show stale output paths')
        check(picker.refresh_button.isEnabled(), 'refresh re-enabled after completion')
    finally:
        attack_versions.fetch = fetch
    report('[Picker audit 3/3] Search, close and final screenshot')
    picker.search.setText('v1.0')
    visible = [row for row in range(picker.table.rowCount()) if not picker.table.isRowHidden(row)]
    check(len(visible) == 1, 'version search')
    picker.table.selectRow(visible[0])
    check(picker.switch_button.isEnabled(), 'downloaded historical version selectable offline')
    picker.search.clear()
    picker.table.selectRow(0)
    QtTest.QTest.qWait(180)
    check(picker.grab().save(str(SCREEN)), 'updated preview saved')
    picker.close()
    write_json(output, {'status': 'PASS', 'checks': checks, 'offline_refresh_simulated': True})
    report(f'[Picker audit] PASS: {len(checks)} checks')
    return 0


def main():
    if '--picker-only' in sys.argv:
        return audit_picker()
    print(f'Input root: {DATA.resolve()}\nOutput report: {RESULT.resolve()}\nOutput preview: {SCREEN.resolve()}\nOutput test root: {TEST.resolve()}', flush=True)
    report('[Version audit 1/6] Discovering every official Enterprise release')
    discovery = discover_versions(DATA, report)
    check(bool(discovery.get('commit_sha')), 'discovery pinned commit')
    check(len(discovery['versions']) >= 41, 'complete historical release list')
    check(discovery['versions'][0]['version'] == '19.2', 'numeric newest-first sorting')
    check(discovery['versions'][-1]['version'] == '1.0', 'oldest version included')
    versions = {row['version']: row for row in discovery['versions']}
    check('ics-attack' not in versions['1.0']['domains'], 'missing historical domain shown accurately')
    report('[Version audit 2/6] Downloading real historical snapshots (v1.0 and v11.2)')
    old, _ = prepare_version(DATA, '1.0', discovery, report)
    middle, _ = prepare_version(DATA, '11.2', discovery, report)
    check(old.version == '1.0' and old.records, 'oldest official bundle loads')
    check(not old.objects_by_domain['ics-attack'], 'absent ICS remains empty')
    check(not middle.objects_by_domain['mobile-attack'], 'Mobile beta label not mixed into Enterprise v11.2')
    check(bool(middle.objects_by_domain['ics-attack']), 'available historical ICS loads')
    report('[Version audit 3/6] Preparing isolated pointer/cache test paths')
    TEST.mkdir(parents=True)
    for version in ('19.2', '1.0', '11.2'):
        source = DATA / ('v' + version)
        target = TEST / source.name
        target.mkdir()
        for path in source.iterdir():
            if path.is_file() and not path.name.endswith('.part'):
                os.link(path, target / path.name)
    os.link(DATA / 'versions-cache.json', TEST / 'versions-cache.json')
    write_json(TEST / 'latest.json', snapshot_pointer(TEST, '19.2'))
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(TEST)
    window.show()
    wait(lambda: window.loaded_ok, 'initial UI')
    check(window.version_action.text() == 'Version (v19.2)', 'top Version action reflects selected version')
    common = next(key for key in old.records if key in window.items_by_id)
    dropped = next(key for key in window.items_by_id if key not in old.records)
    window.items_by_id[common][0].setCheckState(QtCore.Qt.CheckState.Checked)
    window.items_by_id[dropped][0].setCheckState(QtCore.Qt.CheckState.Checked)
    window.switch_category('Groups')
    window.search.setText('old-filter')
    report('[Version audit 4/6] Switching actual models, selections and procedure details')
    check(not switch(window, '1.0', discovery), 'switch to oldest version succeeds')
    check(window.catalog.version == '1.0', 'UI catalog replaced')
    check(window.selected == {common}, 'valid selections retained; unavailable selection removed')
    check(not window.search.text(), 'stale search cleared')
    check(window.active_category == 'Groups', 'active navigation category restored')
    check(not window.library_items['Assets'], 'old missing Assets category is empty')
    window.switch_category('TTP')
    window.show_record(common)
    check(window.details.copy_content['Title'] == old.records[common]['name'], 'copy payload uses new release')
    check('Procedure Examples' in window.details.toPlainText(), 'historical procedures render')
    check(set(window.items_by_id) == set(old.records), 'tree fully rebuilt with no stale technique rows')
    check(json.loads((TEST / 'active.json').read_text())['attack_version'] == '1.0', 'active version persisted')
    check(json.loads((TEST / 'latest.json').read_text())['attack_version'] == '19.2', 'latest pointer stays intact')
    check(not switch(window, '11.2', discovery), 'historical missing-Mobile version switch succeeds')
    check(set(window.items_by_id) == set(middle.records), 'intermediate tree fully rebuilt')
    check(not switch(window, '19.2', discovery), 'switch back to current version succeeds')
    check(len(window.catalog.records) == 697 and len(window.library_items['Assets']) == 18, 'modern libraries restored')
    report('[Version audit 5/6] Failures preserve original catalog and saved choice; restart restores choice')
    before = (TEST / 'active.json').read_bytes()
    old_catalog = window.catalog
    check(bool(switch(window, '999.0', discovery)), 'invalid remote version reports failure')
    check(window.catalog is old_catalog and (TEST / 'active.json').read_bytes() == before, 'failure leaves UI and pointer unchanged')
    # Corrupt only an isolated pointer, never a hard-linked source artifact.
    write_json(TEST / 'active.json', {'attack_version': '999.0', 'manifest': '../outside/manifest.json'})
    fallback = MainWindow(TEST)
    fallback.show()
    wait(lambda: fallback.loaded_ok, 'saved-pointer fallback')
    check(fallback.catalog.version == '19.2', 'invalid saved choice falls back to latest')
    fallback.close()
    check(not switch(window, '1.0', discovery), 'select persisted older release')
    restart = MainWindow(TEST)
    restart.show()
    wait(lambda: restart.loaded_ok, 'restart choice')
    check(restart.catalog.version == '1.0', 'restart restores saved release')
    restart.close()
    check(not switch(window, '19.2', discovery), 'test restores current release in isolated cache')
    report('[Version audit 6/6] Testing real picker rows, search and screenshot')
    picker = VersionDialog(TEST, window.catalog.version, window, auto_refresh=False)
    picker.show()
    QtWidgets.QApplication.processEvents()
    if picker.worker:
        picker.worker.requestInterruption()
        wait(lambda: not picker.worker.isRunning(), 'picker refresh cancellation', 45)
    check(picker.table.rowCount() == len(discovery['versions']), 'picker includes every indexed release')
    picker.search.setText('v1.0')
    QtWidgets.QApplication.processEvents()
    visible = [row for row in range(picker.table.rowCount()) if not picker.table.isRowHidden(row)]
    check(len(visible) == 1, 'picker search filters versions')
    picker.table.selectRow(visible[0])
    check(picker.switch_button.isEnabled(), 'picker allows selection of different release')
    picker.chosen.connect(window.apply_version)
    picker.switch_button.click()
    wait(lambda: not picker.worker.isRunning(), 'actual picker switch')
    wait(lambda: window.catalog.version == '1.0' and window.loaded_ok, 'actual picker tree switch')
    check(window.catalog.version == '1.0', 'native Switch version button applies selected release')
    check(not switch(window, '19.2', discovery), 'return to latest after picker switch')
    # Screenshot a local snapshot of the picker without issuing another refresh.
    picker.current = '19.2'
    picker.populate(discovery)
    picker.search.clear()
    picker.closing = False
    picker.show()
    QtTest.QTest.qWait(180)
    check(picker.grab().save(str(SCREEN)), 'version picker screenshot saved')
    picker.close()
    window.close()
    write_json(RESULT, {'status': 'PASS', 'checks': checks, 'official_versions': len(discovery['versions']),
                        'source': discovery['source'], 'tested_versions': ['19.2', '11.2', '1.0'], 'isolated_data_root': str(TEST)})
    report(f'[Version audit] PASS: {len(checks)} checks; {len(discovery["versions"])} official versions')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
