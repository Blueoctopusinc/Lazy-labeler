import os
import shutil
from models import Task
from .export_screen import ExportWindow
from .labelling_screen import LabelingProjectWindow
from .new_task_screen import NewTaskDialog
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, QMainWindow, QVBoxLayout, QPushButton,
                             QWidget, QLabel, QMessageBox)


class StartWindow(QMainWindow):
    def __init__(self, Session):
        super().__init__()
        self.Session = Session
        self.tasks = []  # List to hold Task objects
        layout = QVBoxLayout()

        # Initialize the table with 0 rows and 5 columns
        self.task_table_widget = QTableWidget(0, 6)
        self.task_table_widget.setHorizontalHeaderLabels(
            ["Task Name", "Labelled", "Created", "Open", "Delete", "Export"])
        self.task_table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.task_table_widget.setSortingEnabled(True)
        self.task_table_widget.verticalHeader().setVisible(False)
        self.task_table_widget.itemDoubleClicked.connect(self.on_task_double_clicked)
        layout.addWidget(self.task_table_widget)

        # Create and add 'New Task' button to the layout
        new_task_btn = QPushButton('New Task')
        new_task_btn.clicked.connect(self.on_new_task_button_clicked)
        layout.addWidget(new_task_btn)

        # Set the layout of the window
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Set the minimum window size
        self.setMinimumSize(800, 600)

        # Load tasks into the table
        self.load_tasks()

    def load_tasks(self):
        """Load tasks from the database and populate the table with task details."""
        self.task_table_widget.setRowCount(0)  # Clear the table
        session = self.Session()
        self.tasks = session.query(Task).all()

        for task in self.tasks:
            row_position = self.task_table_widget.rowCount()
            self.task_table_widget.insertRow(row_position)
            self.task_table_widget.setCellWidget(row_position, 0, QLabel(task.task_name))
            self.task_table_widget.setCellWidget(row_position, 1, QLabel(str(task.labelled_samples)))
            created_at = task.created_at.strftime("%Y-%m-%d %H:%M")
            self.task_table_widget.setCellWidget(row_position, 2, QLabel(created_at))

            # Add 'Open', 'Delete' and 'Export' buttons for each task
            open_button = QPushButton("Open")
            open_button.clicked.connect(lambda checked, task=task: self.on_open_button_clicked(task))
            self.task_table_widget.setCellWidget(row_position, 3, open_button)

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda checked, task=task: self.on_delete_button_clicked(task))
            self.task_table_widget.setCellWidget(row_position, 4, delete_button)

            export_button = QPushButton("Export")
            export_button.clicked.connect(lambda checked, task=task: self.on_export_button_clicked(task))
            self.task_table_widget.setCellWidget(row_position, 5, export_button)

        session.close()

    def on_task_double_clicked(self, item):
        """Open the labeling window for the double-clicked task."""
        task = self.tasks[item.row()]
        self.label_window = LabelingProjectWindow(self.Session, task.task_uuid)
        self.label_window.show()

    def on_new_task_button_clicked(self):
        """Open the 'New Task' dialog."""
        dialog = NewTaskDialog(self, self.Session)
        dialog.task_saved.connect(self.load_tasks)
        dialog.exec()

    def on_delete_button_clicked(self, task):
        """Delete the clicked task after confirmation."""
        confirm_box = QMessageBox()
        confirm_box.setIcon(QMessageBox.Icon.Question)
        confirm_box.setWindowTitle("Confirm Deletion")
        confirm_box.setText(f"Are you sure you want to delete the task '{task.task_name}'?")
        confirm_box.setInformativeText(
            "This will delete the task from the database and all associated files from the disk. This operation cannot be undone.")
        confirm_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_box.setDefaultButton(QMessageBox.StandardButton.No)

        response = confirm_box.exec()

        if response == QMessageBox.StandardButton.Yes:
            # Remove task from database
            session = self.Session()
            session.delete(task)
            session.commit()
            session.close()

            # Remove task files from disk
            task_directory = os.path.join(os.getcwd(), 'tasks', task.task_uuid)
            shutil.rmtree(task_directory, ignore_errors=True)

            # Refresh task list
            self.load_tasks()

    def on_open_button_clicked(self, task):
        """Open the labeling window for the clicked task."""
        self.label_window = LabelingProjectWindow(self.Session, task.task_uuid)
        self.label_window.show()

    def on_export_button_clicked(self, task):
        """Open the export window for the clicked task."""
        self.export_window = ExportWindow(self.Session, task.task_uuid)
        self.export_window.show()