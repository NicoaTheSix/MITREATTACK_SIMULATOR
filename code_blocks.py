"""Read-only, collapsed-by-default code panels for native detail pages. Flow: README.md."""
import html
from html.parser import HTMLParser
import math
import re

from PySide6 import QtCore, QtGui, QtWidgets
from localization import LocalizedTextBrowser, language_manager


def code_html(title, text, language='json'):
    """Only presentation markup; the original text is escaped exactly once."""
    return ('<pre data-title="'+html.escape(title,quote=True)+'" data-language="'+html.escape(language,quote=True)+'">'
            +html.escape(text)+'</pre>')


class CollapsibleCodeBlock(QtWidgets.QFrame):
    def __init__(self,title,text,language='json',notify=None,parent=None):
        super().__init__(parent)
        self.code=text
        self.notify=notify or (lambda *args:None)
        self.setObjectName('collapsibleCodeBlock')
        self.setStyleSheet('QFrame#collapsibleCodeBlock {border:1px solid #414141; border-radius:5px; background:#181818;}')
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Maximum)
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(8,6,8,6);layout.setSpacing(6)
        bar=QtWidgets.QHBoxLayout()
        self.toggle=QtWidgets.QToolButton();self.toggle.setText(title);self.toggle.setCheckable(True)
        self.toggle.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self.toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setAccessibleName('Expand or collapse code block');self.toggle.setAccessibleDescription(title)
        self.toggle.setToolTip(title)
        self.toggle.setMinimumWidth(0)
        self.toggle.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        bar.addWidget(self.toggle,1)
        self.language_label=QtWidgets.QLabel(language);bar.addWidget(self.language_label)
        self.copy_button=QtWidgets.QPushButton('Copy');self.copy_button.setAccessibleName('Copy code block')
        self.copy_button.setAccessibleDescription(title);bar.addWidget(self.copy_button)
        layout.addLayout(bar)
        self.editor=QtWidgets.QPlainTextEdit();self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setPlainText(text)
        font=QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.editor.setFont(font)
        self.editor.setStyleSheet('QPlainTextEdit {font-family:"'+font.family()+'"; font-size:13px; padding:8px; background:#181818; border:none;}')
        self.editor.setAccessibleName('Code block content');self.editor.setAccessibleDescription(title)
        self.editor.setMinimumWidth(0)
        lines=max(1,text.count('\n')+1)
        self.editor.setFixedHeight(min(360,max(76,lines*self.editor.fontMetrics().lineSpacing()+32)))
        layout.addWidget(self.editor);self.editor.hide()
        self.toggle.toggled.connect(self.set_expanded)
        self.copy_button.clicked.connect(self.copy_code)
        self.copy_timer=QtCore.QTimer(self);self.copy_timer.setSingleShot(True);self.copy_timer.setInterval(1200)
        self.copy_timer.timeout.connect(self.reset_copy_label)

    def set_expanded(self,expanded):
        self.notify('Input files: None; output files: None (code block visibility in memory)')
        self.notify('[Code block 1/2] Updating expanded state',0,2)
        self.editor.setVisible(expanded)
        self.toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)
        self.updateGeometry()
        self.notify('[Code block 2/2] '+('Expanded' if expanded else 'Collapsed'),2,2)

    def copy_code(self):
        self.notify('Input files: None (original code block in memory); output files: None (system clipboard)')
        self.notify('[Code copy 1/2] Copying complete original text',0,2)
        QtWidgets.QApplication.clipboard().setText(self.code)
        self.copy_button.setText('Copied');language_manager().refresh_widget(self.copy_button)
        self.copy_timer.start()
        self.notify('[Code copy 2/2] Complete',2,2)

    def reset_copy_label(self):
        self.copy_button.setText('Copy');language_manager().refresh_widget(self.copy_button)


class _RichSection(LocalizedTextBrowser):
    """Use the outer scroll area, so text and code panels share one page."""
    def __init__(self,source,parent):
        super().__init__(parent)
        self.setOpenLinks(False);self.setOpenExternalLinks(False)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self.setStyleSheet('QTextBrowser {padding:4px; border:none;}')
        self.document().documentLayout().documentSizeChanged.connect(self.update_height)
        self.setHtml(source)

    def update_height(self,*_):
        margins=self.contentsMargins()
        height=math.ceil(self.document().size().height())+margins.top()+margins.bottom()+2*self.frameWidth()
        if self.height()!=height:self.setFixedHeight(max(1,height))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.update_height()


class _PreAttributes(HTMLParser):
    def __init__(self,tag):
        super().__init__(convert_charrefs=True);self.attributes={};self.feed(tag)

    def handle_starttag(self,tag,attrs):
        self.attributes=dict(attrs)


class CodeDetailView(QtWidgets.QScrollArea):
    """Render trusted page templates; escaped pre content is always plain text."""
    anchorClicked=QtCore.Signal(QtCore.QUrl)

    def __init__(self,notify=None,parent=None):
        super().__init__(parent)
        self.notify=notify;self.blocks=[];self.sections=[]
        self.setWidgetResizable(True);self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body=QtWidgets.QWidget();self.body.setMinimumWidth(0)
        self.body.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Preferred)
        self.content_layout=QtWidgets.QVBoxLayout(self.body);self.content_layout.setContentsMargins(12,10,12,10);self.content_layout.setSpacing(8)
        self.setWidget(self.body)

    def setHtml(self,source):
        self.blocks=[];self.sections=[]
        while self.content_layout.count():
            item=self.content_layout.takeAt(0)
            if item.widget():item.widget().hide();item.widget().deleteLater()
        def rich(text):
            if not text.strip():return
            section=_RichSection(text,self.body);section.anchorClicked.connect(self.anchorClicked.emit)
            self.content_layout.addWidget(section);self.sections.append(section)
        position=0
        for match in re.finditer(r'(<pre\b[^>]*>)(.*?)</pre\s*>',source,re.I|re.S):
            rich(source[position:match.start()])
            attrs=_PreAttributes(match.group(1)).attributes
            block=CollapsibleCodeBlock(attrs.get('data-title','JSON'),html.unescape(match.group(2)),
                attrs.get('data-language','json'),self.notify,self.body)
            self.content_layout.addWidget(block);self.sections.append(block);self.blocks.append(block)
            position=match.end()
        rich(source[position:]);self.content_layout.addStretch(1)
        self.verticalScrollBar().setValue(0)

    def toPlainText(self):
        # Inspection/search retains the full content, including collapsed panels.
        return '\n'.join(section.toggle.text()+'\n'+section.code if isinstance(section,CollapsibleCodeBlock)
            else section.toPlainText() for section in self.sections)
