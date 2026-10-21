"""Presentation-only English / Taiwan Traditional Chinese. Workflow: README.md."""
from __future__ import annotations

import html
import atexit
import json
from pathlib import Path
import re
import string

from PySide6 import QtCore, QtGui, QtWidgets

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / 'locales' / 'zh_TW.json'
LANGUAGES = ('en', 'zh_TW')
_manager = None


def language():
    return _manager.language if _manager is not None else 'en'


def tr(text):
    return _manager.translate(str(text)) if _manager is not None else str(text)


def translate_html(source):
    """Translate UI text nodes only; never translate attributes or code blocks."""
    chunks = re.split(r'(<[^>]+>)', source)
    code_depth = 0
    for index, chunk in enumerate(chunks):
        if chunk.startswith('<'):
            if re.match(r'<(?:pre|code)\b', chunk, re.I):
                code_depth += 1
            elif re.match(r'</(?:pre|code)\b', chunk, re.I):
                code_depth = max(0, code_depth - 1)
        elif not code_depth:
            decoded = html.unescape(chunk)
            translated = tr(decoded)
            if translated != decoded:
                chunks[index] = html.escape(translated)
    return ''.join(chunks)


class LocalizedTextBrowser(QtWidgets.QTextBrowser):
    """Keep original rich text separate from its translated presentation."""
    def setHtml(self, source):
        self._locale_html = source
        super().setHtml(translate_html(source))

    def retranslate(self):
        source = getattr(self, '_locale_html', None)
        if source is None:
            return
        position = self.verticalScrollBar().value()
        super().setHtml(translate_html(source))
        self.verticalScrollBar().setValue(position)


class TranslatedChoiceDelegate(QtWidgets.QStyledItemDelegate):
    def displayText(self, value, locale):
        return tr(super().displayText(value, locale))


class TranslatedTableDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        table = self.parent()
        tracked = table.property('_studioLocaleSources') or {}
        source = tracked.get('header:' + str(index.column()), ('', ''))[0]
        if source in ('Enabled', 'Resolution', 'Change', 'Action', 'Reviewed', 'Selection',
                      'Type', 'Local status', 'Available domains', 'Status', 'Annotated', 'Category'):
            option.text = (', '.join(tr(part.strip()) for part in option.text.split(','))
                           if source == 'Available domains' else tr(option.text))


