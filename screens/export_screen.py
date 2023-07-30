import os
import pandas as pd
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QPushButton, QFileDialog, QLineEdit, QLabel
from models import Task
from PyQt6.QtCore import QTimer

class ExportWindow(QDialog):
    def __init__(self, Session, task_uuid):
        super().__init__()
        self.Session = Session
        self.task_uuid = task_uuid
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Add radio buttons for export options
        self.all_radio_btn = QRadioButton("Export all rows", checked=True)
        self.layout.addWidget(self.all_radio_btn)

        self.labelled_radio_btn = QRadioButton("Export only labelled rows")
        self.layout.addWidget(self.labelled_radio_btn)

        # Add a button to start the export process
        export_button = QPushButton("Export")
        export_button.clicked.connect(self.export_data)
        self.layout.addWidget(export_button)

    def export_data(self):
        # Open a dialog for the user to select the export file path
        file_path, _ = QFileDialog.getSaveFileName(self, "Export File", "", "CSV Files (*.csv)")

        if file_path:
            # Export the labelled samples to the selected file
            session = self.Session()
            task = session.query(Task).filter_by(task_uuid=self.task_uuid).first()
            data = pd.read_csv(os.path.join('tasks', task.task_uuid, 'data.csv'))

            # Only export rows where the label column has a value, if the labelled_radio_btn is checked
            if self.labelled_radio_btn.isChecked():
                data = data[data[task.label_column_name].notna()]

            data.to_csv(file_path, index=False)

            session.close()

            # Close the export window and show the "Export completed" window
            self.close()
            self.completed_window = ExportCompletedWindow()
            self.completed_window.show()

class ExportCompletedWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel("Export completed"))

        # Close the window after 1 second
        QTimer.singleShot(1000, self.close)