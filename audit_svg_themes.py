"""NAV-025 SVG theme pixels, contrast, overlays and native export audit. Workflow: README.md."""
from copy import deepcopy
from pathlib import Path
import json
import uuid
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
from audit_advanced_navigator import fixture
from audit_export_options import wait
from attack_catalog import external_id, load_catalog
from custom_sources import load_custom
from layer_analysis import snapshot_document
from layer_analysis_dialogs import MatrixExportDialog
from localization import language_manager
from main import configure_application
from matrix_exports import matrix_scene, svg_content, export_matrix, SVG_NS
from navigator_integration import update_annotation, document_layer
from navigator_visuals import LayerAppearance, OverlayAppearance
from svg_export import DEFAULT_SVG, validate_svg_options
from svg_themes import palette, project_scene
from ttp_documents import TTPDocument

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/attack'
OUT = ROOT / 'artifacts/svg-themes'
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


def image_for(payload):
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(payload))
    if not renderer.isValid():
        raise AssertionError('Invalid SVG')
    image = QtGui.QImage(renderer.defaultSize(), QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image); renderer.render(painter); painter.end()
    return image


def contrast(a, b):
    def luminance(color):
        channels = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + .05) / (low + .05)


def cells(scene):
    return [cell for column in scene['columns'] for cell in column['cells']]


def cell_rect(xml, identity):
    return next(rect for rect in xml.findall('.//s:g[@id="matrix"]/s:rect', NS)
                if (rect.findtext('s:title', '', NS).splitlines() or [''])[0].startswith(identity + '  '))


