from unittest.mock import patch

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QApplication, QMessageBox
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Task, Base
from screens.start_screen import StartWindow


class TestStartWindow:

    @pytest.fixture(scope='function', autouse=True)
    def setup_session(self, qtbot):
        self.engine = create_engine('sqlite:///:memory:')
        self.Session = sessionmaker(bind=self.engine)

        # Create the tasks table in the database
        Base.metadata.create_all(self.engine)

        # Start a new session
        self.session = self.Session()

        # Initialize StartWindow
        self.window = StartWindow(self.Session)
        qtbot.addWidget(self.window)

        yield

        # Close the session and drop all tables after each test
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_load_tasks(self, qtbot):
        # Add tasks to the database
        task1 = Task(task_name="Task 1", file_path="/path/to/file1", labels="label1,label2",
                     label_column_name="label", field_to_label="field", single_class=True, task_uuid="uuid1")
        task2 = Task(task_name="Task 2", file_path="/path/to/file2", labels="label3,label4",
                     label_column_name="label", field_to_label="field", single_class=True, task_uuid="uuid2")

        self.session.add(task1)
        self.session.add(task2)
        self.session.commit()

        # Load tasks into the table
        self.window.load_tasks()

        # Check that the table contains the added tasks
        assert self.window.task_table_widget.rowCount() == 2
        assert self.window.task_table_widget.cellWidget(0, 0).text() == "Task 1"
        assert self.window.task_table_widget.cellWidget(1, 0).text() == "Task 2"

    def test_new_task_button_click(self, qtbot):
        with patch('screens.start_screen.NewTaskDialog') as MockNewTaskDialog:
            # Simulate a click event on the 'New Task' button
            qtbot.mouseClick(self.window.new_task_btn, QtCore.Qt.MouseButton.LeftButton)

            # Check if NewTaskDialog was instantiated with the correct arguments
            MockNewTaskDialog.assert_called_once_with(self.window, self.Session)

    def test_delete_button_click(self, qtbot):
        # Add a task to the database
        task = Task(task_name="Task 1", file_path="/path/to/file1", labels="label1,label2",
                    label_column_name="label", field_to_label="field", single_class=True, task_uuid="uuid1")
        self.session.add(task)
        self.session.commit()

        # Load tasks into the table
        self.window.load_tasks()

        # Simulate a click on the 'Delete' button
        # patch the message box to skit the confirmation dialog
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
            qtbot.mouseClick(self.window.task_table_widget.cellWidget(0, 4), QtCore.Qt.MouseButton.LeftButton)

        # Check that the task has been removed from the table
        assert self.window.task_table_widget.rowCount() == 0

        # Check that the task has been removed from the database
        assert self.session.query(Task).count() == 0

    def test_open_button_click(self, qtbot):
        # Add a task to the database
        task = Task(task_name="Task 1", file_path="/path/to/file1", labels="label1,label2",
                    label_column_name="label", field_to_label="field", single_class=True, task_uuid="uuid1")
        self.session.add(task)
        self.session.commit()

        # Load tasks into the table
        self.window.load_tasks()

        with patch('screens.start_screen.LabelingProjectWindow') as MockLabelingProjectWindow:
            # Simulate a click event on the 'Open' button
            qtbot.mouseClick(self.window.task_table_widget.cellWidget(0, 3), QtCore.Qt.MouseButton.LeftButton)

            # Check if LabelingProjectWindow was instantiated with the correct arguments
            MockLabelingProjectWindow.assert_called_once_with(self.Session, task.task_uuid)

