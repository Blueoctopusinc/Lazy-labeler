import os
import sys
from PyQt6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from screens.start_screen import StartWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Create a SQLite database engine
    engine = create_engine('sqlite:///tasks/tasks.db')
    Base.metadata.create_all(engine)
    # Create a SQLAlchemy SessionFactory
    Session = sessionmaker(bind=engine)

    # Pass the Session factory to the main window
    tool = StartWindow(Session)
    tool.show()

    sys.exit(app.exec())
