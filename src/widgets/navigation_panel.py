from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QLabel,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QIcon, QPixmap
import os
from src.utils.file_utils import resource_path


class CollapsibleNavButton(QPushButton):
    def __init__(self, text, icon_path, parent=None):
        super().__init__(text, parent)
        self.original_text = text  # Avoid shadowing QPushButton.text()
        self.icon_path = icon_path
        
        self.setCheckable(True)
        self.setMinimumHeight(45)
        self.setMaximumHeight(45)
        
        if os.path.exists(self.icon_path):
            icon = QIcon(self.icon_path)
            self.setIcon(icon)
            self.setIconSize(QSize(31, 31))

        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 14px;
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
                padding-left: 11px;
            }
        """)

class CollapsibleNavigationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self.expanded_width = 170
        self.collapsed_width = 70
        
        # Cache logo pixmaps
        self.logo_pixmap_large = None
        self.logo_pixmap_small = None
        self._load_logo_pixmaps()
        
        self.setMinimumWidth(self.expanded_width)
        self.setMaximumWidth(self.expanded_width)
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
        self.animation_group = None
        
    def _load_logo_pixmaps(self):
        """Pre-load and cache logo pixmaps to avoid repeated disk I/O"""
        logo_path = resource_path(os.path.join("src", "icons", "logo.png"))
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Cache both sizes
            self.logo_pixmap_large = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, 
                                                   Qt.TransformationMode.SmoothTransformation)
            self.logo_pixmap_small = pixmap.scaled(45, 45, Qt.AspectRatioMode.KeepAspectRatio, 
                                                   Qt.TransformationMode.SmoothTransformation)
        
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
        self.logo_opacity_effect = QGraphicsOpacityEffect()
        self.logo_label.setGraphicsEffect(self.logo_opacity_effect)
        
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
                padding-left: 14px;
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
        
        # Create animation group for synchronized animations
        self.animation_group = QParallelAnimationGroup()
        
        # Width animations for both min and max
        self.min_width_anim = QPropertyAnimation(self, b"minimumWidth")
        self.min_width_anim.setDuration(250)
        self.min_width_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.min_width_anim.setStartValue(self.width())
        self.min_width_anim.setEndValue(self.collapsed_width if self.is_collapsed else self.expanded_width)
        
        self.max_width_anim = QPropertyAnimation(self, b"maximumWidth")
        self.max_width_anim.setDuration(250)
        self.max_width_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.max_width_anim.setStartValue(self.width())
        self.max_width_anim.setEndValue(self.collapsed_width if self.is_collapsed else self.expanded_width)
        
        self.animation_group.addAnimation(self.min_width_anim)
        self.animation_group.addAnimation(self.max_width_anim)
        
        # Logo fade animation
        logo_fade = QPropertyAnimation(self.logo_opacity_effect, b"opacity")
        logo_fade.setDuration(150)
        logo_fade.setStartValue(1.0 if not self.is_collapsed else 0.0)
        logo_fade.setEndValue(0.0 if self.is_collapsed else 1.0)
        self.animation_group.addAnimation(logo_fade)
        
        # Update text visibility
        if self.is_collapsed:
            for button in self.nav_buttons:
                button.setText("")
        else:
            self.animation_group.finished.connect(self.show_button_text)

        self.animation_group.start()
        self.update_logo()

    def show_button_text(self):
        """Show button text after animation finishes."""
        if not self.is_collapsed:
            for button in self.nav_buttons:
                button.setText(button.original_text)
        
        # Disconnect the signal
        if self.animation_group:
            try:
                self.animation_group.finished.disconnect(self.show_button_text)
            except (TypeError, RuntimeError):
                pass

    def update_logo(self):
        """Update logo display using cached pixmaps"""
        if self.is_collapsed:
            self.logo_label.hide()
            # Move button to the start
            self.header_layout.insertWidget(0, self.collapse_btn)
            self.collapse_btn.setFixedSize(60, 50)
            self.collapse_btn.setIconSize(QSize(31, 31))
            self.collapse_btn.setStyleSheet(self.collapse_btn_collapsed_style)
        else:
            self.logo_label.show()
            # Move button to the end
            self.header_layout.addWidget(self.collapse_btn)
            self.collapse_btn.setFixedSize(50, 50)
            self.collapse_btn.setIconSize(QSize(40, 40))
            self.collapse_btn.setStyleSheet(self.collapse_btn_original_style)

        # Use cached pixmaps
        if self.logo_pixmap_large and self.logo_pixmap_small:
            pixmap = self.logo_pixmap_small if self.is_collapsed else self.logo_pixmap_large
            self.logo_label.setPixmap(pixmap)
            size = 45 if self.is_collapsed else 60
            self.logo_label.setFixedSize(size, size)
        else:
            # Fallback text
            size = 45 if self.is_collapsed else 60
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