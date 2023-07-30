import json
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Task
from screens.new_task_screen import NewTaskDialog, LoadFileThread, SaveTaskThread


class TestNewTaskDialog:


    @pytest.fixture(scope='function', autouse=True)
    def setup_dialog(self, qtbot):
        self.engine = create_engine('sqlite:///:memory:')
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()
        self.dialog = NewTaskDialog(Session=self.Session)
        qtbot.addWidget(self.dialog)

        yield

        # Close the session and drop all tables after each test
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_add_label_button_click(self, qtbot):
        # Write the label to be added in the QLineEdit
        self.dialog.labels_edit.setText('label1')

        # Simulate a click event on the 'Add Label' button
        qtbot.mouseClick(self.dialog.add_label_btn, QtCore.Qt.MouseButton.LeftButton)

        # Check if the label has been added to the QListWidget
        assert self.dialog.labels_list_widget.count() == 1
        assert self.dialog.labels_list_widget.item(0).text() == 'label1'

    def test_file_path_button_click(self, qtbot):
        # Mock QFileDialog.getOpenFileName to return a predetermined file path
        with patch.object(QFileDialog, 'getOpenFileName', return_value=('/path/to/file.csv', 'CSV Files (*.csv)')):
            # Simulate a click event on the file path button
            qtbot.mouseClick(self.dialog.file_path_button, QtCore.Qt.MouseButton.LeftButton)

        # Check if the file path has been written to the QLineEdit
        assert self.dialog.file_path_edit.text() == '/path/to/file.csv'

    def test_synonyms_file_path_button_click(self, qtbot):
        # Mock QFileDialog.getOpenFileName to return a predetermined file path
        with patch.object(QFileDialog, 'getOpenFileName',
                          return_value=('/path/to/synonyms.json', 'JSON Files (*.json)')):
            # Simulate a click event on the synonyms file path button
            qtbot.mouseClick(self.dialog.synonyms_file_path_button, QtCore.Qt.MouseButton.LeftButton)

        # Check if the synonyms file path has been written to the QLineEdit
        assert self.dialog.synonyms_file_path_edit.text() == '/path/to/synonyms.json'

    def test_save_button_click(self, qtbot):
        # Mock necessary methods and fill the dialog with necessary data to save a task
        # Here you might need to patch more methods or even add a task to the database depending on your implementation
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes), \
                patch('screens.new_task_screen.SaveTaskThread'):
            self.dialog.task_name_edit.setText('Task 1')
            self.dialog.file_path_edit.setText('/path/to/file.csv')
            self.dialog.synonyms_file_path_edit.setText('/path/to/synonyms.json')
            self.dialog.labels_edit.setText('label1')
            self.dialog.labels_list_widget.addItem('label1')
            self.dialog.label_column_name_edit.setText('label')
            self.dialog.single_class_checkbox.setChecked(True)
            self.dialog.field_to_label_list_widget.addItem('field')

            # Simulate a click event on the 'Save' button
            qtbot.mouseClick(self.dialog.save_btn, QtCore.Qt.MouseButton.LeftButton)

    def test_on_task_saved(self, qtbot):
        # Mock the close method
        self.dialog.close = MagicMock()

        # Emit task_saved signal
        self.dialog.on_task_saved("Task 1")

        # Check if the dialog was closed
        self.dialog.close.assert_called_once()

    def test_empty_file_path(self, qtbot):
        # Set all fields except for file path
        self.dialog.task_name_edit.setText('Task 1')
        self.dialog.labels_edit.setText('label1')
        self.dialog.label_column_name_edit.setText('label')
        self.dialog.field_to_label_list_widget.addItem('field')

        # Mock the QMessageBox to return 'Ok'
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Ok):
            # Click save button
            qtbot.mouseClick(self.dialog.save_btn, Qt.MouseButton.LeftButton)

            # Check if error message box is displayed
            QMessageBox.exec.assert_called_once()

    def test_empty_labels(self, qtbot):
        # Set all fields except for labels
        self.dialog.task_name_edit.setText('Task 1')
        self.dialog.file_path_edit.setText('/path/to/file')
        self.dialog.label_column_name_edit.setText('label')
        self.dialog.field_to_label_list_widget.addItem('field')

        # Mock the QMessageBox to return 'Ok'
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Ok):
            # Click save button
            qtbot.mouseClick(self.dialog.save_btn, Qt.MouseButton.LeftButton)

            # Check if error message box is displayed
            QMessageBox.exec.assert_called_once()

    def test_empty_label_column_name(self, qtbot):
        # Set all fields except for label column name
        self.dialog.task_name_edit.setText('Task 1')
        self.dialog.file_path_edit.setText('/path/to/file')
        self.dialog.labels_edit.setText('label1,label2')
        self.dialog.field_to_label_list_widget.addItem('field')

        # Mock the QMessageBox to return 'Ok'
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Ok):
            # Click save button
            qtbot.mouseClick(self.dialog.save_btn, Qt.MouseButton.LeftButton)

            # Check if error message box is displayed
            QMessageBox.exec.assert_called_once()

    def test_no_field_selected(self, qtbot):
        # Set all fields and do not select a field to label
        self.dialog.task_name_edit.setText('Task 1')
        self.dialog.file_path_edit.setText('/path/to/file')
        self.dialog.labels_edit.setText('label1,label2')
        self.dialog.label_column_name_edit.setText('label')

        # Mock the QMessageBox to return 'Ok'
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Ok):
            # Click save button
            qtbot.mouseClick(self.dialog.save_btn, Qt.MouseButton.LeftButton)

            # Check if error message box is displayed
            QMessageBox.exec.assert_called_once()




