from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDateEdit, QGroupBox, QTextEdit, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont
import json
import os
from datetime import datetime, timedelta


class ReportsPageWidget(QWidget):
    def __init__(self, base_path=None, parent=None):
        super().__init__(parent)
        self.base_path = base_path if base_path else os.path.dirname(os.path.abspath(__file__))
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the reports page UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Reports")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Report filters
        left_panel = QFrame()
        left_panel.setMaximumWidth(300)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        left_layout = QVBoxLayout(left_panel)
        
        # Report type selection
        report_type_group = QGroupBox("Report Type")
        report_type_layout = QVBoxLayout()
        
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "Job Summary",
            "Customer Report",
            "Production Statistics",
            "Archive Overview",
            "Custom Report"
        ])
        report_type_layout.addWidget(self.report_type_combo)
        report_type_group.setLayout(report_type_layout)
        
        left_layout.addWidget(report_type_group)
        
        # Date range selection
        date_group = QGroupBox("Date Range")
        date_layout = QVBoxLayout()
        
        date_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        date_layout.addWidget(self.date_from)
        
        date_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_to)
        
        date_group.setLayout(date_layout)
        left_layout.addWidget(date_group)
        
        # Generate button
        self.generate_btn = QPushButton("Generate Report")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_report)
        left_layout.addWidget(self.generate_btn)
        
        # Export button
        self.export_btn = QPushButton("Export Report")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a5a5a;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #6a6a6a;
            }
        """)
        self.export_btn.setEnabled(False)
        left_layout.addWidget(self.export_btn)
        
        left_layout.addStretch()
        
        # Right panel - Report display
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        right_layout = QVBoxLayout(right_panel)
        
        # Report header
        self.report_header = QLabel("Select a report type and click Generate")
        self.report_header.setAlignment(Qt.AlignCenter)
        report_header_font = QFont()
        report_header_font.setPointSize(14)
        self.report_header.setFont(report_header_font)
        right_layout.addWidget(self.report_header)
        
        # Report content area
        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        self.report_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                padding: 10px;
                color: #ffffff;
            }
        """)
        right_layout.addWidget(self.report_display)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
    def generate_report(self):
        """Generate the selected report"""
        report_type = self.report_type_combo.currentText()
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        
        self.report_header.setText(f"{report_type} - {date_from} to {date_to}")
        
        # Placeholder report content
        report_content = f"""
<h2>{report_type}</h2>
<p><strong>Date Range:</strong> {date_from} to {date_to}</p>
<hr>

<p>This is a placeholder for the {report_type}.</p>

<h3>Summary Statistics</h3>
<ul>
    <li>Total Jobs: 0</li>
    <li>Completed Jobs: 0</li>
    <li>Active Jobs: 0</li>
</ul>

<p><em>Report generation functionality will be implemented based on your specific requirements.</em></p>
"""
        
        self.report_display.setHtml(report_content)
        self.export_btn.setEnabled(True)
        
    def load_active_jobs_data(self):
        """Load active jobs data for reporting"""
        active_jobs_path = os.path.join(self.base_path, "data", "active_jobs.json")
        try:
            with open(active_jobs_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
            
    def load_archived_jobs_data(self):
        """Load archived jobs data for reporting"""
        archived_jobs_path = os.path.join(self.base_path, "data", "archived_jobs.json")
        try:
            with open(archived_jobs_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return [] 