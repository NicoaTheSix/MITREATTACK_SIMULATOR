"""Validated per-layer native display/search preferences. Workflow: README.md."""
import re

DISPLAY_KEY = 'x_ttp_studio_display'
SOURCE_KEY = 'x_ttp_studio_source_search_fields'
SOURCE_FIELDS = ('name', 'id', 'description')
DISPLAY_DEFAULTS = dict(manual_color=True, score_color=True, aggregate_color=True,
                        comment_indicator=True, metadata_indicator=True, link_indicator=True,
                        comment_color='#ffcc00', metadata_color='#ffcc00', link_color='#4daafc', legend_visible=True)


def display_preferences(layer):
    return {**DISPLAY_DEFAULTS, **layer.get(DISPLAY_KEY, {})}


def source_fields(layer):
    return layer.get(SOURCE_KEY, list(SOURCE_FIELDS))


def validate_preferences(layer):
    from context_templates import validate_context
    validate_context(layer)
    fields = source_fields(layer)
    if (not isinstance(fields, list) or not fields or any(not isinstance(f, str) for f in fields)
            or len(fields) != len(set(fields)) or set(fields) - set(SOURCE_FIELDS)):
        raise ValueError('Source search needs one or more unique name / id / description fields.')
    value = layer.get(DISPLAY_KEY, {})
    if not isinstance(value, dict) or set(value) - DISPLAY_DEFAULTS.keys():
        raise ValueError('Unsupported native display preferences.')
    for key, setting in value.items():
        if key.endswith('_color') and key in ('comment_color', 'metadata_color', 'link_color'):
            if not isinstance(setting, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', setting):
                raise ValueError('Indicator colors must be #RRGGBB.')
        elif type(setting) is not bool:
            raise ValueError('Display switches must be booleans.')


def indicator_style(style, preferences):
    """Visibility is independent of annotation classification and stored content."""
    colors = []
    for kind in ('comment', 'metadata', 'link'):
        if style.get(kind + 'Present') and preferences[kind + '_indicator']:
            color = preferences[kind + '_color'].lower()
            if color not in colors:
                colors.append(color)
    return {'markerColors': colors,
            'noteIndicator': bool((style.get('commentPresent') and preferences['comment_indicator']) or
                                  (style.get('metadataPresent') and preferences['metadata_indicator'])),
            'linkIndicator': bool(style.get('linkPresent') and preferences['link_indicator'])}


def display_editor(layer):
    """Draft-only widget; caller validates and commits on Save."""
    from PySide6 import QtGui, QtWidgets
    page = QtWidgets.QWidget()
    form = QtWidgets.QFormLayout(page)
    preferences = display_preferences(layer)
    controls = {}
    for key, text in [('manual_color', 'Show manually assigned technique colors'),
                      ('score_color', 'Show original score gradient colors'),
                      ('aggregate_color', 'Show aggregate score gradient colors'),
                      ('comment_indicator', 'Show comment / source Note indicators'),
                      ('metadata_indicator', 'Show metadata indicators'),
                      ('link_indicator', 'Show link indicators'), ('legend_visible', 'Show matrix legend')]:
        control = QtWidgets.QCheckBox(text)
        control.setChecked(preferences[key])
        form.addRow(control)
        controls[key] = control
    for key, text in [('comment_color', 'Comment / Note color'), ('metadata_color', 'Metadata color'), ('link_color', 'Link color')]:
        editor = QtWidgets.QLineEdit(preferences[key])
        row = QtWidgets.QHBoxLayout()
        row.addWidget(editor)
        button = QtWidgets.QPushButton('Choose…')
        def choose(checked=False, editor=editor, text=text):
            color = QtWidgets.QColorDialog.getColor(QtGui.QColor(editor.text()), page, text)
            if color.isValid(): editor.setText(color.name())
        button.clicked.connect(choose)
        row.addWidget(button)
        form.addRow(text, row)
        controls[key] = editor
    hint = QtWidgets.QLabel('Display switches preserve scores, colors, annotations and annotated-child counts. '
                           'Manual color takes precedence, then enabled aggregate color, then original score color. '
                           'These native per-layer preferences use x_ttp_studio_* extensions.')
    hint.setWordWrap(True)
    form.addRow(hint)
    return page, controls


def editor_values(controls):
    return {key: control.text().strip() if key in ('comment_color', 'metadata_color', 'link_color') else control.isChecked()
            for key, control in controls.items()}
