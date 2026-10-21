"""Exact catalog object clipboard and hover JSON preview. Workflow: README.md."""
from copy import deepcopy
import json
from PySide6 import QtCore, QtGui, QtWidgets
from attack_catalog import external_id


def object_payload(catalog, domain, key, envelope=False):
    """Wrap the selected raw object; never fabricate a remote TAXII response."""
    obj = catalog.all_objects_by_domain.get(domain,{}).get(key)
    if obj is None:
        raise ValueError('This page has no original STIX object in the current catalog.')
    if not isinstance(obj,dict) or obj.get('id') != key or not isinstance(obj.get('type'),str):
        raise ValueError('Invalid source STIX object.')
    value = deepcopy(obj)
    return {'objects':[value], 'more':False} if envelope else value


def object_json(catalog, domain, key, envelope=False):
    return json.dumps(object_payload(catalog,domain,key,envelope),ensure_ascii=False,indent=2,allow_nan=False)+'\n'


class ObjectCopyBar(QtWidgets.QWidget):
    """Two clipboard formats share a scrollable, non-focusing hover popup."""
    def __init__(self, notify, parent=None):
        super().__init__(parent)
        self.notify, self.context = notify, None
        self.pending_format = False
        self.preview_format = False
        self.json_cache, self.buttons = {}, {}
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(12,4,12,4)
        for envelope,label in ((False,'Copy STIX JSON'),(True,'Copy TAXII envelope')):
            button = QtWidgets.QPushButton(label)
            button.setAccessibleName(label)
            button.clicked.connect(lambda checked=False,value=envelope:self.copy(value))
            row.addWidget(button)
            self.buttons[envelope] = button
        self.identity = QtWidgets.QLabel()
        row.addWidget(self.identity,1)
        self.preview = QtWidgets.QFrame(self,QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint |
                                       QtCore.Qt.WindowType.WindowDoesNotAcceptFocus)
        self.preview.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.preview.setObjectName('stixHoverPreview')
        self.preview.setStyleSheet('#stixHoverPreview {border:1px solid #007acc;}')
        self.preview.resize(540,350)
        layout = QtWidgets.QVBoxLayout(self.preview)
        self.preview_title = QtWidgets.QLabel()
        self.preview_title.setWordWrap(True)
        layout.addWidget(self.preview_title)
        self.preview_text = QtWidgets.QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.preview_text,1)
        self.preview_copy = QtWidgets.QPushButton('Copy complete JSON')
        self.preview_copy.clicked.connect(lambda:self.copy(self.preview_format))
        layout.addWidget(self.preview_copy)
        self.preview.installEventFilter(self)
        self.hover_timer = QtCore.QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(300)
        self.hover_timer.timeout.connect(self.show_preview)
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(250)
        self.hide_timer.timeout.connect(self.hide_if_outside)
        for button in self.buttons.values(): button.installEventFilter(self)
        self.hide()

    def clear_context(self):
        self.context = None
        self.json_cache.clear()
        self.hover_timer.stop()
        self.hide_timer.stop()
        self.preview.hide()
        self.hide()

    def set_context(self,catalog,domain,key):
        self.clear_context()
        obj = catalog.all_objects_by_domain.get(domain,{}).get(key)
        if not obj: return
        self.context = catalog,domain,key
        self.identity.setText((external_id(obj) or obj['type'])+' · v'+catalog.version)
        self.show()

    def content(self,envelope):
        if not self.context: raise ValueError('Select a source object first.')
        if envelope not in self.json_cache:
            self.json_cache[envelope] = object_json(*self.context,envelope=envelope)
        return self.json_cache[envelope]

    def copy(self,envelope=False):
        if not self.context: return False
        self.notify('Input files: None (verified source object in memory); output files: None (system clipboard)',0,0)
        self.notify('[Object Copy 1/2] Serializing complete source JSON',0,2)
        try: text = self.content(envelope)
        except (ValueError,TypeError) as error:
            self.notify('[Object Copy] Failed: '+str(error),1,1)
            return False
        QtWidgets.QApplication.clipboard().setText(text)
        self.notify('[Object Copy 2/2] Complete: '+('TAXII 2.1 envelope' if envelope else 'STIX object')+' copied',2,2)
        return True

    def eventFilter(self, watched, event):
        if watched in self.buttons.values():
            if event.type() == QtCore.QEvent.Type.Enter and self.context:
                self.pending_format = next(value for value,button in self.buttons.items() if button is watched)
                self.hide_timer.stop()
                self.hover_timer.start()
            elif event.type() == QtCore.QEvent.Type.Leave:
                self.hover_timer.stop()
                self.hide_timer.start()
        elif watched is self.preview:
            if event.type() == QtCore.QEvent.Type.Enter: self.hide_timer.stop()
            elif event.type() == QtCore.QEvent.Type.Leave: self.hide_timer.start()
        return super().eventFilter(watched,event)

    def hideEvent(self,event):
        self.hover_timer.stop()
        self.preview.hide()
        super().hideEvent(event)

    def hide_if_outside(self):
        point = QtGui.QCursor.pos()
        inside = self.preview.isVisible() and self.preview.frameGeometry().contains(point)
        inside |= any(button.isVisible() and QtCore.QRect(button.mapToGlobal(QtCore.QPoint()),button.size()).contains(point)
                      for button in self.buttons.values())
        if inside:
            if self.preview.isVisible(): self.hide_timer.start()
        else:
            self.preview.hide()

    def show_preview(self):
        if not self.context or not self.isVisible(): return
        self.notify('Input files: None (source object in memory); output files: None (hover preview)',0,0)
        self.notify('[Object Preview 1/2] Preparing read-only JSON',0,2)
        try: text = self.content(self.pending_format)
        except (ValueError,TypeError) as error:
            self.preview.hide()
            self.notify('[Object Preview] Failed: '+str(error),1,1)
            return
        catalog,domain,key = self.context
        title = 'TAXII 2.1 envelope · local object wrapper' if self.pending_format else 'Original STIX JSON'
        self.preview_title.setText(title+'\n'+key+' · '+domain+' · v'+catalog.version)
        self.preview_format = self.pending_format
        if self.preview_text.toPlainText() != text.rstrip('\n'):
            self.preview_text.setPlainText(text)
            self.preview_text.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
        button = self.buttons[self.pending_format]
        point = button.mapToGlobal(QtCore.QPoint(0,button.height()+4))
        screen = button.screen().availableGeometry()
        self.preview.resize(min(540,screen.width()),min(350,screen.height()))
        point.setX(max(screen.left(),min(point.x(),screen.right()-self.preview.width()+1)))
        point.setY(max(screen.top(),min(point.y(),screen.bottom()-self.preview.height()+1)))
        self.preview.move(point)
        self.preview.show()
        self.hide_timer.start()
        self.notify('[Object Preview 2/2] Ready; scroll to inspect or click to copy complete JSON',2,2)
