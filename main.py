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
import src.config as config


class CollapsibleNavButton(QPushButton):
    def __init__(self, text, icon_path, parent=None):
        super().__init__(parent)
        self.text = text
        self.icon_path = icon_path
        self.is_collapsed = False
        
        self.setCheckable(True)
        self.setMinimumHeight(45)
        self.setMaximumHeight(45)
        
        # Set up the button with icon and text
        self.setup_button()
        
    def setup_button(self):
        if os.path.exists(self.icon_path):
            icon = QIcon(self.icon_path)
            self.setIcon(icon)
            self.setIconSize(QSize(24, 24))
        
        if not self.is_collapsed:
            self.setText(self.text)
            self.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 15px;
                    border: none;
                    background-color: transparent;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton:checked {
                    background-color: rgba(255, 255, 255, 0.2);
                    border-left: 3px solid #0078d4;
                }
            """)
        else:
            self.setText("")
            self.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    border: none;
                    background-color: transparent;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton:checked {
                    background-color: rgba(255, 255, 255, 0.2);
                    border-left: 3px solid #0078d4;
                }
            """)
    
    def set_collapsed(self, collapsed):
        self.is_collapsed = collapsed
        self.setup_button()


class CollapsibleNavigationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.expanded_width = 200
        self.collapsed_width = 90  # Adjusted for better spacing
        
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
        
    def create_header(self):
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(80)
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-bottom: 1px solid #464647;
            }
        """)
        
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)
        header_layout.setSpacing(5)
        
        # Logo
        self.logo_label = QLabel()
        
        # Collapse button
        self.collapse_btn = QPushButton()
        collapse_icon_path = os.path.join("src", "icons", "collapse_nav_btn.png")
        if os.path.exists(collapse_icon_path):
            self.collapse_btn.setIcon(QIcon(collapse_icon_path))
        else:
            self.collapse_btn.setText("≡")
        self.collapse_btn.setFixedSize(30, 30)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #464647;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)

        header_layout.addWidget(self.logo_label)
        header_layout.addStretch()
        header_layout.addWidget(self.collapse_btn)

        self.main_layout.addWidget(self.header_frame)
        self.update_logo()

    def add_nav_button(self, text, icon_name):
        icon_path = os.path.join("src", "icons", icon_name)
        button = CollapsibleNavButton(text, icon_path)
        button.set_collapsed(self.is_collapsed)
        
        self.nav_buttons.append(button)
        self.nav_layout.addWidget(button)
        
        return button
    
    def finalize_navigation(self):
        self.nav_layout.addStretch()
    
    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        
        for button in self.nav_buttons:
            button.set_collapsed(self.is_collapsed)
        
        if self.is_collapsed:
            self.setFixedWidth(self.collapsed_width)
        else:
            self.setFixedWidth(self.expanded_width)
            
        self.update_logo()

    def update_logo(self):
        logo_path = os.path.join("src", "icons", "logo.png")
        
        if self.is_collapsed:
            size = 45
        else:
            size = 60

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
        self.jobs_page = JobPageWidget(base_path=self.base_path)
        self.archive_page = ArchivePageWidget(base_path=self.base_path)
        self.settings_page = SettingsPageWidget()

        # Add pages to the stack and create navigation buttons
        self.add_page("Dashboard", QLabel("This is the Dashboard Page.\\n\\nSummary info will go here."), "dashboard.png")
        self.add_page("Jobs", self.jobs_page, "customers.png")
        self.add_page("Settings", self.settings_page, "settings.png")
        self.add_page("Archive", self.archive_page, "Database.png")
        
        # Finalize navigation layout
        self.nav_panel.finalize_navigation()

        # Connect navigation signals
        for i, button in enumerate(self.nav_panel.nav_buttons):
            button.clicked.connect(lambda checked, index=i: self.switch_page(index))

        # Connect other signals
        self.jobs_page.job_to_archive.connect(self.archive_page.add_archived_job)
        self.settings_page.active_jobs_source_changed.connect(self.jobs_page.update_active_jobs_source_directory)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_blue.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