def main():
    log('Input official catalogs: ' + str(DATA.resolve()))
    log('Output fixture, cache, vectors, PNG previews and report: ' + str(OUT.resolve()))
    outputs = ['fixture.json', 'native.svg', 'cancelled.svg', 'reopened.svg', 'audit.json',
               'settings-en.png', 'settings-zh.png', 'native-light-preview.png', 'native-dark-preview.png']
    outputs += [layout + '-' + theme + extension for layout in ('flat', 'side', 'mini')
                for theme in ('light', 'dark') for extension in ('.svg', '.png')]
    for name in outputs:
        log('Output file: ' + str((OUT / name).resolve()))
    OUT.mkdir(parents=True, exist_ok=True)
    log('[SVG Theme Audit 1/7] Prepare alpha/opaque/disabled/neutral fixture', 0, 7)
    payload = fixture()
    template = next(o for o in payload['objects'] if o.get('name') == 'Beta')
    for identity, name in [('T1006', 'Black 中文'), ('T1007', 'White'), ('T1008', 'No annotation'), ('T1009', 'Transparent')]:
        obj = deepcopy(template); obj['name'] = name
        obj['id'] = 'attack-pattern--' + str(uuid.uuid5(uuid.NAMESPACE_DNS, 'svg-theme-' + identity))
        obj['external_references'][0]['external_id'] = identity
        obj['x_mitre_platforms'] = ['Windows', 'Linux']
        payload['objects'].append(obj)
    path = OUT / 'fixture.json'; path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    catalog = load_custom(CACHE, str(path.resolve()), '19.2', log)['catalog']
    ids = {external_id(o): k for k, o in catalog.records.items()}
    doc = TTPDocument('SVG themes <research> 中文', catalog, selected={ids['T1000.001']})
    update_annotation(doc, ids['T1000'], '', 'Parent evidence', 50, '')
    update_annotation(doc, ids['T1000.001'], '', 'Child evidence', 50, '#ffffff')
    update_annotation(doc, ids['T1001'], '', 'Disabled evidence', 100, '#ff0000')
    next(r for r in doc.navigator_layer['techniques'] if r['techniqueID'] == 'T1001')['enabled'] = False
    update_annotation(doc, ids['T1006'], '', 'Black evidence', None, '#000000')
    update_annotation(doc, ids['T1007'], '', 'White evidence', None, '#ffffff')
    update_annotation(doc, ids['T1009'], '', '', 0, '')
    doc.navigator_layer.update(gradient={'colors': ['#ff000000', '#ff0000ff'], 'minValue': 0, 'maxValue': 100},
        legendItems=[{'label': 'Transparent red 中文', 'color': '#ff000080'}, {'label': 'White', 'color': '#ffffff'},
                     {'label': 'Black', 'color': '#000000'}, {'label': 'Invisible', 'color': '#ffffff00'}],
        description='Publication evidence & annotation <literal>')
    before = doc.content_token()
    save_state = (doc.save_path, doc.saved_fingerprint, doc.saved_file_sha256,
                  doc.export_path, doc.export_format, doc.exported_fingerprint)
    scene = matrix_scene(doc)
    frozen = deepcopy(scene)
    check(DEFAULT_SVG['theme'] == 'dark' and validate_svg_options({})['theme'] == 'dark', 'legacy exports default to Dark')
    for invalid in ('Light', '', 'sepia', None, [], True):
        bad(lambda value=invalid: validate_svg_options({'theme': value}), 'reject invalid SVG theme ' + repr(invalid))
    check(LayerAppearance(document_layer(doc), catalog).cell('T1000', 'execution')['rawColor'] == '#ff000080', 'raw interpolated alpha retained for SVG recomposition')
    log('[SVG Theme Audit 2/7] Every layout/theme, actual pixels and text contrast', 1, 7)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([]); configure_application(app)
    application_palette = QtGui.QPalette(app.palette())
    for theme in ('dark', 'light'):
        colors = palette(theme)
        for layout in ('flat', 'side', 'mini'):
            current = {**scene, 'layout': {'layout': layout}}
            options = {**DEFAULT_SVG, 'theme': theme, 'width': 1100, 'height': 1000}
            svg = svg_content(current, options)
            path = OUT / (layout + '-' + theme + '.svg'); path.write_bytes(svg)
            xml = ET.fromstring(svg); image = image_for(svg)
            check(image.pixelColor(0, 0).name() == colors['canvas'], layout + '/' + theme + ': rendered canvas uses selected theme')
            check(image.pixelColor(0, 0).alpha() == 255, layout + '/' + theme + ': canvas is opaque')
            body = xml.find('s:g[@id="matrix"]', NS)
            if layout == 'mini':
                check(cell_rect(xml, 'T1000.001').get('stroke') == '#3794ff', theme + ': advanced Mini export retains selected technique outline')
            scale = float(body.get('transform').split('scale(')[1].split(')')[0])
            top = float(body.get('transform').split('translate(0 ')[1].split(')')[0])
            rect = cell_rect(xml, 'T1000')
            expected = '#f97a7a' if theme == 'light' else '#911213'
            check(rect.get('fill') == expected, layout + '/' + theme + ': transparent gradient composites against correct neutral base')
            x = (float(rect.get('x')) + float(rect.get('width')) * .8) * scale
            y = top + (float(rect.get('y')) - 100 + float(rect.get('height')) * .35) * scale
            check(image.pixelColor(round(x), round(y)).name() == expected, layout + '/' + theme + ': actual technique pixels match alpha projection')
            neutral = cell_rect(xml, 'T1008'); disabled = cell_rect(xml, 'T1001')
            check(neutral.get('fill') == colors['neutral'] and disabled.get('fill') == colors['disabled'], layout + '/' + theme + ': neutral and disabled backgrounds remain distinct')
            check(cell_rect(xml, 'T1009').get('fill') == colors['neutral'], layout + '/' + theme + ': fully transparent score stays neutral')
            projected = project_scene(current, theme)
            for identity in ('T1006', 'T1007', 'T1001', 'T1008', 'T1000'):
                cell = next(c for c in cells(projected) if c['id'] == identity)
                check(contrast(cell['background'], cell['foreground']) >= 4.5, layout + '/' + theme + ': readable text for ' + identity)
            check(contrast(colors['text'], colors['legend']) >= 4.5, layout + '/' + theme + ': legend text contrast')
            legend = xml.find('.//s:g[@id="legend"]', NS)
            swatches = legend.findall('s:rect', NS)
            check(swatches[0].get('fill') == colors['legend'], layout + '/' + theme + ': docked legend panel uses theme')
            check(swatches[-1].get('fill') == colors['legend'], layout + '/' + theme + ': zero-alpha swatch composites onto legend panel')
            if theme == 'light':
                check(any(n.get('stroke-width') == '4' for n in xml.findall('.//s:line', NS)), layout + ': light annotation markers retain colored line with contrast backing')
            check(image.save(str(OUT / (layout + '-' + theme + '.png'))), layout + '/' + theme + ': raster preview saved')
    check(scene == frozen and doc.content_token() == before, 'all theme/layout renders preserve source scene and document')
    log('[SVG Theme Audit 3/7] Headers, detached legends, hidden colors and aggregates', 2, 7)
    for header in ('#000000', '#ffffff'):
        altered = {**scene, 'tactic_background': header}
        xml = ET.fromstring(svg_content(altered, {'theme': 'light', 'cell_border': '#ff00aa'}))
        body = xml.find('s:g[@id="matrix"]', NS)
        check(any(r.get('fill') == header and r.get('stroke') == '#ff00aa' for r in body.findall('s:rect', NS)), 'explicit tactic background and custom border survive light theme ' + header)
        expected_foreground = '#ffffff' if header == '#000000' else '#000000'
        check(any(t.get('fill') == expected_foreground and t.text == 'Execution' for t in body.findall('s:text', NS)), 'saved tactic header has contrasting label ' + header)
    detached = ET.fromstring(svg_content(scene, {'theme': 'light', 'show_header': False, 'legend_undocked': True,
        'width': 1100, 'height': 1000, 'legend_x': 750, 'legend_y': 80, 'legend_width': 300}))
    check(detached.find('s:g[@id="legend"]', NS) is not None and len(detached.find('s:g[@id="header"]', NS)) == 0, 'detached light legend remains visible without header')
    hidden = ET.fromstring(svg_content(scene, {'theme': 'light', 'show_header': False, 'show_legend': False}))
    check(hidden.find('.//s:g[@id="legend"]', NS) is None, 'light theme preserves independent legend visibility')
    neutral = project_scene(matrix_scene(doc, colors=False), 'light')
    check(all(c['background'] == palette('light')['neutral'] for c in cells(neutral)), 'hide-colors remains neutral including disabled cells')
    hidden_doc = snapshot_document(doc); hidden_doc.navigator_layer['hideDisabled'] = True
    check(not any(c['id'] == 'T1001' for c in cells(project_scene(matrix_scene(hidden_doc), 'light'))), 'theme respects Hide disabled projection')
    aggregate = snapshot_document(doc); aggregate.navigator_layer['layout'] = {'showAggregateScores': True, 'aggregateFunction': 'average'}
    update_annotation(aggregate, ids['T1000.001'], '', '', 100, '')
    aggregate_scene = project_scene(matrix_scene(aggregate), 'light')
    parent = next(c for c in cells(aggregate_scene) if c['id'] == 'T1000')
    check(parent['style']['aggregateScore'] == 75 and parent['style']['rawColor'] == '#ff0000bf', 'aggregate gradient retains raw alpha rather than dark baked color')
    check(parent['background'] != next(c for c in cells(scene) if c['id'] == 'T1000')['background'], 'light aggregate uses recomposed output color')
    log('[SVG Theme Audit 4/7] Overlay alpha, zero-opacity exclusion and per-source display switches', 3, 7)
    blue = snapshot_document(doc); blue.name = 'Blue source'
    blue.navigator_layer = {'name': blue.name, 'domain': catalog.domain, 'versions': {'attack': catalog.version, 'layer': '4.5', 'navigator': '5.3.2'},
                           'techniques': [{'techniqueID': 'T1000', 'color': '#0000ff'}]}
    over = matrix_scene(doc, sources=[doc, blue])
    over_cell = next(c for c in cells(project_scene(over, 'light')) if c['id'] == 'T1000')
    check(over_cell['background'] == '#7c3dbc', 'overlay recomposes each alpha source on light base before equal-weight mixing')
    check(over_cell['style']['sources'][0]['color'] == '#f97a7a', 'SVG hover provenance reports the actual theme-composited source color')
    reversed_scene = matrix_scene(doc, sources=[blue, doc])
    check(next(c for c in cells(project_scene(reversed_scene, 'light')) if c['id'] == 'T1000')['background'] == over_cell['background'], 'light overlay remains independent of source order')
    check(OverlayAppearance([(doc.name, document_layer(doc)), (blue.name, document_layer(blue))], document_layer(doc), catalog).cell('T1000', 'execution')['background'] != over_cell['background'], 'native dark overlay remains unchanged while SVG recomposes')
    no_score = snapshot_document(doc); no_score.navigator_layer['x_ttp_studio_display'] = {'score_color': False}
    switch_scene = project_scene(matrix_scene(no_score, sources=[no_score, blue]), 'light')
    check(next(c for c in cells(switch_scene) if c['id'] == 'T1000')['background'] == '#0000ff', 'per-source background switch still excludes score contribution')
    transparent = snapshot_document(doc)
    update_annotation(transparent, ids['T1000'], '', '', 0, '')
    zero_scene = project_scene(matrix_scene(transparent, sources=[transparent, blue]), 'light')
    check(next(c for c in cells(zero_scene) if c['id'] == 'T1000')['background'] == '#0000ff', 'zero-alpha overlay source never dilutes opaque source')
    log('[SVG Theme Audit 5/7] Actual native theme choice, bilingual preview and identical export bytes', 4, 7)
    manager = language_manager(); manager.set_language('en')
    owner = QtWidgets.QWidget(); owner.operation_report = log
    target = OUT / 'native.svg'; original = b'Previous output'; target.write_bytes(original)
    dialog = MatrixExportDialog(doc, target, 'svg', {}, owner); dialog.show()
    settings = dialog.svg_settings
    check(settings.options() is None and settings.theme.currentData() == 'dark', 'native default keeps legacy options=None and Dark')
    settings.theme.setCurrentIndex(settings.theme.findData('light'))
    check(settings.options()['theme'] == 'light' and dialog.export_button.isEnabled(), 'native Light choice reaches export options')
    settings.controls['width'].setValue(1100); settings.controls['height'].setValue(1000)
    app.processEvents(); check(dialog.grab().save(str(OUT / 'settings-en.png')), 'English SVG theme setting screenshot saved')
    manager.set_language('zh_TW'); manager.refresh_all(); app.processEvents()
    check(manager.translate(settings.theme.currentText()) == '淺色' and settings.theme.currentData() == 'light', 'Traditional Chinese theme presentation retains canonical data')
    check(dialog.grab().save(str(OUT / 'settings-zh.png')), 'Traditional Chinese theme setting screenshot saved')
    manager.set_language('en')
    captured = []
    original_show = dialog.show_preview
    # Worker callback is bound when Preview is requested; capture exactly what QSvgWidget receives.
    dialog.show_preview = lambda value: (captured.append(value), original_show(value))
    dialog.preview_button.click()
    check(not settings.isEnabled(), 'theme settings lock during background rendering')
    wait(lambda: dialog.worker and not dialog.worker.isRunning() and dialog.preview_button.isEnabled())
    check(captured and dialog.preview.renderer().isValid(), 'native background preview receives valid Light SVG')
    check(target.read_bytes() == original and dialog.output_path is None, 'preview leaves existing destination bytes untouched')
    check(dialog.grab().save(str(OUT / 'native-light-preview.png')), 'native light preview screenshot saved')
    dialog.export_button.click(); wait(lambda: dialog.worker and not dialog.worker.isRunning() and dialog.output_path is not None)
    check(target.read_bytes() == captured[-1], 'native preview and exported Light SVG are byte-identical')
    settings.theme.setCurrentIndex(settings.theme.findData('dark'))
    check(dialog.output_path is None and dialog.export_button.isEnabled(), 'changing theme after export enables fresh export')
    dialog.preview_button.click(); wait(lambda: dialog.worker and not dialog.worker.isRunning() and dialog.preview_button.isEnabled())
    dark_preview = captured[-1]
    dialog.export_button.click(); wait(lambda: dialog.worker and not dialog.worker.isRunning() and dialog.output_path is not None)
    check(target.read_bytes() == dark_preview and image_for(dark_preview).pixelColor(0, 0).name() == '#1e1e1e', 'switching back to Dark has matching preview and output without residual Light styling')
    check(dialog.grab().save(str(OUT / 'native-dark-preview.png')), 'native dark preview screenshot saved')
    dialog.reject()
    cancelled = MatrixExportDialog(doc, OUT / 'cancelled.svg', 'svg', {}, owner)
    cancelled.svg_settings.theme.setCurrentIndex(1); cancelled.reject()
    check(not (OUT / 'cancelled.svg').exists(), 'cancelling theme selection writes no file')
    reopened = MatrixExportDialog(doc, OUT / 'reopened.svg', 'svg', {}, owner)
    check(reopened.svg_settings.theme.currentData() == 'dark', 'new export dialog starts at Dark without persisting previous dialog theme')
    reopened.reject()
    log('[SVG Theme Audit 6/7] Validation, atomic errors, cancellation and domain preservation', 5, 7)
    protected = target.read_bytes()
    bad(lambda: export_matrix(doc, target, 'svg', log, svg_options={'theme': 'bad'}), 'invalid theme rejected before output publication')
    with patch.object(Path, 'replace', side_effect=PermissionError('Theme audit publication failure')):
        bad(lambda: export_matrix(doc, target, 'svg', log, svg_options={'theme': 'light'}), 'failed Light SVG publication reports error')
    def cancel(message, current=0, total=0):
        if '[Matrix Export 3/4]' in message:
            raise InterruptedError('Cancel before writing')
    bad(lambda: export_matrix(doc, target, 'svg', cancel, svg_options={'theme': 'light'}), 'Light SVG cancellation stops before writing')
    check(target.read_bytes() == protected and not list(OUT.glob('*.tmp')), 'theme validation/failure/cancellation preserves previous output and removes temporary files')
    current = load_catalog(DATA, log)
    for domain in ('enterprise-attack', 'mobile-attack', 'ics-attack'):
        official = current.for_domain(domain)
        sample = TTPDocument(domain, official)
        key = next(iter(official.records)); identity = external_id(official.records[key])
        update_annotation(sample, key, '', 'Real domain evidence', None, '#ffffff')
        selected = matrix_scene(sample, query=identity)
        check(image_for(svg_content(selected, {'theme': 'light'})).pixelColor(0, 0).name() == '#ffffff', domain + ': real catalog Light SVG renders')
    check(doc.content_token() == before and scene == frozen, 'native preview/export/cancel and all model checks preserve annotations, selection, saved state and source scene')
    check(save_state == (doc.save_path, doc.saved_fingerprint, doc.saved_file_sha256,
                        doc.export_path, doc.export_format, doc.exported_fingerprint), 'SVG theme never changes Studio/save/export baseline markers')
    check(app.palette() == application_palette, 'SVG theme choices preserve application palette')
    check('svg_theme' not in document_layer(doc) and 'rawColor' not in json.dumps(document_layer(doc)), 'SVG theme and render provenance never enter saved Navigator layer')
    log('[SVG Theme Audit 7/7] Publish reproducible report', 6, 7)
    (OUT / 'audit.json').write_text(json.dumps({'passed': True, 'count': len(CHECKS), 'checks': CHECKS}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log(f'[SVG Theme Audit] PASS: {len(CHECKS)} checks', 7, 7)
    owner.close()


if __name__ == '__main__':
    main()
