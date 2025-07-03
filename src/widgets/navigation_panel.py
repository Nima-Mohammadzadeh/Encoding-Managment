from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QLabel,
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPixmap
import os


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
            self.setIconSize(QSize(24, 24))

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
        self.expanded_width = 200
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