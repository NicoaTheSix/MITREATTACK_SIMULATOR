"""NAV-026 paper presets, orientation, physical sizing and native IO. Workflow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
from audit_advanced_navigator import fixture
from audit_export_options import wait
from attack_catalog import external_id
from custom_sources import load_custom
from export_dialogs import SvgSettings
from layer_analysis_dialogs import MatrixExportDialog
from localization import language_manager
from main import configure_application
from matrix_exports import matrix_scene, svg_content, export_matrix, SVG_NS
from navigator_integration import update_annotation, document_layer
from svg_export import DEFAULT_SVG, validate_svg_options
from svg_sizing import PAPER_SIZES, UNITS, paper_dimensions, maximum_length
from ttp_documents import TTPDocument

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/attack'
OUT = ROOT / 'artifacts/svg-paper'
CACHE = OUT / 'cache'
NS = {'s': SVG_NS}
CHECKS = []


def log(message, current=0, total=0):
    print(str(message) + (f' ({current}/{total})' if total else ''), flush=True)


def check(value, message):
    if not value:
        raise AssertionError(message)
    CHECKS.append(message)


def bad(task, message):
    try:
        task()
    except (ValueError, PermissionError, InterruptedError):
        check(True, message)
    else:
        raise AssertionError(message)


def close(a, b, epsilon=1e-7):
    return abs(a-b) < epsilon


def main():
    log('Input cached catalog metadata: ' + str(DATA.resolve()))
    log('Output isolated cache: ' + str(CACHE.resolve()))
    names = ['fixture.json', 'native.svg', 'cancelled.svg', 'audit.json', 'settings-en.png', 'settings-zh.png', 'preview.png']
    names += [size + '-' + orientation + '-' + unit + '.svg' for size in PAPER_SIZES
              for orientation in ('portrait', 'landscape') for unit in UNITS]
    for name in names:
        log('Output file: ' + str((OUT / name).resolve()))
    OUT.mkdir(parents=True, exist_ok=True)
    log('[Paper Audit 1/7] Prepare stable source and validate preset schema', 0, 7)
    path = OUT / 'fixture.json'; path.write_text(json.dumps(fixture()), encoding='utf-8')
    catalog = load_custom(CACHE, str(path.resolve()), '19.2', log)['catalog']
    ids = {external_id(o): k for k, o in catalog.records.items()}
    doc = TTPDocument('Paper exports 中文', catalog, selected={ids['T1000.001']})
    update_annotation(doc, ids['T1000'], '', 'Publication evidence', 20, '#ffffff')
    doc.navigator_layer.update(description='Preset size and orientation', legendItems=[{'label': 'Evidence', 'color': '#ff000080'}])
    before = doc.content_token()
    state = (doc.save_path, doc.saved_fingerprint, doc.export_path, doc.export_format, doc.exported_fingerprint)
    scene = matrix_scene(doc); original_scene = deepcopy(scene)
    expected_inches = {'letter': (8.5, 11), 'legal': (8.5, 14), 'small': (11, 17), 'medium': (18, 24), 'large': (24, 36)}
    check(PAPER_SIZES == expected_inches, 'all five physical paper dimensions match named presets')
    check(validate_svg_options({})['size'] == 'custom' and DEFAULT_SVG['width'] == 0, 'legacy default remains Custom Auto')
    for invalid in ('A0', '', None, True, [], 1):
        bad(lambda v=invalid: validate_svg_options({'size': v}), 'reject invalid paper size ' + repr(invalid))
    for invalid in ('vertical', '', None, True, [], 1):
        bad(lambda v=invalid: validate_svg_options({'orientation': v}), 'reject invalid orientation ' + repr(invalid))
    bad(lambda: paper_dimensions('custom', 'portrait'), 'Custom requires explicit dimensions rather than a guessed paper')
    bad(lambda: paper_dimensions('letter', 'portrait', 'mm'), 'unsupported physical unit rejected')
    for options in ({'size': 'letter', 'width': -1}, {'size': 'letter', 'height': float('nan')},
                    {'size': 'large', 'legend_x': float('inf')}, {'width': 100001}, {'unit': 'in', 'header_height': 1042}):
        bad(lambda value=options: validate_svg_options(value), 'invalid numeric value is not concealed by preset resolution')
    log('[Paper Audit 2/7] Every preset/orientation/unit produces exact physical SVG', 1, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); configure_application(app)
    for size, (short, long) in expected_inches.items():
        for orientation in ('portrait', 'landscape'):
            inches = (short, long) if orientation == 'portrait' else (long, short)
            for unit, factor in UNITS.items():
                options = {'size': size, 'orientation': orientation, 'unit': unit, 'legend_width': 240/factor,
                           'legend_x': 18/factor, 'legend_y': 18/factor, 'theme': 'light'}
                normalized = validate_svg_options(options)
                check(all(close(v*factor, expected*96) for v, expected in zip((normalized['width'], normalized['height']), inches)),
                      size + '/' + orientation + '/' + unit + ': normalized physical size at 96 DPI')
                check(validate_svg_options(normalized) == normalized, size + '/' + orientation + '/' + unit + ': size normalization is idempotent')
                svg = svg_content(scene, options); xml = ET.fromstring(svg)
                (OUT / (size + '-' + orientation + '-' + unit + '.svg')).write_bytes(svg)
                check(xml.get('width') == f'{normalized["width"]:g}'+unit and xml.get('height') == f'{normalized["height"]:g}'+unit,
                      size + '/' + orientation + '/' + unit + ': root retains exact named physical dimensions')
                box = [float(x) for x in xml.get('viewBox').split()]
                check(close(box[2], inches[0]*96) and close(box[3], inches[1]*96), size + '/' + orientation + '/' + unit + ': viewBox matches paper logical dimensions')
                renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(svg))
                check(renderer.isValid() and close(renderer.viewBoxF().width(), inches[0]*96), size + '/' + orientation + '/' + unit + ': actual Qt SVG renderer accepts physical page')
    log('[Paper Audit 3/7] Custom dimensions, automatic axes, header/legend and layout compatibility', 2, 7)
    custom = validate_svg_options({'width': 1600, 'height': 1000})
    check(custom['orientation'] == 'landscape' and custom['width'] == 1600, 'legacy wide custom dimensions remain authoritative')
    check(validate_svg_options({'width': 600, 'height': 900, 'orientation': 'landscape'})['orientation'] == 'portrait', 'Custom derives orientation from explicit dimensions without an implicit backend rotation')
    for values in ({'width': 0, 'height': 0}, {'width': 1000, 'height': 0}, {'width': 0, 'height': 1000}):
        check(QtSvg.QSvgRenderer(QtCore.QByteArray(svg_content(scene, values))).isValid(), 'Custom preserves Auto dimension behavior ' + str(values))
    for mode in ('flat', 'side', 'mini'):
        for theme in ('light', 'dark'):
            svg = svg_content({**scene, 'layout': {'layout': mode}}, {'size': 'letter', 'orientation': 'landscape', 'theme': theme})
            xml = ET.fromstring(svg)
            check(xml.get('width') == '1056px' and xml.get('height') == '816px' and QtSvg.QSvgRenderer(QtCore.QByteArray(svg)).isValid(),
                  mode + '/' + theme + ': preset supports native SVG layout/theme')
    for orientation in ('portrait', 'landscape'):
        xml = ET.fromstring(svg_content(scene, {'size': 'letter', 'orientation': orientation, 'header_height': 120,
            'legend_undocked': True, 'legend_x': 400, 'legend_y': 150, 'legend_width': 200, 'legend_height': 100}))
        check('translate(0 120)' in xml.find('s:g[@id="matrix"]', NS).get('transform') and xml.find('s:g[@id="legend"]', NS) is not None,
              orientation + ': fixed header and undocked legend preserved with paper')
    bad(lambda: svg_content(scene, {'size': 'letter', 'legend_undocked': True, 'legend_x': 800}), 'preset does not silently reposition an out-of-page detached legend')
    bad(lambda: svg_content(scene, {'size': 'letter', 'header_height': 1100}), 'header cannot consume preset matrix area')
    log('[Paper Audit 4/7] Native preset locking, unit round trips and Custom draft restoration', 3, 7)
    manager = language_manager(); manager.set_language('en')
    settings = SvgSettings(); settings.show()
    check(settings.options() is None and not settings.orientation.isEnabled(), 'initial Custom Auto preserves options=None and has no implied direction')
    settings.controls['width'].setValue(900); settings.controls['height'].setValue(1200)
    settings.controls['header_height'].setValue(150); settings.controls['legend_x'].setValue(60)
    settings.controls['legend_width'].setValue(240)
    check(settings.orientation.currentData() == 'portrait' and settings.orientation.isEnabled(), 'explicit Custom dimensions enable direction control')
    settings.orientation.setCurrentIndex(settings.orientation.findData('landscape'))
    check(settings.controls['width'].value() == 1200 and settings.controls['height'].value() == 900, 'Custom Landscape swaps dimensions once')
    settings.orientation.setCurrentIndex(settings.orientation.findData('portrait'))
    check(settings.controls['width'].value() == 900 and settings.controls['height'].value() == 1200, 'Custom Portrait restores short/long axes')
    settings.paper_size.setCurrentIndex(settings.paper_size.findData('letter'))
    check(not settings.controls['width'].isEnabled() and not settings.controls['height'].isEnabled(), 'presets lock manual width and height editing')
    check(settings.controls['width'].value() == 816 and settings.controls['height'].value() == 1056, 'native Letter displays 816 by 1056 pixels')
    settings.orientation.setCurrentIndex(settings.orientation.findData('landscape'))
    check(settings.controls['width'].value() == 1056 and settings.controls['height'].value() == 816, 'native preset Landscape swaps physical axes')
    other_fields = {k: settings.length_pixels[k] for k in ('header_height', 'legend_x', 'legend_y', 'legend_width', 'legend_height')}
    for _ in range(15):
        for unit in ('cm', 'in', 'px'):
            settings.unit.setCurrentIndex(settings.unit.findData(unit))
            values = validate_svg_options(settings.options())
            check(close(values['width']*UNITS[unit], 1056) and close(values['height']*UNITS[unit], 816), 'repeated preset conversion remains exact in '+unit)
    check(all(close(settings.length_pixels[k], v) for k, v in other_fields.items()), 'unit round trips preserve physical header/legend settings without drift')
    settings.unit.setCurrentIndex(settings.unit.findData('cm'))
    settings.paper_size.setCurrentIndex(settings.paper_size.findData('large'))
    settings.paper_size.setCurrentIndex(settings.paper_size.findData('custom'))
    custom = settings.options()
    check(close(custom['width']*UNITS['cm'], 900) and close(custom['height']*UNITS['cm'], 1200) and settings.orientation.currentData() == 'portrait',
          'Custom restores pre-preset dimensions and direction in the newly chosen unit')
    check(settings.controls['width'].isEnabled() and settings.controls['header_height'].value() > 0, 'returning to Custom unlocks dimensions without resetting header')
    settings.unit.setCurrentIndex(settings.unit.findData('px'))
    settings.controls['width'].setValue(100000); settings.controls['height'].setValue(1200)
    for unit in ('in', 'cm', 'px'):
        settings.unit.setCurrentIndex(settings.unit.findData(unit))
        check(close(settings.options()['width']*UNITS[unit], 100000), unit + ': maximum physical width never silently clamps during conversion')
        check(settings.controls['width'].maximum() == maximum_length(unit), unit + ': input range enforces the physical maximum')
    empty = SvgSettings(); empty.paper_size.setCurrentIndex(1); empty.orientation.setCurrentIndex(1); empty.paper_size.setCurrentIndex(0)
    check(empty.options() is None and not empty.orientation.isEnabled(), 'Custom Auto restores original direction and complete defaults after preset visit')
    empty.deleteLater(); settings.close()
    log('[Paper Audit 5/7] Native bilingual controls, exact preview/export and cancellation', 4, 7)
    owner = QtWidgets.QWidget(); owner.operation_report = log
    path = OUT / 'native.svg'; path.write_bytes(b'Previous output')
    dialog = MatrixExportDialog(doc, path, 'svg', {}, owner); dialog.show()
    page = dialog.svg_settings
    page.paper_size.setCurrentIndex(page.paper_size.findData('letter'))
    page.orientation.setCurrentIndex(page.orientation.findData('landscape'))
    page.unit.setCurrentIndex(page.unit.findData('in'))
    page.controls['header_height'].setValue(1.25)
    app.processEvents(); check(dialog.grab().save(str(OUT / 'settings-en.png')), 'English paper/orientation settings screenshot saved')
    manager.set_language('zh_TW'); manager.refresh_all(); app.processEvents()
    check(manager.translate(page.orientation.currentText()) == '橫式' and page.orientation.currentData() == 'landscape', 'Traditional Chinese orientation keeps canonical value')
    check(manager.translate(page.paper_size.currentText()) != page.paper_size.currentText() and page.paper_size.currentData() == 'letter', 'Traditional Chinese preset label keeps canonical size ID')
    check(dialog.grab().save(str(OUT / 'settings-zh.png')), 'Traditional Chinese page controls screenshot saved')
    manager.set_language('en')
    captured = []; show = dialog.show_preview
    dialog.show_preview = lambda payload: (captured.append(payload), show(payload))
    dialog.preview_button.click()
    check(not page.isEnabled(), 'paper/orientation/units freeze during background preview')
    wait(lambda: dialog.worker and not dialog.worker.isRunning() and dialog.preview_button.isEnabled())
    check(captured and dialog.preview.renderer().isValid() and path.read_bytes() == b'Previous output', 'native preview renders without overwriting chosen destination')
    check(dialog.grab().save(str(OUT / 'preview.png')), 'native paper preview screenshot saved')
    dialog.export_button.click(); wait(lambda: dialog.worker and not dialog.worker.isRunning() and dialog.output_path is not None)
    check(path.read_bytes() == captured[-1], 'native paper preview and exported SVG are byte-identical')
    root = ET.parse(path).getroot()
    check(root.get('width') == '11in' and root.get('height') == '8.5in', 'actual native file uses Letter Landscape dimensions')
    page.orientation.setCurrentIndex(page.orientation.findData('portrait'))
    check(dialog.output_path is None and dialog.export_button.isEnabled(), 'changing direction after export enables a fresh export')
    dialog.reject()
    cancelled = MatrixExportDialog(doc, OUT / 'cancelled.svg', 'svg', {}, owner)
    cancelled.svg_settings.paper_size.setCurrentIndex(5); cancelled.reject()
    check(not (OUT / 'cancelled.svg').exists(), 'cancelling preset selection writes no file')
    log('[Paper Audit 6/7] Atomic errors, cancellation and immutable source', 5, 7)
    protected = path.read_bytes()
    bad(lambda: export_matrix(doc, path, 'svg', log, svg_options={'size': 'bad'}), 'invalid paper stops before publication')
    with patch.object(Path, 'replace', side_effect=PermissionError('Paper audit publication error')):
        bad(lambda: export_matrix(doc, path, 'svg', log, svg_options={'size': 'letter'}), 'preset SVG publish failure reported')
    def cancel(message, current=0, total=0):
        if '[Matrix Export 3/4]' in message:
            raise InterruptedError('Paper audit cancellation')
    bad(lambda: export_matrix(doc, path, 'svg', cancel, svg_options={'size': 'legal'}), 'preset SVG cancellation stops before writing')
    check(path.read_bytes() == protected and not list(OUT.glob('*.tmp')), 'preset failure/cancellation preserves previous output and cleans temporary files')
    check(doc.content_token() == before and scene == original_scene, 'paper and direction changes preserve complete source document and projected scene')
    check(state == (doc.save_path, doc.saved_fingerprint, doc.export_path, doc.export_format, doc.exported_fingerprint), 'preset export preserves save/export baseline markers')
    check('orientation' not in document_layer(doc) and 'size' not in document_layer(doc), 'paper and orientation never enter saved Navigator layer')
    log('[Paper Audit 7/7] Publish reproducible result', 6, 7)
    (OUT / 'audit.json').write_text(json.dumps({'passed': True, 'count': len(CHECKS), 'checks': CHECKS}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log(f'[Paper Audit] PASS: {len(CHECKS)} checks', 7, 7)
    owner.close()


if __name__ == '__main__':
    main()
