import datetime
from sqlalchemy import Column, Integer, String, Boolean, create_engine, DateTime
from sqlalchemy.orm import validates, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    task_name = Column(String)
    file_path = Column(String)
    labels = Column(String)
    label_column_name = Column(String)
    synonyms_file_path = Column(String)
    field_to_label = Column(String)
    single_class = Column(Boolean)
    labelled_samples = Column(Integer, default=0)
    task_uuid = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.now())  # Set default value to current UTC time

    @validates('task_name', 'file_path', 'labels', 'label_column_name', 'field_to_label', 'task_directory')
    def validate_not_empty(self, key, value):
        error_messages = {
            'task_name': 'Task Name is required.',
            'file_path': 'Path to the data you are labelling is required.',
            'labels': 'Discrete classes are required.',
            'label_column_name': 'The name given to the column for the label class is required.',
            'field_to_label': 'The field to label is required.'
        }
        if not value:
            raise ValueError(error_messages.get(key, f"{key} should not be empty"))
        return value

    def get_labels_list(self):
        return self.labels.split(',')

    def get_single_class_bool(self):
        return self.single_class.lower() == 'true'