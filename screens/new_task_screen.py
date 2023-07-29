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
    data_signal = pyqtSignal(object)

    def __init__(self, file_path, is_csv):
        QThread.__init__(self)
        self.file_path = file_path
        self.is_csv = is_csv

    def run(self):
        if self.is_csv:
            data = pd.read_csv(self.file_path, dtype=str)
        else:  # json file
            with open(self.file_path, 'r') as f:
                data = json.load(f)
        self.data_signal.emit(data)


class SaveTaskThread(QThread):
    task_saved_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, Session, task_directory, file_path, new_file_path, synonyms_file_path, task_uuid, task,
                 selected_field, label_column_name):
        QThread.__init__(self)
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
        print("Running SaveTaskThread...")
        os.makedirs(self.task_directory, exist_ok=True)
        print(f"Created task directory: {self.task_directory}")

        session = None
        try:
            # Load the CSV file into a pandas DataFrame
            df = pd.read_csv(self.file_path)

            # Keep only the selected column
            df = df[[self.selected_field]]

            # Add a new column for the labels, initially set to None
            df[self.label_column_name] = None

            # Save the DataFrame to a new CSV file in the task's directory
            df.to_csv(self.new_file_path, index=False)

            # Copy synonyms file to the task directory
            shutil.copyfile(self.synonyms_file_path, os.path.join(self.task_directory, 'synonyms.json'))
            print(f"Copied synonyms file to: {os.path.join(self.task_directory, 'synonyms.json')}")

            # Create new Task object
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

            # Open new session
            session = self.Session()
            session.add(new_task)
            session.commit()
            print("Saved task to database")

            self.task_saved_signal.emit()
            print("Finished running SaveTaskThread.")

        except Exception as e:
            # Remove task directory if saving task fails
            if os.path.exists(self.task_directory):
                shutil.rmtree(self.task_directory)

            # Rollback if session is defined
            if session is not None:
                session.rollback()
            print("Failed to save task to database")
            print(e)
            self.error_signal.emit(str(e))  # emit error signal with the exception message

        finally:
            if session is not None:
                session.close()  # Close the session


class NewTaskDialog(QDialog):
    task_saved = pyqtSignal()

    def __init__(self, parent=None, Session=None):
        super().__init__(parent)
        self.Session = Session
        self.load_file_thread = None
        self.save_task_thread = None
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Task Name"))
        self.task_name_edit = QLineEdit()
        layout.addWidget(self.task_name_edit)

        layout.addWidget(QLabel("CSV File Path"))
        self.file_path_edit = QLineEdit()
        layout.addWidget(self.file_path_edit)

        self.file_path_button = QPushButton("...")
        self.file_path_button.clicked.connect(self.on_file_path_button_clicked)
        layout.addWidget(self.file_path_button)

        layout.addWidget(QLabel("Synonyms File Path"))
        self.synonyms_file_path_edit = QLineEdit()
        layout.addWidget(self.synonyms_file_path_edit)

        self.synonyms_file_path_button = QPushButton("...")
        self.synonyms_file_path_button.clicked.connect(self.on_synonyms_file_path_button_clicked)
        layout.addWidget(self.synonyms_file_path_button)

        self.field_to_label_group = QButtonGroup(self)

        layout.addWidget(QLabel("Labels"))
        self.labels_edit = QLineEdit()
        layout.addWidget(self.labels_edit)

        add_label_btn = QPushButton('+')
        add_label_btn.clicked.connect(self.on_add_label_button_clicked)
        layout.addWidget(add_label_btn)

        self.labels_list_widget = QListWidget()
        layout.addWidget(self.labels_list_widget)

        layout.addWidget(QLabel("Label Column Name"))
        self.label_column_name_edit = QLineEdit()
        layout.addWidget(self.label_column_name_edit)

        self.single_class_checkbox = QCheckBox("Single Class")
        layout.addWidget(self.single_class_checkbox)

        layout.addWidget(QLabel("Field to Label"))
        self.field_to_label_list_widget = QListWidget()
        layout.addWidget(self.field_to_label_list_widget)

        save_btn = QPushButton('Save')
        save_btn.clicked.connect(self.on_save_button_clicked)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def on_add_label_button_clicked(self):
        # Get the current label from the line edit
        label = self.labels_edit.text()

        # Add the label to the list widget
        self.labels_list_widget.addItem(label)

        # Clear the line edit
        self.labels_edit.clear()

    def on_file_path_button_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.file_path_edit.setText(file_path)
            self.load_file_thread = LoadFileThread(file_path, is_csv=True)
            self.load_file_thread.data_signal.connect(self.on_csv_loaded)
            self.load_file_thread.start()

    def on_csv_loaded(self, df):
        column_names = df.columns.tolist()
        self.field_to_label_list_widget.clear()
        for column_name in column_names:
            radio_btn = QRadioButton(column_name)
            radio_btn.setObjectName(column_name)
            self.field_to_label_group.addButton(radio_btn)
            list_item = QListWidgetItem(self.field_to_label_list_widget)
            self.field_to_label_list_widget.setItemWidget(list_item, radio_btn)

    def on_synonyms_file_path_button_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)")
        if file_path:
            self.synonyms_file_path_edit.setText(file_path)
            self.load_file_thread = LoadFileThread(file_path, is_csv=False)
            self.load_file_thread.data_signal.connect(self.load_labels_from_json)
            self.load_file_thread.start()

    def load_labels_from_json(self, data):
        labels = list(data.keys())
        for label in labels:
            self.labels_list_widget.addItem(label)

    def on_save_button_clicked(self):
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
        self.task_saved.emit()
        self.close()

    def on_task_save_error(self, error_message):
        QMessageBox.critical(self, "Error", "Failed to save task:\n\n" + error_message)