class TestLoadFileThread:

    def test_load_csv(self):
        file_path = '/fixtures/dummy.csv'

        # Assume we have the following data in the CSV file
        data = pd.DataFrame({
            'column1': ['a', 'b', 'c'],
            'column2': ['d', 'e', 'f']
        })

        # Save the DataFrame to a CSV file
        data.to_csv(file_path, index=False)

        # Create and start the LoadFileThread
        load_file_thread = LoadFileThread(file_path, is_csv=True)

        # Connect a slot to the data_signal to capture the emitted data
        load_file_thread.data_signal.connect(self.slot)
        load_file_thread.start()

        # Wait for the thread to finish
        load_file_thread.wait()

        # Check if the emitted data is the same as the original data
        pd.testing.assert_frame_equal(self.emitted_data, data)

    def test_load_json(self):
        file_path = '/fixtures/dummy.json'

        # Assume we have the following data in the JSON file
        data = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }

        # Save the data to a JSON file
        with open(file_path, 'w') as f:
            json.dump(data, f)

        # Create and start the LoadFileThread
        load_file_thread = LoadFileThread(file_path, is_csv=False)

        # Connect a slot to the data_signal to capture the emitted data
        load_file_thread.data_signal.connect(self.slot)
        load_file_thread.start()

        # Wait for the thread to finish
        load_file_thread.wait()

        # Check if the emitted data is the same as the original data
        assert self.emitted_data == data

    def slot(self, data):
        self.emitted_data = data

class TestSaveTaskThread:
    @pytest.fixture(scope='function', autouse=True)
    def setup_thread(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.session = self.Session()

        self.task = {
            'task_name': 'Task 1',
            'file_path': 'fixtures/dummy.csv',
            'synonyms_file_path': 'fixtures/dummy.json',
            'labels': ['label1', 'label2'],
            'label_column_name': 'label',
            'single_class': True,
            'selected_field': 'column1',
            'task_directory': 'fixtures/',
            'task_uuid': 'unique-task-uuid'
        }

        yield

        # Close the session and drop all tables after each test
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_save_task(self):
        save_task_thread = SaveTaskThread(self.Session, self.task)
        save_task_thread.task_saved_signal.connect(self.slot)
        save_task_thread.run()
        save_task_thread.wait()

        session = self.Session()
        task = session.query(Task).filter_by(task_uuid=self.task['task_uuid']).first()
        assert task is not None
        assert task.task_name == self.task['task_name']
        assert task.labels == ','.join(self.task['labels'])
        assert task.label_column_name == self.task['label_column_name']
        assert task.single_class == self.task['single_class']
        assert task.field_to_label == self.task['selected_field']
        assert task.task_uuid == self.task['task_uuid']
        session.close()

    def test_save_task_with_error(self):
        self.task['file_path'] = '/path/to/non/existent/file.csv'  # This file does not exist, should raise an error
        save_task_thread = SaveTaskThread(self.Session, self.task)
        save_task_thread.error_signal.connect(self.slot)
        save_task_thread.run()
        save_task_thread.wait()

        assert hasattr(self, 'emitted_data')  # Check if 'emitted_data' attribute exists
        if hasattr(self, 'emitted_data'):
            assert isinstance(self.emitted_data, str)  # The emitted data should be the error message
            assert 'No such file or directory' in self.emitted_data

    def slot(self, data):
        print(data)
        self.emitted_data = data
