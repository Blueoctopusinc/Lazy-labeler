import datetime
import os
import json
import threading

import matplotlib
import numpy as np
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal, QEvent, QTimer
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QLabel, QTextEdit, QGridLayout, QPushButton, QWidget, \
    QApplication, QCheckBox
from PyQt6.QtGui import QKeyEvent
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from matplotlib import cm

from models import Task


class TextProcessingThread(QThread):
    """
    QThread that performs text processing.
    It calculates cosine similarity between the description of a task and a list of synonyms for each class.
    The results are then emitted via a PyQt signal.
    """

    # Define a signal that will be emitted with the results of the text processing
    result_signal = pyqtSignal(dict)

    def __init__(self, class_synonyms, description):
        super().__init__()
        # Store the class synonyms and description as instance variables
        self.class_synonyms = class_synonyms
        self.description = description
        # Initialize a TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer()

    def run(self):
        """
        Calculates cosine similarity between the description and class synonyms.
        Emits the result_signal with the results when done.
        """

        results = {}

        # For each class and its synonyms...
        for class_name, synonyms in self.class_synonyms.items():
            # If synonyms is a dict, we calculate nested similarities
            if isinstance(synonyms, dict):
                nested_similarities = []
                for sub_class_name, sub_synonyms in synonyms.items():
                    similarity = self.calculate_similarity(sub_synonyms)
                    if similarity is not None:
                        nested_similarities.append(similarity)
                if len(nested_similarities) == len(synonyms):
                    results[class_name] = min(nested_similarities)
            else:
                # If synonyms is not a dict, we just calculate similarity
                similarity = self.calculate_similarity(synonyms)
                if similarity is not None:
                    results[class_name] = similarity

        # Emit the results
        self.result_signal.emit(results)

    def calculate_similarity(self, synonyms):
        """
        Calculate the cosine similarity between the description and the synonyms.
        """

        # Create a corpus with the synonyms and the description
        corpus = synonyms + [self.description]
        # Generate TF-IDF vectors for the corpus
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(corpus)
        # Separate the description vector from the synonyms vectors
        description_vector = tfidf_matrix[-1]
        synonyms_vectors = tfidf_matrix[:-1]
        # Calculate and return the average cosine similarity
        return cosine_similarity(description_vector, synonyms_vectors).mean()


class DatabaseUpdateThread(QThread):
    """
    QThread that performs database updates.
    A signal is emitted when the update is done.
    """

    # Define a signal that will be emitted when the database update is done
    done = pyqtSignal()

    def __init__(self, session, project_data, current_index):
        super().__init__()

        # Store the session, project data, and current index as instance variables
        self.session = session
        self.project_data = project_data
        self.current_index = current_index

    def run(self):
        """
        Updates the number of labelled samples in the project data and commits the changes to the session.
        Emits the done signal when finished.
        """

        # Update the number of labelled samples in the project data
        # implicit conversion to int otherwise it gets stored and returned as bytes
        # believe it is something to do with how a pandas dataframe index works
        self.project_data.labelled_samples = int(self.current_index)

        # Add the updated project data to the session and commit the changes
        self.session.add(self.project_data)
        self.session.commit()

        # Emit the done signal
        self.done.emit()


class FileSavingThread(QThread):
    """
    QThread that saves the DataFrame to a CSV file.
    A signal is emitted when the file saving operation is done.
    """

    # signal that will be emitted when the file saving operation is done
    done = pyqtSignal()

    def __init__(self, df, file_path):
        super().__init__()

        self.df = df
        self.file_path = file_path

    def run(self):
        """
        Saves the DataFrame to a CSV file and emits the done signal when finished.
        """

        # Save the DataFrame to a CSV file
        self.df.to_csv(self.file_path, index=False)

        # Emit the done signal
        self.done.emit()


