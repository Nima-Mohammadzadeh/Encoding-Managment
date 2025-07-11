from datetime import datetime
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor


class JobSelectionDialog(QDialog):
    """Dialog for selecting a job when multiple jobs are due on the same day."""
    job_selected = Signal(dict)
    
    def __init__(self, jobs: List[Dict[str, Any]], date_str: str, parent=None):
        super().__init__(parent)
        self.jobs = jobs
        self.selected_job = None
        
        self.setWindowTitle("Select Job")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        # Style the dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d30;
                border: 1px solid #464647;
            }
        """)
        
        self.setup_ui(date_str)
    
    def setup_ui(self, date_str: str):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel(f"Jobs Due on {date_str}")
        header_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header_label)
        
        # Subtitle
        subtitle_label = QLabel(f"Select a job to view details ({len(self.jobs)} jobs):")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 12px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(subtitle_label)
        
        # Jobs list
        self.jobs_list = QListWidget()
        self.jobs_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 5px;
                color: #e0e0e0;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #464647;
                margin: 2px 0px;
            }
            QListWidget::item:hover {
                background-color: #3d3d40;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        
        # Populate jobs list
        for job in self.jobs:
            item_widget = self.create_job_item(job)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.jobs_list.addItem(list_item)
            self.jobs_list.setItemWidget(list_item, item_widget)
        
        layout.addWidget(self.jobs_list, 1)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        select_btn = QPushButton("Select")
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        select_btn.clicked.connect(self.on_select_clicked)
        buttons_layout.addWidget(select_btn)
        
        layout.addLayout(buttons_layout)
        
        # Connect double-click to select
        self.jobs_list.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def create_job_item(self, job: Dict[str, Any]) -> QFrame:
        """Create a widget for displaying job information."""
        item_frame = QFrame()
        item_frame.job_data = job  # Store job data with the widget
        
        layout = QVBoxLayout(item_frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Main info line
        customer = job.get("Customer", "Unknown")
        ticket = job.get("Job Ticket#", job.get("Ticket#", "N/A"))
        po = job.get("PO#", "N/A")
        
        main_line = QLabel(f"{customer} - Ticket #{ticket}")
        main_line.setStyleSheet("font-weight: bold; color: #e0e0e0; font-size: 12px;")
        layout.addWidget(main_line)
        
        # Details line
        part = job.get("Part#", "N/A")
        qty = job.get("Quantity", job.get("Qty", "N/A"))
        
        # Format quantity with commas
        if qty and str(qty).replace(',', '').isdigit():
            clean_qty = str(qty).replace(',', '')
            qty = f"{int(clean_qty):,}"
        
        details_line = QLabel(f"PO: {po} | Part#: {part} | Qty: {qty}")
        details_line.setStyleSheet("color: #cccccc; font-size: 10px;")
        layout.addWidget(details_line)
        
        # Additional info
        inlay = job.get("Inlay Type", "N/A")
        size = job.get("Label Size", "N/A")
        
        additional_line = QLabel(f"Inlay: {inlay} | Size: {size}")
        additional_line.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(additional_line)
        
        return item_frame
    
    def on_select_clicked(self):
        """Handle select button click."""
        current_item = self.jobs_list.currentItem()
        if current_item:
            current_widget = self.jobs_list.itemWidget(current_item)
            if current_widget and hasattr(current_widget, 'job_data'):
                self.selected_job = current_widget.job_data
                self.job_selected.emit(self.selected_job)
                self.accept()
    
    def on_item_double_clicked(self, item):
        """Handle item double-click."""
        current_widget = self.jobs_list.itemWidget(item)
        if current_widget and hasattr(current_widget, 'job_data'):
            self.selected_job = current_widget.job_data
            self.job_selected.emit(self.selected_job)
            self.accept() 