"""Native SVG settings/preview and all-layer Excel export. Workflow: README.md."""
from pathlib import Path
from PySide6 import QtCore, QtWidgets

from layer_analysis import snapshot_document
from navigator_dialogs import IntegrationDialog
from svg_export import DEFAULT_SVG, UNITS
from svg_sizing import PAPER_LABELS, LENGTH_FIELDS, paper_dimensions, custom_orientation, maximum_length
from workbook_exports import export_all_layers_excel


class SvgSettings(QtWidgets.QWidget):
    changed=QtCore.Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.controls={}
        self.last_unit='px'
        self.length_pixels={field: DEFAULT_SVG[field] for field in LENGTH_FIELDS}
        self.custom_pixels=(0, 0)
        self.custom_direction='portrait'
        layout=QtWidgets.QVBoxLayout(self)
        self.tabs=QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)
        basic=QtWidgets.QWidget()
        form=QtWidgets.QFormLayout(basic)
        def combo(field,choices):
            control=QtWidgets.QComboBox()
            for label,value in choices: control.addItem(label,value)
            self.controls[field]=control
            return control
        self.unit=combo('unit',[(u,u) for u in UNITS])
        self.theme=combo('theme',[('Dark','dark'),('Light','light')])
        form.addRow('SVG theme',self.theme)
        hint=QtWidgets.QLabel('SVG theme applies only to this export. Preview and file use the same colors; layer data and application theme stay unchanged.')
        hint.setWordWrap(True)
        form.addRow(hint)
        form.addRow('Units',self.unit)
        self.paper_size=combo('size',PAPER_LABELS)
        form.addRow('Paper size',self.paper_size)
        self.orientation=combo('orientation',[('Portrait','portrait'),('Landscape','landscape')])
        form.addRow('Orientation',self.orientation)
        self.orientation.setEnabled(False)
        page_hint=QtWidgets.QLabel('Presets fix the canvas size. Custom restores your last custom dimensions; with both dimensions set, orientation swaps them. Header and legend settings keep their physical sizes.')
        page_hint.setWordWrap(True)
        form.addRow(page_hint)
        for field,label in (('width','Image width · 0 = Auto'),('height','Image height · 0 = Auto'),
                            ('header_height','Header height · 0 = Auto')):
            form.addRow(label,self.size_control(field))
        form.addRow('Font',combo('font',[(name,name) for name in ('sans-serif','serif','monospace')]))
        form.addRow('Sub-techniques',combo('subtechniques',[
            ('Show all matching children','all'),('Show children expanded when export opened','expanded'),('Show none','none')]))
        border=QtWidgets.QLineEdit(DEFAULT_SVG['cell_border'])
        border.setPlaceholderText('#RRGGBB')
        self.controls['cell_border']=border
        form.addRow('Cell border color',border)
        for field,label in (('show_header','Show header'),('show_about','Show layer name / description'),
                            ('show_domain','Show domain / version'),('show_filters','Show platform / search')):
            control=QtWidgets.QCheckBox(label)
            control.setChecked(True)
            self.controls[field]=control
            form.addRow(control)
        self.tabs.addTab(basic,'Image and header')
        legend_page=QtWidgets.QWidget()
        legend_form=QtWidgets.QFormLayout(legend_page)
        for field,label in (('show_legend','Show legend'),('legend_undocked','Undock legend · may overlap matrix')):
            control=QtWidgets.QCheckBox(label)
            control.setChecked(DEFAULT_SVG[field])
            self.controls[field]=control
            legend_form.addRow(control)
        for field,label in (('legend_x','Legend X'),('legend_y','Legend Y'),('legend_width','Legend width'),
                            ('legend_height','Legend height · 0 = Auto')):
            legend_form.addRow(label,self.size_control(field))
        hint=QtWidgets.QLabel('Docked legends follow the header. An undocked legend stays visible when the header is hidden. '
                              'Positions and sizes use the selected units. A detached legend must fit inside the image. '
                              'Image/header/legend content is scaled to fit; smaller dimensions produce smaller text.')
        hint.setWordWrap(True)
        legend_form.addRow(hint)
        self.tabs.addTab(legend_page,'Legend')
        self.unit.currentIndexChanged.connect(self.change_unit)
        self.paper_size.currentIndexChanged.connect(self.change_paper)
        self.orientation.currentIndexChanged.connect(self.change_orientation)
        for field,control in self.controls.items():
            if field in ('unit', 'size', 'orientation'):
                continue
            if field in LENGTH_FIELDS:
                control.valueChanged.connect(lambda *_, key=field: self.length_changed(key))
                continue
            if isinstance(control,QtWidgets.QComboBox): control.currentIndexChanged.connect(self.changed)
            elif isinstance(control,QtWidgets.QCheckBox): control.toggled.connect(self.changed)
            elif isinstance(control,QtWidgets.QLineEdit): control.textChanged.connect(self.changed)
            else: control.valueChanged.connect(self.changed)

    def size_control(self,field):
        control=QtWidgets.QDoubleSpinBox()
        control.setDecimals(6)
        control.setRange(0,100000)
        control.setValue(DEFAULT_SVG[field])
        self.controls[field]=control
        return control

    def display_lengths(self):
        unit=self.unit.currentData()
        for field in LENGTH_FIELDS:
            control=self.controls[field]
            value=self.length_pixels[field]/UNITS[unit]
            if abs(value-round(value))<1e-9:
                value=round(value)
            with QtCore.QSignalBlocker(control):
                control.setMaximum(maximum_length(unit))
                control.setValue(value)

    def update_page(self):
        custom=self.paper_size.currentData()=='custom'
        for field in ('width', 'height'):
            self.controls[field].setEnabled(custom)
        width, height=self.length_pixels['width'], self.length_pixels['height']
        self.orientation.setEnabled(not custom or bool(width and height))
        if custom:
            value=custom_orientation(width,height,self.orientation.currentData())
            with QtCore.QSignalBlocker(self.orientation):
                self.orientation.setCurrentIndex(self.orientation.findData(value))

    def change_unit(self):
        unit=self.unit.currentData()
        self.display_lengths()
        self.last_unit=unit
        self.changed.emit()

    def change_paper(self):
        size=self.paper_size.currentData()
        if size=='custom':
            self.length_pixels['width'], self.length_pixels['height']=self.custom_pixels
            with QtCore.QSignalBlocker(self.orientation):
                self.orientation.setCurrentIndex(self.orientation.findData(self.custom_direction))
        else:
            self.length_pixels['width'], self.length_pixels['height']=paper_dimensions(size,self.orientation.currentData())
        self.display_lengths()
        self.update_page()
        self.changed.emit()

    def change_orientation(self):
        size=self.paper_size.currentData()
        if size=='custom':
            width, height=self.length_pixels['width'], self.length_pixels['height']
            if width and height and custom_orientation(width,height,self.orientation.currentData())!=self.orientation.currentData():
                self.length_pixels['width'], self.length_pixels['height']=height,width
                self.custom_pixels=(height,width)
            self.custom_direction=self.orientation.currentData()
        else:
            self.length_pixels['width'], self.length_pixels['height']=paper_dimensions(size,self.orientation.currentData())
        self.display_lengths()
        self.update_page()
        self.changed.emit()

    def length_changed(self,field):
        self.length_pixels[field]=self.controls[field].value()*UNITS[self.unit.currentData()]
        if field in ('width','height') and self.paper_size.currentData()=='custom':
            self.custom_pixels=(self.length_pixels['width'],self.length_pixels['height'])
            self.update_page()
            self.custom_direction=self.orientation.currentData()
        self.changed.emit()

    def options(self):
        result={}
        for field,control in self.controls.items():
            if isinstance(control,QtWidgets.QComboBox): value=control.currentData()
            elif isinstance(control,QtWidgets.QCheckBox): value=control.isChecked()
            elif isinstance(control,QtWidgets.QLineEdit): value=control.text().strip()
            else: value=self.length_pixels[field]/UNITS[self.unit.currentData()]
            result[field]=value
        # Preserve the established default output exactly when no options are changed.
        return None if result==DEFAULT_SVG else result