def contrast_color(color):
    color = color[1:]
    r, g, b = int(color[:2], 16), int(color[2:4], 16), int(color[4:], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return '#000000' if brightness > 127 else '#ffffff'

class LabelingProjectWindow(QMainWindow):
    """
    This class represents the main window of the labeling project. It includes various UI elements and methods to manage
    the labeling process.
    """

    # Define the key map for class button shortcuts
    key_map = ['1', '2', '3', '4', '5', 'q', 'w', 'e', 'r', 't', 'a', 's', 'd', 'f', 'g', 'z', 'x', 'c', 'v', 'b']

    def __init__(self, Session, project_uuid):
        super().__init__()

        # Install the event filter to catch key press events at the application level
        QApplication.instance().installEventFilter(self)

        # Initialize threads and session
        self.text_processing_thread = None
        self.session = Session()
        session = Session()

        # Load project data from the database
        self.project_data = self.session.query(Task).filter_by(task_uuid=project_uuid).first()
        session.close()

        # Generate colors for class buttons
        self.colors = self._generate_colors()

        # Load data for labeling from CSV file
        self.df = pd.read_csv(self.project_data.file_path)

        # Add a new column for labels if it does not exist
        if self.project_data.label_column_name not in self.df.columns:
            self.df[self.project_data.label_column_name] = None

        # Find the first index where the label is null (i.e., the first unlabeled sample)
        self.current_index = self.df[self.df[self.project_data.label_column_name].isnull()].first_valid_index()

        # Load class synonyms from JSON file
        with open(self.project_data.synonyms_file_path) as f:
            self.class_synonyms = json.load(f)

        # Initialize list of selected classes and the database update thread
        self.selected_classes = []
        self.database_update_thread = None

        # Setup user interface
        self.initUI()

        # Initialize file saving thread and autosave timer
        self.file_saving_thread = None
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_enabled = False  # Autosave is disabled by default
        self.changes_made = False  # No changes have been made yet

    def _generate_colors(self):
        num_labels = len(self.project_data.get_labels_list())
        colors = cm.get_cmap('hsv', num_labels)
        colors = [colors(i) for i in np.linspace(0, 1, num_labels)]
        colors = [matplotlib.colors.rgb2hex(c) for c in colors]
        return colors

    def _generate_colors(self):
        """
        Generate a list of color codes for class buttons. The number of colors generated is equal to the number of labels.
        """
        num_labels = len(self.project_data.get_labels_list())
        colors = cm.get_cmap('hsv', num_labels)
        colors = [colors(i) for i in np.linspace(0, 1, num_labels)]
        colors = [matplotlib.colors.rgb2hex(c) for c in colors]
        return colors

    def initUI(self):
        """
        Initialize the user interface. This includes setting up various UI elements and their respective handlers.
        """
        layout = QVBoxLayout()

        # Setup for labelled samples count label
        self.labelled_samples_count_label = QLabel()
        layout.addWidget(self.labelled_samples_count_label)

        # Setup for description text edit box
        layout.addWidget(QLabel("Description"))
        self.description_edit = QTextEdit()
        self.description_edit.setReadOnly(True)
        layout.addWidget(self.description_edit)

        # Setup for TF-IDF results text edit box
        layout.addWidget(QLabel("TF-IDF Results"))
        self.tfidf_results_edit = QTextEdit()
        self.tfidf_results_edit.setReadOnly(True)
        layout.addWidget(self.tfidf_results_edit)

        # Setup for selected classes text edit box
        layout.addWidget(QLabel("Selected Classes"))
        self.selected_classes_edit = QTextEdit()
        self.selected_classes_edit.setReadOnly(True)
        layout.addWidget(self.selected_classes_edit)

        # Setup for class buttons
        layout.addWidget(QLabel("Class Buttons"))
        layout.addLayout(self._create_class_buttons())

        # Setup for 'Next' button
        next_btn = QPushButton('Next - Space')
        next_btn.clicked.connect(self.on_next_button_clicked)
        layout.addWidget(next_btn)

        # Setup for 'Save' button
        save_btn = QPushButton('Save')
        save_btn.clicked.connect(self.on_save_button_clicked)
        layout.addWidget(save_btn)

        # Setup for autosave checkbox
        layout.addWidget(QLabel("Autosave Checkbox"))
        self.autosave_checkbox = QCheckBox("Autosave every 10 minutes")
        self.autosave_checkbox.stateChanged.connect(self.toggle_autosave)
        layout.addWidget(self.autosave_checkbox)

        # Finalize UI setup
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.description_edit.setText(self.df.loc[self.current_index, 'description'])
        self.labelled_samples_count_label.setText(f"Number of labelled samples: {self.current_index}")
        self.setCentralWidget(central_widget)
        self._start_text_processing_thread()

    def _create_class_buttons(self):
        """
        Create class buttons dynamically based on the number of classes/labels. Each button is linked to its respective handler.
        """
        grid = QGridLayout()
        self.class_buttons = []
        for i, class_name in enumerate(self.project_data.get_labels_list()):
            btn = QPushButton(f"{self.key_map[i]} - {class_name}")
            btn.setStyleSheet(
                f"background-color: {self.colors[i]}; color: {contrast_color(self.colors[i])}; font-weight: bold")
            btn.setCheckable(True)
            btn.clicked.connect(self.on_class_button_clicked)
            self.class_buttons.append(btn)
            grid.addWidget(btn, i // 3, i % 3)
        return grid

    def on_class_button_clicked(self):
        """
        Handler for class button click event. It updates the selected classes and changes the appearance of the clicked button.
        """
        # Identify the button that was just clicked
        clicked_button = self.sender()

        if self.project_data.single_class:
            # If single_class is True, deselect other buttons
            for btn in self.class_buttons:
                if btn is not clicked_button:
                    btn.setChecked(False)
        # Update selected classes
        self.selected_classes = [i for i, btn in enumerate(self.class_buttons) if btn.isChecked()]

        # Update button styles based on their selection status
        for i, btn in enumerate(self.class_buttons):
            if btn.isChecked():
                btn.setStyleSheet(f"background-color: black; color: {self.colors[i]}; font-weight: bold")
            else:
                btn.setStyleSheet(
                    f"background-color: {self.colors[i]}; color: {contrast_color(self.colors[i])}; font-weight: bold")
        self.selected_classes_edit.setText(
            ", ".join(self.project_data.get_labels_list()[i] for i in self.selected_classes))

    def on_next_button_clicked(self):
        """
        Handler for 'Next' button click event. It saves the current label, loads the next unlabeled sample,
        and starts the text processing and database update threads.
        """
        self.df.loc[self.current_index, self.project_data.label_column_name] = str(self.selected_classes)
        next_indices = self.df[self.df[self.project_data.label_column_name].isnull()].index
        if len(next_indices) > 0:
            self.current_index = next_indices[0]
            self.description_edit.setText(self.df.loc[self.current_index, 'description'])
            self._start_database_update_thread()
            self._start_text_processing_thread()
            self.changes_made = True

        else:
            self.description_edit.setText("No more unlabelled records.")
        self.labelled_samples_count_label.setText(f"Number of labelled samples: {self.current_index}")
        self.selected_classes = []
        for btn in self.class_buttons:
            btn.setChecked(False)
            btn.setStyleSheet(btn.styleSheet().replace("background-color: black",
                                                       f"background-color: {self.colors[self.class_buttons.index(btn)]}"))
        if self.current_index % 10 == 0:
            self.df.to_csv(self.project_data.file_path, index=False)

    def _start_database_update_thread(self):
        """
        Start the database update thread. If it's already running, wait for it to finish first.
        """
        if self.database_update_thread and self.database_update_thread.isRunning():
            self.database_update_thread.wait()
        self.database_update_thread = DatabaseUpdateThread(self.session, self.project_data, self.current_index)
        self.database_update_thread.done.connect(self.on_database_update_done)
        self.database_update_thread.start()

    def _start_text_processing_thread(self):
        """
        Start the text processing thread. If it's already running, stop it first and wait for it to finish.
        """
        if self.text_processing_thread and self.text_processing_thread.isRunning():
            self.text_processing_thread.stop_signal.emit()
            self.text_processing_thread.wait()
        self.text_processing_thread = TextProcessingThread(self.class_synonyms,
                                                           self.df.loc[self.current_index, 'description'])
        self.text_processing_thread.result_signal.connect(self.on_similarity_computed)
        self.text_processing_thread.start()
    def on_save_button_clicked(self):
        """
        Handler for 'Save' button click event. Saves the current label and writes the DataFrame to a CSV file.
        """
        self.df.loc[self.current_index, self.project_data.label_column_name] = str(self.selected_classes)
        self.df.to_csv(self.project_data.file_path, index=False)

    def on_database_update_done(self):
        """
        Handler for the completion signal from the database update thread.
        """
        print("Database update done")

    def on_similarity_computed(self, results):
        """
        Handler for the completion signal from the text processing thread. It updates the selected classes based on the similarity results, and displays the results.
        """
        if not results:
            return
        if self.selected_classes:
            return
        best_match_class = max(results, key=results.get)
        best_match_index = self.project_data.get_labels_list().index(best_match_class)
        self.class_buttons[best_match_index].setChecked(True)
        self.on_class_button_clicked()

        sorted_results = sorted(results.items(), key=lambda item: item[1], reverse=True)
        top_n = 10
        sorted_results = sorted_results[:top_n]
        results_str = "\n".join(f"{class_name}: {similarity:.2f}" for class_name, similarity in sorted_results)
        self.tfidf_results_edit.setText(results_str)

    def on_save_done(self):
        """
        Handler for the completion signal from the file saving thread.
        """
        print("File saved at", datetime.datetime.now())
        self.changes_made = False  # Reset the changes_made flag

    def toggle_autosave(self, state):
        """
        Handler for the state change event of the autosave checkbox. It starts or stops the autosave timer based on the state of the checkbox.
        """
        if state == 2:  # Checkbox is checked
            self.autosave_enabled = True
            self.autosave_timer.start(10 * 60 * 1000)  # Start the timer with a 10-minute interval
        else:  # Checkbox is not checked
            self.autosave_enabled = False
            self.autosave_timer.stop()

    def autosave(self):
        """
        Autosave method.
        """
        if self.changes_made:
            self.save_changes()

    def eventFilter(self, source, event):
        """
        Event filter method. It captures key press events at the application level and processes them. Required for spacebar shortcut.
        """
        if event.type() == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True
        return super().eventFilter(source, event)


    def keyPressEvent(self, event: QKeyEvent):
        """
        Handler for key press events. It processes shortcuts for class buttons and the 'Next' button.
        """
        if event.key() == 32:  # space bar
            self.on_next_button_clicked()
        elif event.text() in self.key_map:
            index = self.key_map.index(event.text())
            self.class_buttons[index].click()

    def closeEvent(self, event):
        """
        Handler for the window close event. It closes the database session before closing the window.
        """
        self.session.close()
        super().closeEvent(event)
