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
from src.tabs.job_page import JobPageWidget
from src.tabs.archive_page import ArchivePageWidget
from src.tabs.settings_page import SettingsPageWidget
from src.tabs.dashboard_page import DashboardPageWidget
from src.tabs.reports_page import ReportsPageWidget
from src.tabs.tools_page import ToolsPageWidget
from src.widgets.job_details_dialog import JobDetailsDialog
import src.config as config
from src.utils.file_utils import resource_path


class CollapsibleNavButton(QPushButton):
    def __init__(self, text, icon_path, parent=None):
        super().__init__(parent)
        self.text = text
        self.icon_path = icon_path
        
        self.setCheckable(True)
        self.setMinimumHeight(45)
        self.setMaximumHeight(45)
        
        if os.path.exists(self.icon_path):
            icon = QIcon(self.icon_path)
            self.setIcon(icon)
            self.setIconSize(QSize(32, 32))

        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 18px; /* Adjusted padding for icon */
                border: none;
                background-color: transparent;
                font-size: 14px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:checked {
                background-color: rgba(255, 255, 255, 0.2);
                border-left: 3px solid #0078d4;
                padding-left: 15px; /* Adjust padding when checked */
            }
        """)

class CollapsibleNavigationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.expanded_width = 170
        self.collapsed_width = 60  # Adjusted for better spacing and icon visibility
        
        self.setFixedWidth(self.expanded_width)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d30;
                border-right: 1px solid #464647;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.create_header()
        
        self.nav_frame = QFrame()
        self.nav_layout = QVBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(5, 10, 5, 10)
        self.nav_layout.setSpacing(5)
        
        self.main_layout.addWidget(self.nav_frame, 1)
        
        self.nav_buttons = []
        self.animation = None
        
    def create_header(self):
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(80)
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border-bottom: 1px solid #464647;
            }
        """)
        
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(5, 5, 5, 5)
        self.header_layout.setSpacing(5)
        
        # Logo
        self.logo_label = QLabel()
        
        # Collapse button
        self.collapse_btn = QPushButton()
        collapse_icon_path = resource_path(os.path.join("src", "icons", "collapse_nav_btn.png"))
        if os.path.exists(collapse_icon_path):
            self.collapse_btn.setIcon(QIcon(collapse_icon_path))
        else:
            self.collapse_btn.setText("≡")
        self.collapse_btn.setFixedSize(50, 50)
        self.collapse_btn.setIconSize(QSize(40, 40))
        
        self.collapse_btn_original_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid #464647;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        self.collapse_btn_collapsed_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                text-align: left;
                padding-left: 18px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """
        self.collapse_btn.setStyleSheet(self.collapse_btn_original_style)
        self.collapse_btn.clicked.connect(self.toggle_collapse)

        self.header_layout.addWidget(self.logo_label)
        self.header_layout.addStretch(1)
        self.header_layout.addWidget(self.collapse_btn)

        self.main_layout.addWidget(self.header_frame)
        self.update_logo()

    def add_nav_button(self, text, icon_name):
        icon_path = resource_path(os.path.join("src", "icons", icon_name))
        button = CollapsibleNavButton(text, icon_path)
        
        self.nav_buttons.append(button)
        self.nav_layout.addWidget(button)
        
        return button
    
    def finalize_navigation(self):
        self.nav_layout.addStretch()
    
    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        
        # Animate the panel width
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        start_width = self.width()
        end_width = self.collapsed_width if self.is_collapsed else self.expanded_width
        
        self.animation.setStartValue(start_width)
        self.animation.setEndValue(end_width)
        
        # Hide text before shrinking, show after expanding
        if self.is_collapsed:
            for button in self.nav_buttons:
                button.setText("")
        else:
            self.animation.finished.connect(self.show_button_text)

        self.animation.start()
        
        self.update_logo()

    def show_button_text(self):
        """Show button text after animation finishes."""
        if not self.is_collapsed:
            for button in self.nav_buttons:
                button.setText(button.text)
        
        # Only disconnect if the animation object exists
        if self.animation:
            try:
                self.animation.finished.disconnect(self.show_button_text)
            except (TypeError, RuntimeError):
                # This can happen if the signal is not connected, which is fine.
                pass

    def update_logo(self):
        logo_path = resource_path(os.path.join("src", "icons", "logo.png"))
        
        if self.is_collapsed:
            size = 45
            self.logo_label.hide()
            # Move button to the start, before the stretch
            self.header_layout.insertWidget(0, self.collapse_btn)
            
            self.collapse_btn.setIconSize(QSize(32, 32))
            self.collapse_btn.setStyleSheet(self.collapse_btn_collapsed_style)
        else:
            size = 60
            self.logo_label.show()
            # Move button to the end, after the stretch
            self.header_layout.addWidget(self.collapse_btn)

            self.collapse_btn.setIconSize(QSize(40, 40))
            self.collapse_btn.setStyleSheet(self.collapse_btn_original_style)

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
            self.logo_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.logo_label.setFixedSize(size, size)
        else:
            self.logo_label.setText("ST")
            self.logo_label.setStyleSheet(f"""
                QLabel {{
                    color: #0078d4;
                    font-size: {size / 2}px;
                    font-weight: bold;
                    background-color: transparent;
                    border: none;
                }}
            """)
            self.logo_label.setFixedSize(size, size)
        
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_current_button(self, index):
        for button in self.nav_buttons:
            button.setChecked(False)
        
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)


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
        
        # Set initial button text based on default state
        self.nav_panel.show_button_text()

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