class AllLayersExcelDialog(IntegrationDialog):
    def __init__(self,documents,target,parent):
        super().__init__(parent)
        self.documents=[snapshot_document(doc) for doc in documents]
        self.target=Path(target).expanduser().resolve()
        self.output_path=None
        self.setWindowTitle('Export all open layers to Excel')
        self.resize(740,520)
        layout=QtWidgets.QVBoxLayout(self)
        label=QtWidgets.QLabel(f'Output file: {self.target}')
        label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        hint=QtWidgets.QLabel('One worksheet per open layer, in tab order. Each uses its own saved platform filters, '
                              'states, scores, colors and all matching sub-techniques. Current search text, color hiding '
                              'and combined overlays are not applied. Mixed domains/versions use independent sheets. '
                              'Duplicate or unsupported sheet names are sanitized; full layer names stay in row 1.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        table=QtWidgets.QTableWidget(len(self.documents),2)
        table.setHorizontalHeaderLabels(['Layer','Domain / version'])
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0,QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1,QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        for index,doc in enumerate(self.documents):
            table.setItem(index,0,QtWidgets.QTableWidgetItem(doc.name))
            table.setItem(index,1,QtWidgets.QTableWidgetItem(f'{doc.catalog.domain} v{doc.catalog.version}'))
        self.layers_table=table
        layout.addWidget(table)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.export_button=QtWidgets.QPushButton('Export all layers XLSX')
        self.export_button.clicked.connect(self.export)
        layout.addWidget(self.export_button)
        close=QtWidgets.QPushButton('Cancel / Close')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def export(self):
        if self.worker and self.worker.isRunning(): return
        self.export_button.setEnabled(False)
        self.start_task(lambda notify:export_all_layers_excel(self.documents,self.target,notify),self.complete)
        self.worker.finished.connect(lambda:self.export_button.setEnabled(self.output_path is None))

    def complete(self,path):
        self.output_path=path
        self.report(f'Complete: {path}',4,4)
