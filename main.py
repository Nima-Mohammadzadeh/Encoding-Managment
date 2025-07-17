from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QStackedWidget,
    QLabel,
    QListWidgetItem,
    QFileDialog,    
    QMessageBox,
    QPushButton,
    QFrame,
    QSizePolicy
)
import pymupdf, shutil, os, sys
from qt_material import apply_stylesheet
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPixmap, QFont, QPainter
from PySide6.QtSvg import QSvgRenderer

# Import the widgets from their new locations
from src.widgets.navigation_panel import CollapsibleNavigationPanel
from src.tabs.job_page import JobPageWidget
from src.tabs.archive_page import ArchivePageWidget
from src.tabs.settings_page import SettingsPageWidget
from src.tabs.dashboard_page import DashboardPageWidget
from src.tabs.reports_page import ReportsPageWidget
from src.tabs.tools_page import ToolsPageWidget
from src.widgets.job_details_dialog import JobDetailsDialog
import src.config as config
from src.utils.file_utils import resource_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Starport Tech")    
        self.setGeometry(50, 50, 1200, 650)
        self.setMinimumSize(1200, 650)

        # Define the base path for the application
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        # Ensure that the directories specified in the config exist
        config.ensure_dirs_exist()

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Navigation panel
        self.nav_panel = CollapsibleNavigationPanel()
        main_layout.addWidget(self.nav_panel)

        # Content pages
        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)

        main_layout.setStretchFactor(self.nav_panel, 0)
        main_layout.setStretchFactor(self.page_stack, 1)

        # Instantiate pages, passing the base_path to them
        self.dashboard_page = DashboardPageWidget(base_path=self.base_path)
        self.jobs_page = JobPageWidget(base_path=self.base_path)
        self.tools_page = ToolsPageWidget(base_path=self.base_path)
        self.reports_page = ReportsPageWidget(base_path=self.base_path)
        self.archive_page = ArchivePageWidget(base_path=self.base_path)
        self.settings_page = SettingsPageWidget()

        # Add pages to the stack and create navigation buttons
        self.add_page("Dashboard", self.dashboard_page, "dashboard.png")
        self.add_page("Jobs", self.jobs_page, "customers.png")
        self.add_page("Tools", self.tools_page, "tools.png")
        self.add_page("Reports", self.reports_page, "reports.png")
        self.add_page("Archive", self.archive_page, "Database.png")
        self.add_page("Settings", self.settings_page, "settings.png")
        
        # Finalize navigation layout
        self.nav_panel.finalize_navigation()

        # Connect navigation signals
        for i, button in enumerate(self.nav_panel.nav_buttons):
            button.clicked.connect(lambda checked, index=i: self.switch_page(index))

        # Connect other signals
        self.jobs_page.job_to_archive.connect(self.archive_page.add_archived_job)
        self.jobs_page.job_created.connect(self.dashboard_page.refresh_dashboard)  # New connection
        self.settings_page.active_jobs_source_changed.connect(self.jobs_page.update_active_jobs_source_directory)
        self.settings_page.active_jobs_source_changed.connect(self.dashboard_page.update_source_directories)
        self.archive_page.job_was_archived.connect(self.dashboard_page.refresh_dashboard)
        self.archive_page.job_was_deleted.connect(self.dashboard_page.refresh_dashboard)  # New connection
        
        # Connect dashboard signals
        self.dashboard_page.navigate_to_jobs.connect(lambda: self.switch_page(1))
        self.dashboard_page.navigate_to_archive.connect(lambda: self.switch_page(4))
        self.dashboard_page.navigate_to_tools.connect(lambda: self.switch_page(2))
        self.dashboard_page.navigate_to_reports.connect(lambda: self.switch_page(3))
        self.dashboard_page.create_new_job.connect(self.handle_create_new_job)
        self.dashboard_page.open_job_details.connect(self.handle_open_job_details)

        # Set central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Set initial page
        self.switch_page(0)

    def closeEvent(self, event):
        """Save data when the application is closing."""
        print("Closing application")
        self.jobs_page.save_data()
        event.accept()

    def add_page(self, title, widget, icon_name):
        """Helper to add a page and navigation button."""
        self.page_stack.addWidget(widget)
        self.nav_panel.add_nav_button(title, icon_name)
        
    def switch_page(self, index):
        """Switch page based on navigation selection."""
        self.page_stack.setCurrentIndex(index)
        self.nav_panel.set_current_button(index)
    
    def handle_create_new_job(self):
        """Handle create new job from dashboard - switch to jobs page and open wizard."""
        self.switch_page(1)  # Switch to jobs page
        self.jobs_page.open_new_job_wizard()  # Open the new job wizard

    def handle_open_job_details(self, job_data):
        """Handle opening the job details dialog from anywhere in the app."""
        details_dialog = JobDetailsDialog(job_data, self.base_path, self)
        details_dialog.job_updated.connect(self.handle_job_updated)
        details_dialog.job_archived.connect(self.handle_job_archived)
        details_dialog.job_deleted.connect(self.handle_job_deleted)
        details_dialog.exec()

    def handle_job_updated(self, updated_job_data):
        """Handle the job_updated signal from JobDetailsDialog."""
        self.jobs_page.refresh_jobs_table()
        self.dashboard_page.refresh_dashboard()
        self.archive_page.load_jobs()

    def handle_job_archived(self, job_data):
        """Handle the job_archived signal from JobDetailsDialog."""
        self.archive_page.add_archived_job(job_data)
        self.jobs_page.refresh_jobs_table()
        self.dashboard_page.refresh_dashboard()

    def handle_job_deleted(self, job_data):
        """Handle the job_deleted signal from JobDetailsDialog."""
        # Refresh the jobs page to reflect the deletion
        self.jobs_page.refresh_jobs_table()
        # Refresh the dashboard to update statistics
        self.dashboard_page.refresh_dashboard()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

