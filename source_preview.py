"""Mouse-only source-result previews; no document/model mutation. Flow: README.md."""
from PySide6 import QtCore, QtGui

PREVIEW_COLOR = '#00e5ff'


def draw_source_preview(painter, rect, kind):
    if not kind: return
    painter.save()
    pen = QtGui.QPen(QtGui.QColor(PREVIEW_COLOR),2)
    if kind == 'family': pen.setStyle(QtCore.Qt.PenStyle.DashLine)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    painter.drawRect(rect.adjusted(1,1,-2,-2))
    painter.restore()


class SourceResultHover(QtCore.QObject):
    """One view owns its preview; delayed leave events cannot clear another view."""
    def __init__(self, view, preview, clear):
        super().__init__(view)
        self.view, self.preview, self.clear_callback = view, preview, clear
        view.setMouseTracking(True)
        view.viewport().setMouseTracking(True)
        view.installEventFilter(self)
        view.viewport().installEventFilter(self)
        view.verticalScrollBar().valueChanged.connect(self.clear)
        view.horizontalScrollBar().valueChanged.connect(self.clear)
        model = view.model()
        for name in ('modelReset','layoutChanged','rowsRemoved','rowsInserted','dataChanged'):
            getattr(model,name).connect(self.clear)
        view.clicked.connect(self.clear)
        view.activated.connect(self.clear)

    def clear(self, *args):
        self.clear_callback(self)

    def eventFilter(self, watched, event):
        kind = event.type()
        # Native destruction also delivers events. Do not ask a partially
        # destroyed QAbstractItemView for its viewport on those events.
        if kind == QtCore.QEvent.Type.MouseMove and watched is self.view.viewport():
            index = self.view.indexAt(event.position().toPoint())
            if index.isValid(): self.preview(index,self)
            else: self.clear()
        elif kind in (QtCore.QEvent.Type.Leave,QtCore.QEvent.Type.Hide,QtCore.QEvent.Type.Close,
                      QtCore.QEvent.Type.FocusOut,QtCore.QEvent.Type.WindowDeactivate,
                      QtCore.QEvent.Type.Wheel,QtCore.QEvent.Type.MouseButtonPress,QtCore.QEvent.Type.KeyPress):
            self.clear()
        return False