class LanguageManager(QtCore.QObject):
    changed = QtCore.Signal(str)

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        app.setAttribute(QtCore.Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
        self.language = 'en'
        self.pending = False
        self.refreshing = False
        self.stopping = False
        self.cache = {}
        print(f'[Language 1/2] Input file: {CATALOG}', flush=True)
        print('Output files: None (translation catalog in memory)', flush=True)
        try:
            payload = json.loads(CATALOG.read_text(encoding='utf-8'))
            if not isinstance(payload, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in payload.items()):
                raise ValueError('Invalid Taiwan Traditional Chinese catalog')
        except (OSError, ValueError) as error:
            print(f'[Language] Translation catalog unavailable: {error}; using English', flush=True)
            payload = {}
        self.catalog = payload
        self.patterns = []
        for source, target in payload.items():
            if not re.search(r'(?<!\{)\{[a-zA-Z_]\w*\}(?!\})', source):
                continue
            regex = ''
            names = []
            for literal, name, spec, conversion in string.Formatter().parse(source):
                regex += re.escape(literal)
                if name is not None:
                    if name in names:
                        regex += '(?P=' + name + ')'
                    else:
                        regex += '(?P<' + name + '>.+?)'
                        names.append(name)
            self.patterns.append((re.compile(regex, re.S), target))
        self.qt_translator = QtCore.QTranslator(self)
        qt_path = QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.LibraryPath.TranslationsPath)
        self.qt_translation_available = self.qt_translator.load('qtbase_zh_TW', qt_path)
        app.installEventFilter(self)
        app.aboutToQuit.connect(self.shutdown)
        atexit.register(self.shutdown)
        print(f'[Language 2/2] Ready: {len(payload)} Taiwan translations', flush=True)

    def translate(self, text):
        if self.language == 'en' or not text:
            return text
        if text in self.cache:
            return self.cache[text]
        result = self.catalog.get(text)
        if result is None:
            for separator in (' → ', ' / '):
                parts = text.split(separator)
                if len(parts) > 1 and parts[0] in self.catalog:
                    translated_parts = [self.translate(part) for part in parts]
                    if all(part in self.catalog or value != part for part, value in zip(parts, translated_parts)):
                        result = separator.join(translated_parts)
                        break
        if result is None:
            for pattern, target in self.patterns:
                match = pattern.fullmatch(text)
                if match:
                    values = match.groupdict()
                    # Only typed UI categories are translated inside templates.
                    # Names, paths, user notes, formulas and IDs remain literal.
                    for name in ('domain', 'kind', 'category', 'scope', 'state'):
                        if name in values:
                            values[name] = self.translate(values[name])
                    if 'fields' in values:
                        values['fields'] = ', '.join(self.translate(part.strip()) for part in values['fields'].split(','))
                    result = target.format_map(values)
                    break
        if result is None and '\n' in text:
            result = '\n'.join(self.translate(line) for line in text.split('\n'))
        if result is None:
            progress = re.fullmatch(r'\[([^\]]+)\](.*)', text, re.S)
            if progress:
                stage = progress.group(1)
                numbered = re.fullmatch(r'(.+?) (\d+/\d+)(.*)', stage)
                if numbered:
                    stage = self.translate(numbered.group(1)) + ' ' + numbered.group(2) + self.translate(numbered.group(3))
                else:
                    stage = self.translate(stage)
                result = '[' + stage + ']' + self.translate(progress.group(2))
        if result is None and re.search(r'</?[a-zA-Z][^>]*>', text):
            result = translate_html(text)
        if result is None and text.strip() != text:
            stripped = text.strip()
            result = text.replace(stripped, self.translate(stripped), 1) if stripped else text
        if result is None:
            result = text
        if len(self.cache) < 20000:
            self.cache[text] = result
        return result

    def set_language(self, selected):
        if selected not in LANGUAGES or (selected == 'zh_TW' and not self.catalog):
            selected = 'en'
        if selected != self.language:
            self.language = selected
            self.cache.clear()
            if selected == 'zh_TW' and self.qt_translation_available:
                self.app.installTranslator(self.qt_translator)
            else:
                self.app.removeTranslator(self.qt_translator)
            self.changed.emit(selected)
            for widget in self.app.allWidgets():
                if isinstance(widget, LocalizedTextBrowser):
                    widget.retranslate()
        self.refresh_all()

    def eventFilter(self, obj, event):
        if self.stopping or QtCore.QCoreApplication.closingDown():
            return False
        if not self.refreshing and event.type() in (QtCore.QEvent.Type.Show, QtCore.QEvent.Type.Polish,
                QtCore.QEvent.Type.LayoutRequest, QtCore.QEvent.Type.ActionAdded,
                QtCore.QEvent.Type.ActionChanged, QtCore.QEvent.Type.WindowTitleChange,
                QtCore.QEvent.Type.LanguageChange):
            if not self.pending:
                self.pending = True
                QtCore.QTimer.singleShot(0, self.refresh_all)
        return False

    def property_text(self, obj, key, getter, setter):
        current = getter()
        if not isinstance(current, str) or not current:
            return
        # Store on the C++ QObject: temporary PySide QAction wrappers can expire.
        tracked = obj.property('_studioLocaleSources') or {}
        source, last = tracked.get(key, (current, current))
        if current != last:
            source = current
        translated = self.translate(source)
        if (key == 'text' and isinstance(obj, (QtGui.QAction, QtWidgets.QAbstractButton))) or key.startswith('tab:'):
            translated = translated.replace('ATT&CK', 'ATT&&CK')
        if translated != current:
            setter(translated)
        tracked[key] = (source, translated)
        obj.setProperty('_studioLocaleSources', tracked)

    def refresh_widget(self, widget):
        if not isinstance(widget, QtWidgets.QMenu):
            self.property_text(widget, 'title', widget.windowTitle, widget.setWindowTitle)
        self.property_text(widget, 'tooltip', widget.toolTip, widget.setToolTip)
        self.property_text(widget, 'statusTip', widget.statusTip, widget.setStatusTip)
        self.property_text(widget, 'accessibleName', widget.accessibleName, widget.setAccessibleName)
        self.property_text(widget, 'accessibleDescription', widget.accessibleDescription, widget.setAccessibleDescription)
        if isinstance(widget, (QtWidgets.QLabel, QtWidgets.QAbstractButton)):
            self.property_text(widget, 'text', widget.text, widget.setText)
        if isinstance(widget, QtWidgets.QGroupBox):
            self.property_text(widget, 'group', widget.title, widget.setTitle)
        if isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            self.property_text(widget, 'placeholder', widget.placeholderText, widget.setPlaceholderText)
        for action in widget.actions():
            self.property_text(action, 'text', action.text, action.setText)
            self.property_text(action, 'tooltip', action.toolTip, action.setToolTip)
            self.property_text(action, 'statusTip', action.statusTip, action.setStatusTip)
        if isinstance(widget, QtWidgets.QTabBar):
            for index in range(widget.count()):
                identity = widget.tabData(index)
                if widget.property('documentTabs') and identity not in ('__manual__', '__details__'):
                    continue
                key = 'tab:' + str(identity if identity is not None else index)
                self.property_text(widget, key, lambda i=index: widget.tabText(i), lambda text, i=index: widget.setTabText(i, text))
        if isinstance(widget, QtWidgets.QComboBox) and not widget.property('languageDelegate'):
            # Paint translated choices while currentText/currentData remain canonical.
            widget.setItemDelegate(TranslatedChoiceDelegate(widget))
            if not widget.isEditable():
                widget.setLabelDrawingMode(QtWidgets.QComboBox.LabelDrawingMode.UseDelegate)
            widget.setProperty('languageDelegate', True)
        if isinstance(widget, QtWidgets.QTableWidget):
            for index in range(widget.columnCount()):
                item = widget.horizontalHeaderItem(index)
                if item is not None:
                    with QtCore.QSignalBlocker(widget):
                        self.property_text(widget, 'header:' + str(index), item.text, item.setText)
            if not widget.property('languageTableDelegate'):
                widget.setItemDelegate(TranslatedTableDelegate(widget))
                widget.setProperty('languageTableDelegate', True)
        if isinstance(widget, QtWidgets.QTreeWidget):
            item = widget.headerItem()
            for index in range(widget.columnCount()):
                self.property_text(widget, 'header:' + str(index), lambda i=index: item.text(i), lambda text, i=index: item.setText(i, text))
        widget.update()

    @QtCore.Slot()
    def refresh_all(self):
        self.pending = False
        if self.refreshing or self.stopping:
            return
        self.refreshing = True
        try:
            for widget in self.app.allWidgets():
                try:
                    self.refresh_widget(widget)
                except RuntimeError:
                    pass  # A dialog may have been deleted since allWidgets().
        finally:
            self.refreshing = False

    def shutdown(self):
        self.stopping = True
        try:
            self.app.removeEventFilter(self)
        except RuntimeError:
            pass


