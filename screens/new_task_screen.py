from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import QListWidgetItem, QFileDialog, QRadioButton, QPushButton, QListWidget, QLabel, QCheckBox, \
    QLineEdit, QVBoxLayout, QDialog, QMessageBox, QButtonGroup
import pandas as pd
import json
import os
import shutil
import uuid
import traceback

from models import Task

class LoadFileThread(QThread):
    """
    Thread class to load data from a file (CSV or JSON) in the background.
    Emits a signal containing the loaded data when done.
    """
    data_signal = pyqtSignal(object)

    def __init__(self, file_path, is_csv):
        super().__init__()
        self.file_path = file_path
        self.is_csv = is_csv

    def run(self):
        """Load data from a CSV or JSON file and emit the data as a signal."""
        if self.is_csv:
            data = pd.read_csv(self.file_path, dtype=str)
        else:  # json file
            with open(self.file_path, 'r') as f:
                data = json.load(f)
        self.data_signal.emit(data)


class SaveTaskThread(QThread):
    """
    Thread class to save a task to the database and move relevant files to a new directory in the background.
    Emits a signal when the task is saved successfully or an error occurs.
    """
    task_saved_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, Session, task_directory, file_path, new_file_path, synonyms_file_path, task_uuid, task,
                 selected_field, label_column_name):
        super().__init__()
        self.Session = Session
        self.task_directory = task_directory
        self.file_path = file_path
        self.new_file_path = new_file_path
        self.synonyms_file_path = synonyms_file_path
        self.task_uuid = task_uuid
        self.task = task
        self.selected_field = selected_field
        self.label_column_name = label_column_name

    def run(self):
        """
        Save a task to the database, move data and synonym files to a new directory,
        and emit a signal indicating the task is saved or an error has occurred.
        """
        os.makedirs(self.task_directory, exist_ok=True)

        session = None
        try:
            df = pd.read_csv(self.file_path)
            df = df[[self.selected_field]]
            df[self.label_column_name] = None
            df.to_csv(self.new_file_path, index=False)

            shutil.copyfile(self.synonyms_file_path, os.path.join(self.task_directory, 'synonyms.json'))

            new_task = Task(
                task_name=self.task['task_name'],
                file_path=self.new_file_path,
                labels=",".join(self.task['labels']),
                label_column_name=self.task['label_column_name'],
                synonyms_file_path=os.path.join(self.task_directory, 'synonyms.json'),
                single_class=self.task['single_class'],
                field_to_label=self.task['field_to_label'],
                task_uuid=self.task_uuid
            )

            session = self.Session()
            session.add(new_task)
            session.commit()

            self.task_saved_signal.emit()

        except Exception as e:
            if os.path.exists(self.task_directory):
                shutil.rmtree(self.task_directory)
            if session is not None:
                session.rollback()
            self.error_signal.emit(str(e))

        finally:
            if session is not None:
                session.close()
class NewTaskDialog(QDialog):
    """Dialog for creating a new task."""
    task_saved = pyqtSignal()

    def __init__(self, parent=None, Session=None):
        super().__init__(parent)
        self.Session = Session
        self.load_file_thread = None
        self.save_task_thread = None

        layout = QVBoxLayout()
        # Add elements to the layout here

        self.setLayout(layout)

    def on_add_label_button_clicked(self):
        """Add a new label to the labels list widget."""
        label = self.labels_edit.text()
        self.labels_list_widget.addItem(label)
        self.labels_edit.clear()

    def on_file_path_button_clicked(self):
        """Open a file dialog to select a CSV file and start the LoadFileThread."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.file_path_edit.setText(file_path)
            self.load_file_thread = LoadFileThread(file_path, is_csv=True)
            self.load_file_thread.data_signal.connect(self.on_csv_loaded)
            self.load_file_thread.start()

    def on_csv_loaded(self, df):
        """Load the column names into the field_to_label_list_widget when the CSV file is loaded."""
        column_names = df.columns.tolist()
        self.field_to_label_list_widget.clear()
        for column_name in column_names:
            radio_btn = QRadioButton(column_name)
            radio_btn.setObjectName(column_name)
            self.field_to_label_group.addButton(radio_btn)
            list_item = QListWidgetItem(self.field_to_label_list_widget)
            self.field_to_label_list_widget.setItemWidget(list_item, radio_btn)

    def on_synonyms_file_path_button_clicked(self):
        """Open a file dialog to select a JSON file and start the LoadFileThread."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.synonyms_file_path_edit.setText(file_path)
            self.load_file_thread = LoadFileThread(file_path, is_csv=False)
            self.load_file_thread.data_signal.connect(self.load_labels_from_json)
            self.load_file_thread.start()

    def load_labels_from_json(self, data):
        """Load the labels into the labels_list_widget when the JSON file is loaded."""
        labels = list(data.keys())
        for label in labels:
            self.labels_list_widget.addItem(label)

    def on_save_button_clicked(self):
        """Save the task when the 'Save' button is clicked."""
        task_name = self.task_name_edit.text()
        file_path = self.file_path_edit.text()

        labels = [self.labels_list_widget.item(i).text() for i in range(self.labels_list_widget.count())]

        label_column_name = self.label_column_name_edit.text()
        synonyms_file_path = self.synonyms_file_path_edit.text()

        single_class = True if not self.single_class_checkbox.isChecked() else False

        selected_field_button = self.field_to_label_group.checkedButton()
        # Check if a field has been selected
        if not selected_field_button:
            # If no field has been selected, show a warning dialog and return
            QMessageBox.warning(self, "No field selected", "Please select a field before saving.")
            return

        selected_field = selected_field_button.text()

        # Generate a UUID for the task
        task_uuid = str(uuid.uuid4())

        # Create a new directory for the task
        task_directory = os.path.join(os.getcwd(), 'tasks', task_uuid)

        # Define the path for the new CSV file in the task's directory
        new_file_path = os.path.join(task_directory, 'data.csv')

        # Copy the synonyms file to the task's directory
        new_synonyms_file_path = os.path.join(task_directory, 'synonyms.json')

        task = {
            'task_name': task_name,
            'file_path': new_file_path,
            'labels': labels,
            'label_column_name': label_column_name,
            'synonyms_file_path': new_synonyms_file_path,
            'single_class': single_class,
            'field_to_label': selected_field,
            'task_directory': task_directory,
            'task_uuid': task_uuid
        }

        self.save_task_thread = SaveTaskThread(self.Session, task_directory, file_path, new_file_path,
                                               synonyms_file_path,
                                               task_uuid, task, selected_field, label_column_name)
        self.save_task_thread.error_signal.connect(self.on_task_save_error)
        self.save_task_thread.task_saved_signal.connect(self.on_task_saved)
        self.save_task_thread.start()

    def on_task_saved(self):
        """Close the dialog when the task is saved."""
        self.task_saved.emit()
        self.close()

    def on_task_save_error(self, error_message):
        """Show an error message when an error occurs while saving the task."""
        QMessageBox.critical(self, "Error", "Failed to save task:\n\n" + error_message)