"""
Global Search Dialog

This dialog provides comprehensive search functionality across all job data including:
- Active jobs
- Archived jobs
- All data fields (Customer, PO#, Ticket#, UPC, Serial Numbers, etc.)
- Advanced filtering and sorting options
"""

import os
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QGroupBox, QFrame,
    QTableView, QHeaderView, QComboBox, QCheckBox, QProgressBar,
    QMessageBox, QSizePolicy, QTabWidget, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QAbstractTableModel
from PySide6.QtGui import QFont, QStandardItem, QStandardItemModel

import src.config as config


class JobDataModel(QStandardItemModel):
    """Model for displaying job search results"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = [
            "Customer", "Ticket#", "PO#", "Part#", 
            "Inlay", "Size", "Qty", "UPC", "Status", "Date"
        ]
        self.setHorizontalHeaderLabels(self.headers)
        
        self.jobs_data = []  # Store full job data for details
    
    def add_job_result(self, job_data, job_type="Active"):
        """Add a job to the search results"""
        # Handle both old and new field names
        ticket_num = job_data.get("Ticket#", job_data.get("Job Ticket#", ""))
        quantity = job_data.get("Qty", job_data.get("Quantity", ""))
        
        # Format quantity with commas if it's a number
        if quantity and str(quantity).replace(",", "").isdigit():
            quantity = f"{int(str(quantity).replace(',', '')):,}"
        
        # Determine date to display
        date_display = ""
        if job_type == "Archive":
            archive_date = job_data.get("dateArchived", job_data.get("archivedDate", ""))
            if archive_date:
                try:
                    if " " in archive_date:
                        date_display = archive_date.split()[0]  # Extract date part
                    else:
                        date_display = archive_date
                except Exception:
                    date_display = archive_date
        else:
            # For active jobs, try to get due date or creation date
            due_date = job_data.get("Due Date", "")
            if due_date:
                date_display = due_date
        
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(ticket_num),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(str(quantity)),
            QStandardItem(job_data.get("UPC Number", "")),
            QStandardItem(job_data.get("Status", "")),
            QStandardItem(date_display)
        ]
        
        self.appendRow(row_items)
        self.jobs_data.append(job_data)
    
    def clear_results(self):
        """Clear all search results"""
        self.clear()
        self.setHorizontalHeaderLabels(self.headers)
        self.jobs_data = []
    
    def get_job_data(self, row):
        """Get full job data for a specific row"""
        if 0 <= row < len(self.jobs_data):
            return self.jobs_data[row]
        return None


class GlobalSearchWorker(QThread):
    """Worker thread for performing global search"""
    
    progress_updated = Signal(int, str)  # percentage, message
    result_found = Signal(dict, str)     # job_data, job_type
    search_completed = Signal(int)       # total_results
    
    def __init__(self, search_terms, search_active, search_archived):
        super().__init__()
        self.search_terms = search_terms.lower().strip()
        self.search_active = search_active
        self.search_archived = search_archived
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the search operation"""
        self.is_cancelled = True
    
    def run(self):
        """Perform the search operation"""
        try:
            total_results = 0
            
            # Search active jobs if requested
            if self.search_active and not self.is_cancelled:
                self.progress_updated.emit(10, "Searching active jobs...")
                results = self.search_active_jobs()
                total_results += results
                
                if self.is_cancelled:
                    return
            
            # Search archived jobs if requested
            if self.search_archived and not self.is_cancelled:
                self.progress_updated.emit(60, "Searching archived jobs...")
                results = self.search_archived_jobs()
                total_results += results
            
            if not self.is_cancelled:
                self.progress_updated.emit(100, f"Search completed - {total_results} results found")
                self.search_completed.emit(total_results)
                
        except Exception as e:
            self.progress_updated.emit(0, f"Search error: {str(e)}")
            self.search_completed.emit(0)
    
    def search_active_jobs(self):
        """Search through active jobs"""
        results_count = 0
        active_source_dir = config.ACTIVE_JOBS_SOURCE_DIR
        
        if not os.path.exists(active_source_dir):
            return 0
        
        try:
            for root, dirs, files in os.walk(active_source_dir):
                if self.is_cancelled:
                    break
                    
                if "job_data.json" in files:
                    job_data_path = os.path.join(root, "job_data.json")
                    try:
                        with open(job_data_path, 'r', encoding='utf-8') as f:
                            job_data = json.load(f)
                        
                        if self.matches_search_criteria(job_data):
                            self.result_found.emit(job_data, "Active")
                            results_count += 1
                            
                    except Exception as e:
                        continue  # Skip corrupted files
                        
        except Exception as e:
            print(f"Error searching active jobs: {e}")
        
        return results_count
    
    def search_archived_jobs(self):
        """Search through archived jobs"""
        results_count = 0
        archive_dir = config.ARCHIVE_DIR
        
        if not os.path.exists(archive_dir):
            return 0
        
        try:
            for folder_name in os.listdir(archive_dir):
                if self.is_cancelled:
                    break
                    
                job_folder_path = os.path.join(archive_dir, folder_name)
                if os.path.isdir(job_folder_path):
                    metadata_path = os.path.join(job_folder_path, 'job_data.json')
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                job_data = json.load(f)
                            
                            if self.matches_search_criteria(job_data):
                                self.result_found.emit(job_data, "Archive")
                                results_count += 1
                                
                        except Exception as e:
                            continue  # Skip corrupted files
                            
        except Exception as e:
            print(f"Error searching archived jobs: {e}")
        
        return results_count
    
    def matches_search_criteria(self, job_data):
        """Check if job data matches search criteria"""
        if not self.search_terms:
            return True  # Empty search returns all
        
        # List of fields to search
        searchable_fields = [
            job_data.get("Customer", ""),
            job_data.get("Part#", ""),
            job_data.get("Job Ticket#", ""),
            job_data.get("Ticket#", ""),
            job_data.get("PO#", ""),
            job_data.get("Inlay Type", ""),
            job_data.get("Label Size", ""),
            job_data.get("Quantity", ""),
            job_data.get("Qty", ""),
            job_data.get("Status", ""),
            job_data.get("UPC Number", ""),
            job_data.get("Serial Number", ""),
            job_data.get("Due Date", ""),
            job_data.get("dateArchived", ""),
            job_data.get("archivedDate", ""),
            job_data.get("Item", ""),
            job_data.get("LPR", ""),
            job_data.get("Rolls", ""),
        ]
        
        # Combine all searchable text
        combined_text = " ".join(str(field) for field in searchable_fields if field).lower()
        
        # Check if search terms are in the combined text
        search_words = self.search_terms.split()
        
        # For multi-word searches, all words must be present
        for word in search_words:
            if word not in combined_text:
                return False
        
        return True


class GlobalSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Global Job Search")
        self.setModal(True)
        self.setMinimumSize(1000, 700)
        
        self.search_worker = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the global search UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Header section
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Global Job Search")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        subtitle_label = QLabel("Search across all active and archived job data")
        subtitle_label.setStyleSheet("color: #888888;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Search section
        search_group = QGroupBox("Search Parameters")
        search_layout = QVBoxLayout(search_group)
        
        # Search input
        search_input_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search terms (Customer, PO#, Ticket#, UPC, etc.)...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.perform_search)
        self.search_btn.setDefault(True)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_search)
        
        search_input_layout.addWidget(QLabel("Search:"))
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.search_btn)
        search_input_layout.addWidget(self.clear_btn)
        
        search_layout.addLayout(search_input_layout)
        
        # Search options
        options_layout = QHBoxLayout()
        
        self.search_active_check = QCheckBox("Search Active Jobs")
        self.search_active_check.setChecked(True)
        
        self.search_archived_check = QCheckBox("Search Archived Jobs")
        self.search_archived_check.setChecked(True)
        
        options_layout.addWidget(self.search_active_check)
        options_layout.addWidget(self.search_archived_check)
        options_layout.addStretch()
        
        search_layout.addLayout(options_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        search_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(search_group)
        
        # Results section
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)
        
        # Results header
        results_header_layout = QHBoxLayout()
        
        self.results_count_label = QLabel("No search performed yet")
        self.results_count_label.setStyleSheet("font-weight: bold;")
        
        results_header_layout.addWidget(self.results_count_label)
        results_header_layout.addStretch()
        
        results_layout.addLayout(results_header_layout)
        
        # Results table
        self.results_model = JobDataModel()
        self.results_table = QTableView()
        self.results_table.setModel(self.results_model)
        self.results_table.setSortingEnabled(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        
        # Configure column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)           # Customer
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Ticket#
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # PO#
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Part#
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Inlay
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Qty
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # UPC
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)  # Date
        
        # Connect double-click for details
        self.results_table.doubleClicked.connect(self.show_job_details)
        
        results_layout.addWidget(self.results_table)
        
        main_layout.addWidget(results_group)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.export_btn = QPushButton("Export Results")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
    
    def on_search_text_changed(self):
        """Handle search input changes with debouncing"""
        self.search_timer.stop()
        self.search_timer.start(500)  # 500ms delay for auto-search
    
    def perform_search(self):
        """Perform the global search"""
        search_terms = self.search_input.text().strip()
        search_active = self.search_active_check.isChecked()
        search_archived = self.search_archived_check.isChecked()
        
        if not search_active and not search_archived:
            QMessageBox.warning(self, "No Search Sources", 
                              "Please select at least one source to search (Active Jobs or Archived Jobs).")
            return
        
        # Cancel any existing search
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.search_worker.wait()
        
        # Clear previous results
        self.results_model.clear_results()
        self.results_count_label.setText("Searching...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.export_btn.setEnabled(False)
        
        # Start new search
        self.search_worker = GlobalSearchWorker(search_terms, search_active, search_archived)
        self.search_worker.progress_updated.connect(self.update_search_progress)
        self.search_worker.result_found.connect(self.add_search_result)
        self.search_worker.search_completed.connect(self.search_finished)
        self.search_worker.start()
    
    def update_search_progress(self, percentage, message):
        """Update search progress"""
        self.progress_bar.setValue(percentage)
        self.results_count_label.setText(message)
    
    def add_search_result(self, job_data, job_type):
        """Add a job to the search results"""
        self.results_model.add_job_result(job_data, job_type)
    
    def search_finished(self, total_results):
        """Handle search completion"""
        self.progress_bar.setVisible(False)
        
        if total_results > 0:
            self.results_count_label.setText(f"Found {total_results} matching jobs")
            self.export_btn.setEnabled(True)
        else:
            search_terms = self.search_input.text().strip()
            if search_terms:
                self.results_count_label.setText(f"No jobs found matching '{search_terms}'")
            else:
                self.results_count_label.setText(f"Found {total_results} total jobs")
    
    def clear_search(self):
        """Clear search results and input"""
        self.search_input.clear()
        self.results_model.clear_results()
        self.results_count_label.setText("No search performed yet")
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(False)
        
        # Cancel any running search
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
    
    def show_job_details(self, index):
        """Show detailed information for selected job"""
        if not index.isValid():
            return
        
        row = index.row()
        job_data = self.results_model.get_job_data(row)
        
        if not job_data:
            return
        
        # Create a simple details dialog
        details_dialog = QDialog(self)
        details_dialog.setWindowTitle("Job Details")
        details_dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(details_dialog)
        
        # Job details text
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        # Format job data for display
        details_content = []
        details_content.append("JOB DETAILS")
        details_content.append("=" * 50)
        
        for key, value in job_data.items():
            if value:  # Only show non-empty values
                details_content.append(f"{key}: {value}")
        
        details_text.setPlainText("\n".join(details_content))
        layout.addWidget(details_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(details_dialog.accept)
        layout.addWidget(close_btn)
        
        details_dialog.exec()
    
    def export_results(self):
        """Export search results to a text file"""
        if self.results_model.rowCount() == 0:
            QMessageBox.information(self, "No Results", "No search results to export.")
            return
        
        from PySide6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Search Results", 
            f"job_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("GLOBAL JOB SEARCH RESULTS\n")
                f.write("=" * 50 + "\n")
                f.write(f"Search Terms: {self.search_input.text().strip()}\n")
                f.write(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Results: {self.results_model.rowCount()}\n")
                f.write("\n")
                
                # Write headers
                headers = self.results_model.headers
                f.write("\t".join(headers) + "\n")
                f.write("-" * 100 + "\n")
                
                # Write data
                for row in range(self.results_model.rowCount()):
                    row_data = []
                    for col in range(len(headers)):
                        item = self.results_model.item(row, col)
                        row_data.append(item.text() if item else "")
                    f.write("\t".join(row_data) + "\n")
            
            QMessageBox.information(self, "Export Complete", f"Results exported to:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{str(e)}") 