def language_manager():
    global _manager
    app = QtWidgets.QApplication.instance()
    if _manager is None:
        _manager = LanguageManager(app)
    return _manager


class LanguageWorkspace:
    def init_language(self):
        self.language_manager = language_manager()
        selected = self.ui_settings.value('interface/language', 'en')
        self.language_manager.set_language(selected)
        self.language_manager.changed.connect(self.language_changed)

    def add_language_menu(self, menu):
        language_menu = menu.addMenu('Language')
        group = QtGui.QActionGroup(self)
        group.setExclusive(True)
        self.language_actions = {}
        for code, label in (('en', 'English'), ('zh_TW', '繁體中文（臺灣）')):
            action = language_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(code == language())
            action.triggered.connect(lambda checked=False, value=code: self.change_language(value))
            group.addAction(action)
            self.language_actions[code] = action

    def change_language(self, selected):
        self.operation_report(f'Input translation file: {CATALOG}')
        self.operation_report(f'Input/output settings file: {self.settings_path}')
        self.operation_report('[Language setting 1/3] Validating requested language', 0, 3)
        if selected not in LANGUAGES:
            self.operation_report('[Language setting 3/3] Unsupported language; previous preference retained', 3, 3)
            return False
        if selected == 'zh_TW' and not self.language_manager.catalog:
            self.operation_report('[Language setting 3/3] Translation catalog unavailable; English retained', 3, 3)
            self.language_changed(language())
            return False
        self.operation_report('[Language setting 2/3] Saving interface preference', 1, 3)
        self.ui_settings.setValue('interface/language', selected)
        self.ui_settings.sync()
        if self.ui_settings.status() != QtCore.QSettings.Status.NoError:
            self.operation_report('[Language setting 3/3] Could not save preference', 3, 3)
            self.language_changed(language())
            return False
        self.language_manager.set_language(selected)
        self.operation_report('[Language setting 3/3] Interface and manual updated', 3, 3)
        return True

    def language_changed(self, selected):
        for code, action in getattr(self, 'language_actions', {}).items():
            action.setChecked(code == selected)
        if getattr(self, 'manual_page', None) is not None:
            self.manual_page.retranslate_manual()
