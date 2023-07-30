import pytest
from PyQt6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

app = QApplication([])

class BaseTestCase:
    @pytest.fixture(scope='function', autouse=True)
    def setup_session(self):
        # Create a SQLite database in memory and a sessionmaker
        self.engine = create_engine('sqlite:///:memory:')
        self.Session = sessionmaker(bind=self.engine)

        # Create the tasks table in the database
        Base.metadata.create_all(self.engine)

        # Start a new session
        self.session = self.Session()

        yield

        # Close the session and drop all tables after each test
        self.session.close()
        Base.metadata.drop_all(self.engine)