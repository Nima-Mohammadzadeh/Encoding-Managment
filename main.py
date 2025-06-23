from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QLabel,
    QListWidgetItem,
    QFileDialog,
    QMessageBox
)
import pymupdf, shutil, os, sys
from qt_material import apply_stylesheet
from PySide6.QtCore import Qt, QSize

# Import the widgets from their new locations
from src.tabs.job_page import JobPageWidget
from src.tabs.archive_page import ArchivePageWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Workflow Optimizer")
        self.setGeometry(50, 50, 1100, 650)

        # Define the base path for the application
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        # Main layout
        main_layout = QHBoxLayout()

        # Navigation
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(135)
        main_layout.addWidget(self.nav_list)

        # Content pages
        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)

        main_layout.setStretchFactor(self.nav_list, 0)
        main_layout.setStretchFactor(self.page_stack, 1)

        # Instantiate pages, passing the base_path to them
        self.jobs_page = JobPageWidget(base_path=self.base_path)
        self.archive_page = ArchivePageWidget(base_path=self.base_path)

        # Add pages to the stack
        self.add_page("Dashboard", QLabel("This is the Dashboard Page.\\n\\nSummary info will go here."))
        self.add_page("QuickTools", QLabel("This is the QuickTools Page.\\n\\nWidgets for small, one-off tasks go here."))
        self.add_page("Jobs", self.jobs_page)
        self.add_page("Reports", QLabel("This is the Reports Page.\\n\\nCharts and data exports will live here."))
        self.add_page("Settings", QLabel("This is the Settings Page.\\n\\nApplication settings will be configured here."))
        self.add_page("Archive", self.archive_page)

        # Connect signals
        self.jobs_page.job_to_archive.connect(self.archive_page.add_archived_job)
        self.nav_list.currentItemChanged.connect(self.switch_page)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Set initial page
        self.nav_list.setCurrentRow(0)

    def closeEvent(self, event):
        """Save data when the application is closing."""
        print("Closing application")
        self.jobs_page.save_data()
        event.accept()

    def add_page(self, title, widget):
        """Helper to add a page and navigation item."""
        self.page_stack.addWidget(widget)
        item = QListWidgetItem(title)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setSizeHint(QSize(0, 35))
        self.nav_list.addItem(item)
        
    def switch_page(self, current_item):
        """Switch page based on navigation selection."""
        index = self.nav_list.row(current_item)
        self.page_stack.setCurrentIndex(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
