import json
import os
import shutil
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QTableView,
    QHeaderView,
    QSizePolicy,
    QAbstractItemView,
    QMenu,
    QComboBox,
    QDateEdit,
    QPushButton,
    QLabel,
    QLineEdit,
    QFrame,
    QGroupBox,
    QCheckBox,
    QSpacerItem
)

from src.widgets.job_details_dialog import JobDetailsDialog, FileOperationProgressDialog
import src.config as config

from PySide6.QtGui import QStandardItem, QStandardItemModel, QFont, QIcon
from PySide6.QtCore import Qt, QDate, QTimer

class ArchivePageWidget(QWidget):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.archive_dir = config.ARCHIVE_DIR
        
        self.all_jobs = []  # Complete list of archived jobs
        self.filtered_jobs = []  # Currently filtered/searched jobs
        
        # Timer for search debouncing
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.setup_ui()
        self.load_jobs()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # Header section with title and stats
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Job Archive")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Stats labels
        self.stats_label = QLabel("0 jobs found")
        self.stats_label.setStyleSheet("color: #666; font-size: 12px;")
        header_layout.addWidget(self.stats_label)
        
        main_layout.addLayout(header_layout)

        # Search section - prominent and easy to use
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        search_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        search_layout = QVBoxLayout(search_frame)
        
        # Main search bar
        search_row = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setMinimumWidth(60)
        search_row.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search across all job fields (Customer, PO#, Ticket#, Part#, etc.)...")
        self.search_input.setMinimumHeight(35)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_row.addWidget(self.search_input)
        
        self.clear_search_btn = QPushButton("Clear")
        self.clear_search_btn.setMaximumWidth(60)
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_row.addWidget(self.clear_search_btn)
        
        search_layout.addLayout(search_row)
        
        # Quick filter row
        quick_filter_layout = QHBoxLayout()
        quick_filter_layout.addWidget(QLabel("Quick filters:"))
        
        self.customer_filter = QComboBox()
        self.customer_filter.setMaximumWidth(200)
        self.customer_filter.currentTextChanged.connect(self.apply_filters)
        quick_filter_layout.addWidget(self.customer_filter)
        
        # Removed status filter since we don't need the status column
        # self.status_filter = QComboBox()
        # self.status_filter.setMaximumWidth(150)
        # self.status_filter.addItems(["All Status", "New", "In Progress", "Completed", "Archived"])
        # self.status_filter.currentTextChanged.connect(self.apply_filters)
        # quick_filter_layout.addWidget(self.status_filter)
        
        # Advanced filters toggle
        self.show_advanced_btn = QPushButton("Show Date Filters")
        self.show_advanced_btn.setCheckable(True)
        self.show_advanced_btn.setMaximumWidth(130)
        self.show_advanced_btn.clicked.connect(self.toggle_advanced_filters)
        quick_filter_layout.addWidget(self.show_advanced_btn)
        
        quick_filter_layout.addStretch()
        search_layout.addLayout(quick_filter_layout)
        
        main_layout.addWidget(search_frame)

        # Advanced filters section (initially hidden)
        self.advanced_filters_frame = QFrame()
        self.advanced_filters_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.advanced_filters_frame.setVisible(False)
        
        advanced_layout = QHBoxLayout(self.advanced_filters_frame)
        
        advanced_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_from.dateChanged.connect(self.apply_filters)
        advanced_layout.addWidget(self.date_from)

        advanced_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.apply_filters)
        advanced_layout.addWidget(self.date_to)
        
        self.reset_dates_btn = QPushButton("Reset Dates")
        self.reset_dates_btn.clicked.connect(self.reset_date_filters)
        advanced_layout.addWidget(self.reset_dates_btn)
        
        advanced_layout.addStretch()
        
        main_layout.addWidget(self.advanced_filters_frame)

        # Results table
        self.setup_results_table()
        main_layout.addWidget(self.jobs_table)

        self.setLayout(main_layout)

    def setup_results_table(self):
        """Set up the results table with proper formatting and functionality."""
        self.model = QStandardItemModel()
        # Removed Status column, reordered for better space utilization
        # Updated headers: "Inlay Type" → "Inlay", "Label Size" → "Size"
        self.headers = [
            "Customer", "Ticket#", "PO#", "Part#", 
            "Inlay", "Size", "Qty", "Archived Date"
        ]
        self.model.setHorizontalHeaderLabels(self.headers)
        
        self.jobs_table = QTableView()
        self.jobs_table.setModel(self.model)
        self.jobs_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setSortingEnabled(True)
        self.jobs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.jobs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.jobs_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Configure column widths for better visibility
        header = self.jobs_table.horizontalHeader()
        # Customer gets more space and stretches
        header.setSectionResizeMode(self.headers.index("Customer"), QHeaderView.ResizeMode.Stretch)
        header.resizeSection(self.headers.index("Customer"), 180)  # Set minimum width
        
        # Other columns resize to content but with reasonable limits
        header.setSectionResizeMode(self.headers.index("Ticket#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("PO#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Part#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Inlay"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Size"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Qty"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Archived Date"), QHeaderView.ResizeMode.ResizeToContents)
        
        self.jobs_table.verticalHeader().hide()

        # Connect double-click signal for job details
        self.jobs_table.doubleClicked.connect(self.open_job_details)

    def on_search_text_changed(self):
        """Handle search input changes with debouncing."""
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms delay for debouncing

    def perform_search(self):
        """Perform the actual search and filtering."""
        self.apply_filters()

    def clear_search(self):
        """Clear the search input and reset filters."""
        self.search_input.clear()
        self.customer_filter.setCurrentIndex(0)
        # Removed status filter reset since we removed the status filter
        # self.status_filter.setCurrentIndex(0)
        self.apply_filters()

    def toggle_advanced_filters(self):
        """Toggle visibility of advanced date filters."""
        is_visible = self.advanced_filters_frame.isVisible()
        self.advanced_filters_frame.setVisible(not is_visible)
        self.show_advanced_btn.setText("Hide Date Filters" if not is_visible else "Show Date Filters")

    def reset_date_filters(self):
        """Reset date filters to default range."""
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_to.setDate(QDate.currentDate())
        self.apply_filters()

    def apply_filters(self):
        """Apply all active filters and search criteria."""
        self.model.removeRows(0, self.model.rowCount())
        self.filtered_jobs = []
        
        search_text = self.search_input.text().lower().strip()
        customer_filter = self.customer_filter.currentText()
        # Removed status_filter since we don't need the status column
        # status_filter = self.status_filter.currentText()
        date_from = self.date_from.date()
        date_to = self.date_to.date()
        use_date_filter = self.advanced_filters_frame.isVisible()
        
        for job in self.all_jobs:
            # Search filter - search across all relevant fields
            if search_text:
                searchable_fields = [
                    job.get("Customer", ""),
                    job.get("Part#", ""),
                    job.get("Job Ticket#", ""),
                    job.get("Ticket#", ""),  # Handle both field names
                    job.get("PO#", ""),
                    job.get("Inlay Type", ""),
                    job.get("Label Size", ""),
                    job.get("Quantity", ""),
                    job.get("Qty", ""),  # Handle both field names
                    job.get("Status", ""),
                    job.get("UPC Number", ""),
                    job.get("Serial Number", ""),
                    job.get("Due Date", ""),
                ]
                
                # Combine all searchable text
                combined_text = " ".join(str(field) for field in searchable_fields if field).lower()
                
                if search_text not in combined_text:
                    continue
            
            # Customer filter
            if customer_filter != "All Customers" and job.get("Customer") != customer_filter:
                continue
            
            # Removed status filter
            # if status_filter != "All Status" and job.get("Status") != status_filter:
            #     continue
            
            # Date filter (only if advanced filters are shown)
            if use_date_filter:
                # Try multiple date field names for archive date
                archive_date_str = ""
                
                # First try the full timestamp field
                date_with_time = job.get('dateArchived', '')
                if date_with_time:
                    if ' ' in date_with_time:
                        archive_date_str = date_with_time.split(' ')[0]  # Extract date part
                    else:
                        archive_date_str = date_with_time
                
                # If no dateArchived, try the date-only field
                if not archive_date_str:
                    archive_date_str = job.get('archivedDate', '')
                
                # If still no date, try legacy field names
                if not archive_date_str:
                    archive_date_str = job.get('archived_date', '')
                
                if archive_date_str:
                    try:
                        # Parse the date string (expecting yyyy-mm-dd format)
                        if len(archive_date_str) >= 10:
                            date_part = archive_date_str[:10]  # Take first 10 chars (yyyy-mm-dd)
                            archive_date = QDate.fromString(date_part, 'yyyy-MM-dd')
                            if archive_date.isValid() and not (date_from <= archive_date <= date_to):
                                continue
                    except Exception as e:
                        print(f"Error parsing archive date '{archive_date_str}': {e}")
                        continue  # Skip jobs with invalid dates
            
            # Job passed all filters
            self.filtered_jobs.append(job)
            self.add_job_to_table(job)
        
        # Update stats
        total_jobs = len(self.all_jobs)
        filtered_count = len(self.filtered_jobs)
        
        if search_text or customer_filter != "All Customers" or use_date_filter:
            self.stats_label.setText(f"{filtered_count} of {total_jobs} jobs found")
        else:
            self.stats_label.setText(f"{total_jobs} archived jobs")

    def add_job_to_table(self, job_data):
        """Add a job to the results table."""
        # Handle both old and new field names for compatibility
        ticket_num = job_data.get("Ticket#", job_data.get("Job Ticket#", ""))
        quantity = job_data.get("Qty", job_data.get("Quantity", ""))
        
        # Format quantity with commas if it's a number
        if quantity and str(quantity).replace(",", "").isdigit():
            quantity = f"{int(str(quantity).replace(',', '')):,}"
        
        # Handle archived date display - try multiple field names and format properly
        archived_date = ""
        
        # First try the full timestamp
        date_with_time = job_data.get("dateArchived", "")
        if date_with_time:
            try:
                if " " in date_with_time:
                    # Extract just the date part from timestamp
                    archived_date = date_with_time.split()[0]
                else:
                    archived_date = date_with_time
            except Exception:
                archived_date = date_with_time
        
        # If no dateArchived, try the date-only field
        if not archived_date:
            archived_date = job_data.get("archivedDate", "")
        
        # If still no date, try legacy field names
        if not archived_date:
            archived_date = job_data.get("archived_date", "")
        
        # Format the date for better display if it's in ISO format
        if archived_date and len(archived_date) >= 10:
            try:
                # Try to parse and reformat if it's in yyyy-mm-dd format
                if archived_date[4] == '-' and archived_date[7] == '-':
                    date_obj = datetime.strptime(archived_date[:10], '%Y-%m-%d')
                    archived_date = date_obj.strftime('%m/%d/%Y')  # Convert to MM/DD/YYYY
            except Exception:
                # If parsing fails, keep the original format
                pass
        
        # If still no date, show current date as fallback (shouldn't happen with proper archiving)
        if not archived_date:
            archived_date = datetime.now().strftime('%m/%d/%Y')
            print(f"Warning: No archive date found for job {ticket_num}, using current date")
        
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(ticket_num),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(str(quantity)),
            QStandardItem(archived_date)
        ]
        self.model.appendRow(row_items)

    def load_jobs(self):
        """Load all archived jobs from the archive directory."""
        self.all_jobs = []
        
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)
            print(f"Created archive directory: {self.archive_dir}")
            self.update_ui_after_load()
            return
        
        print(f"Loading archived jobs from: {self.archive_dir}")
        job_count = 0
        
        for folder_name in os.listdir(self.archive_dir):
            job_folder_path = os.path.join(self.archive_dir, folder_name)
            if os.path.isdir(job_folder_path):
                metadata_path = os.path.join(job_folder_path, 'job_data.json')
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            job_data = json.load(f)
                            # Ensure the path is correct for operations like deletion
                            job_data['job_folder_path'] = job_folder_path
                            self.all_jobs.append(job_data)
                            job_count += 1
                    except Exception as e:
                        print(f"Error loading job data from {metadata_path}: {e}")
        
        print(f"Loaded {job_count} archived jobs")
        self.update_ui_after_load()

    def update_ui_after_load(self):
        """Update UI components after loading jobs."""
        self.populate_customer_filter()
        self.apply_filters()

    def populate_customer_filter(self):
        """Populate the customer filter dropdown with unique customers."""
        customers = sorted(list(set(job.get('Customer', '') for job in self.all_jobs if job.get('Customer'))))
        
        self.customer_filter.clear()
        self.customer_filter.addItem("All Customers")
        self.customer_filter.addItems(customers)

    def add_archived_job(self, job_data):
        """Add a new job to the archive (called from the jobs page)."""
        job_folder_path = job_data.get('job_folder_path')
        if not job_folder_path or not os.path.exists(job_folder_path):
            QMessageBox.warning(self, "Archive Error", "Original job folder not found. Cannot archive.")
            return

        # Destination for the job folder in the archive directory
        destination_folder_name = os.path.basename(job_folder_path)
        destination_path = os.path.join(self.archive_dir, destination_folder_name)

        # Check if destination already exists
        if os.path.exists(destination_path):
            QMessageBox.warning(
                self, 
                "Archive Error", 
                f"A job with the same name already exists in the archive: {destination_folder_name}"
            )
            return

        # Store job data for later use in callback
        self.temp_archive_job_data = job_data.copy()
        self.temp_archive_destination = destination_path

        # Use threaded file operation for potentially large moves
        progress_dialog = FileOperationProgressDialog(
            'move', job_folder_path, destination_path, job_data, self
        )
        
        # Connect completion signal
        progress_dialog.operation_finished.connect(self.on_archive_operation_finished)
        
        # Show the dialog
        progress_dialog.exec()

    def on_archive_operation_finished(self, success, message):
        """Handle completion of archive operation."""
        if not hasattr(self, 'temp_archive_job_data'):
            return
            
        job_data = self.temp_archive_job_data
        destination_path = self.temp_archive_destination
        
        # Clean up temporary data
        delattr(self, 'temp_archive_job_data')
        delattr(self, 'temp_archive_destination')
        
        if success:
            try:
                # Update the job's folder path to its new location
                job_data['job_folder_path'] = destination_path
                
                # Ensure archived date is properly set with current timestamp
                current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                job_data['dateArchived'] = current_timestamp
                
                # Also store just the date part for easier filtering/display
                job_data['archivedDate'] = datetime.now().strftime('%Y-%m-%d')
                
                # Ensure status is set to archived
                job_data['Status'] = 'Archived'
                
                print(f"Setting archive date: {current_timestamp}")
                
                # Save the job metadata inside the newly moved folder
                metadata_path = os.path.join(destination_path, 'job_data.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(job_data, f, indent=4)
                
                print(f"Saved archive metadata to: {metadata_path}")
                
                # Add to the archive list and refresh display
                self.all_jobs.append(job_data)
                self.update_ui_after_load()
                
                QMessageBox.information(self, "Success", f"Job archived successfully:\n{destination_path}")
                
            except Exception as e:
                print(f"Error updating archive metadata: {e}")
                QMessageBox.critical(self, "Archive Error", f"Job moved but could not update metadata:\n{e}")
        else:
            QMessageBox.critical(self, "Archive Error", f"Could not move job to archive:\n{message}")

    def open_job_details(self, index):
        """Open job details dialog when a job is double-clicked."""
        if not index.isValid():
            return

        row = index.row()
        job_data = self._get_job_data_for_row(row)
        
        if not job_data:
            QMessageBox.warning(self, "Error", "Could not retrieve job data.")
            return

        dialog = JobDetailsDialog(job_data, self.base_path, self)
        dialog.setWindowTitle(f"Archived Job Details - {job_data.get('Job Ticket#', job_data.get('Ticket#', 'N/A'))}")
        
        # Make the dialog read-only for archived jobs
        dialog.edit_btn.setEnabled(False)
        dialog.edit_btn.setToolTip("Editing is disabled for archived jobs")
        
        # Disable specific action buttons for archived jobs
        if hasattr(dialog, 'complete_btn'):
            dialog.complete_btn.setEnabled(False)
        
        if hasattr(dialog, 'archive_btn'):
            dialog.archive_btn.setEnabled(False)

        dialog.exec()

    def _get_job_data_for_row(self, row):
        """Get the full job data for a specific table row."""
        if row < 0 or row >= len(self.filtered_jobs):
            return None

        # Since we're displaying filtered jobs in order, we can directly index
        return self.filtered_jobs[row]

    def delete_selected_job(self):
        """Delete the selected archived job."""
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
        
        reply = QMessageBox.question(
            self, "Delete Archived Job", 
            "Are you sure you want to permanently delete this archived job?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        selected_row_index = selection_model.selectedRows()[0]
        job_to_remove = self._get_job_data_for_row(selected_row_index.row())
        
        if not job_to_remove:
            QMessageBox.warning(self, "Error", "Could not find job data to delete.")
            return
        
        job_folder_path = job_to_remove.get('job_folder_path')
        if job_folder_path and os.path.exists(job_folder_path):
            # Store data for callback
            self.temp_delete_job_data = job_to_remove
            self.temp_delete_row_index = selected_row_index.row()
            
            # Use threaded deletion for potentially large folders
            progress_dialog = FileOperationProgressDialog(
                'delete', job_folder_path, None, job_to_remove, self
            )
            
            # Connect completion signal
            progress_dialog.operation_finished.connect(self.on_delete_operation_finished)
            
            # Show the dialog
            progress_dialog.exec()
        else:
            QMessageBox.warning(self, "Delete Error", "Could not find job folder to delete.")

    def on_delete_operation_finished(self, success, message):
        """Handle completion of delete operation."""
        if not hasattr(self, 'temp_delete_job_data'):
            return
            
        job_to_remove = self.temp_delete_job_data
        row_index = self.temp_delete_row_index
        
        # Clean up temporary data
        delattr(self, 'temp_delete_job_data')
        delattr(self, 'temp_delete_row_index')
        
        if success:
            # Remove from the main jobs list
            job_folder_path = job_to_remove.get('job_folder_path')
            self.all_jobs = [j for j in self.all_jobs if j.get('job_folder_path') != job_folder_path]
            
            # Refresh the display
            self.apply_filters()
            
            QMessageBox.information(self, "Deleted", "Archived job has been permanently deleted.")
        else:
            QMessageBox.critical(self, "Delete Error", f"Could not delete job folder:\n{message}")

    def contextMenuEvent(self, event):
        """Handle right-click context menu."""
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
            
        menu = QMenu(self)
        menu.addAction("View Details", lambda: self.open_job_details(selection_model.selectedRows()[0]))
        menu.addSeparator()
        menu.addAction("Delete Job", self.delete_selected_job)
        menu.exec(event.globalPos())

    def save_data(self):
        """Legacy method - data is now saved as individual JSON files."""
        pass
