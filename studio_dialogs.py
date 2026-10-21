"""Background Studio open/save and session validation dialogs. Workflow: README.md."""
from PySide6 import QtCore, QtWidgets
from navigator_dialogs import IntegrationDialog


class StudioTaskDialog(IntegrationDialog):
    def __init__(self, title, task, parent):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 240)
        self.result_value = None
        self.failure_message = None
        self.task = task
        self.mutating = title == 'Save Studio JSON'
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.close_button = QtWidgets.QPushButton('Close' if self.mutating else 'Cancel / Close')
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        # A save cannot be cancelled between atomic file publication and baseline adoption.
        self.close_button.setEnabled(not self.mutating)
        QtCore.QTimer.singleShot(0, self.run_task)

    def run_task(self):
        if self.closing:
            return
        self.start_task(self.task, self.completed)
        self.worker.finished.connect(self.finished_task)
        self.worker.failed.connect(lambda message: setattr(self, 'failure_message', message))

    def completed(self, value):
        self.result_value = value

    def finished_task(self):
        self.close_button.setEnabled(True)
        if self.result_value is not None and not self.closing:
            self.accept()
        elif self.failure_message:
            self.reject()

    def reject(self):
        if self.mutating and self.worker and self.worker.isRunning():
            return
        if not self.worker:
            self.closing = True
        super().reject()
