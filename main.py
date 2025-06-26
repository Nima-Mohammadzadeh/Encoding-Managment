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
import pymupdf, shutil, os, sys, json
from qt_material import apply_stylesheet
from PySide6.QtCore import Qt, QSize

# Import the widgets from their new locations
from src.tabs.job_page import JobPageWidget
from src.tabs.archive_page import ArchivePageWidget
from src.shared_serial_manager import initialize_shared_serial_manager



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Workflow Optimizer")
        self.setGeometry(50, 50, 1200, 650)
        self.setMinimumSize(1200, 650)

        # Define the base path for the application
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Initialize shared serial number system
        self.initialize_shared_serial_system()

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

    def initialize_shared_serial_system(self):
        """Initialize the shared serial number system using Z: drive."""
        try:
            # Load settings to get the shared path
            settings_path = os.path.join(self.base_path, "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}
            
            # Get shared path (defaults to Z: drive)
            shared_path = settings.get("base_path", r"Z:\3 Encoding and Printing Files\Customers Encoding Files")
            
            # Try to initialize the shared serial manager
            success = initialize_shared_serial_manager(shared_path)
            
            if success:
                print(f"✅ Shared serial number system initialized at: {shared_path}")
            else:
                print(f"⚠️  Could not initialize shared serial system at: {shared_path}")
                print("   Serial numbers will not be available until the shared drive is accessible.")
                
                # Show a non-blocking message to the user
                QMessageBox.warning(
                    self,
                    "Shared Serial System",
                    f"Could not initialize the shared serial number system.\n\n"
                    f"Path: {shared_path}\n\n"
                    "Serial number assignment will not be available until the shared drive is accessible.\n"
                    "Please check your network connection to the Z: drive."
                )
                
        except Exception as e:
            print(f"Error initializing shared serial system: {e}")
            QMessageBox.critical(
                self,
                "Serial System Error",
                f"Error initializing shared serial number system:\n{e}"
            )

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
