import os
import json
import time
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QTableView,
    QMessageBox,
    QLineEdit,
    QFormLayout,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QMenu,
    QHeaderView,
    QSizePolicy,
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QLabel,
    QTextEdit,
)
import fitz
import pymupdf, shutil, os, sys
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt, Signal, QFileSystemWatcher, QTimer, QThread, QObject, QSortFilterProxyModel
from src.wizards.new_job_wizard import NewJobWizard
from src.widgets.job_details_dialog import JobDetailsDialog, EPCProgressDialog, FileOperationProgressDialog, PDFProgressDialog
from src.widgets.interactive_roll_tracker_dialog import InteractiveRollTrackerDialog
import src.config as config
from src.utils.epc_conversion import (
    create_upc_folder_structure,
    generate_epc_database_files,
    generate_epc_database_files_with_progress,
    validate_upc,
    calculate_total_quantity_with_percentages,
)
from src.utils.roll_tracker import generate_quality_control_sheet
import re
from src.utils.template_mapping import get_template_manager


class JobLoaderWorker(QObject):
    """Worker to load job data from the filesystem in a background thread."""
    jobs_loaded = Signal(list)
    error = Signal(str)

    def __init__(self, source_dir):
        super().__init__()
        self.source_dir = source_dir
        self.is_cancelled = False

    def run(self):
        """Scan the source directory for job_data.json files, skipping archived jobs."""
        jobs = []
        if not os.path.exists(self.source_dir):
            self.error.emit(f"Source directory not found: {self.source_dir}")
            return

        try:
            for root, _, files in os.walk(self.source_dir):
                if self.is_cancelled:
                    return

                if "job_data.json" in files:
                    job_data_path = os.path.join(root, "job_data.json")
                    try:
                        with open(job_data_path, "r", encoding="utf-8") as f:
                            job_data = json.load(f)
                        
                        # Critical Fix: Do not load jobs marked as 'Archived'
                        if job_data.get('Status') == 'Archived':
                            print(f"Skipping archived job found in active directory: {job_data_path}")
                            continue

                        # Add the canonical path from the filesystem
                        job_data["active_source_folder_path"] = root
                        jobs.append(job_data)
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON from {job_data_path}")
                    except Exception as e:
                        print(f"Error loading job from {job_data_path}: {e}")
            
            if not self.is_cancelled:
                self.jobs_loaded.emit(jobs)

        except Exception as e:
            self.error.emit(f"Failed to scan job directory: {e}")

    def cancel(self):
        self.is_cancelled = True


class JobPageWidget(QWidget):
    job_to_archive = Signal(dict)
    job_created = Signal()  # New signal for job creation

    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.save_file = os.path.join(self.base_path, "data", "active_jobs.json")
        self.network_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        self.all_jobs = []  # This will be the source of truth
        self.is_loading = False # Flag to prevent concurrent loads

        # Initialize file system watcher for real-time monitoring
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.directoryChanged.connect(self.on_directory_changed)

        # Timer to debounce rapid file system changes
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_jobs_table)

        layout = QVBoxLayout(self)

        actions_layout = QHBoxLayout()
        self.add_job_button = QPushButton("Add Job")
        self.add_job_button.clicked.connect(self.open_new_job_wizard)
        
        # Add manual refresh button
        self.refresh_button = QPushButton("Refresh Jobs")
        self.refresh_button.clicked.connect(self.manual_refresh_jobs)
        self.refresh_button.setToolTip("Manually refresh the job list from disk")
        
        # Add debug button for troubleshooting (commented out for production)
        # self.debug_button = QPushButton("Debug Info")
        # self.debug_button.clicked.connect(self.show_debug_info)

        actions_layout.addWidget(self.add_job_button)
        actions_layout.addWidget(self.refresh_button)
        # actions_layout.addWidget(self.debug_button)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Create source model
        self.source_model = QStandardItemModel()
        self.headers = [
            "Customer",
            "Part#",
            "Ticket#",
            "PO#",
            "Inlay Type",
            "Label Size",
            "Qty",
            "Due Date",
        ]
        self.source_model.setHorizontalHeaderLabels(self.headers)

        # Create proxy model for sorting
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)

        self.jobs_table = QTableView()
        self.jobs_table.setModel(self.proxy_model)  # Set proxy model instead of source model
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setSortingEnabled(True)
        self.jobs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.jobs_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.jobs_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.jobs_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        header = self.jobs_table.horizontalHeader()
        header.setSectionResizeMode(
            self.headers.index("Customer"), QHeaderView.ResizeMode.Stretch
        )
        header.resizeSection(self.headers.index("Customer"), 200)
        header.setSectionResizeMode(
            self.headers.index("Part#"), QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self.headers.index("Ticket#"), QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self.headers.index("PO#"), QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self.headers.index("Inlay Type"), QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self.headers.index("Label Size"), QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self.headers.index("Qty"), QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            self.headers.index("Due Date"), QHeaderView.ResizeMode.ResizeToContents
        )
        self.jobs_table.verticalHeader().hide()

        layout.addWidget(self.jobs_table)
        self.setLayout(layout)

        self.load_jobs()
        self.setup_directory_monitoring()

        # Add double-click handler for the table
        self.jobs_table.doubleClicked.connect(self.open_job_details)

    def setup_directory_monitoring(self):
        """Set up file system monitoring for the active jobs source directory with performance optimizations."""
        active_source_dir = config.ACTIVE_JOBS_SOURCE_DIR
        
        # Check if monitoring is disabled in settings
        if not config.ENABLE_FILE_MONITORING:
            print("File system monitoring is DISABLED in settings")
            print("Jobs will only refresh on application startup or manual refresh")
            return

        # Ensure the directory exists
        if not os.path.exists(active_source_dir):
            os.makedirs(active_source_dir, exist_ok=True)
            print(f"Created active jobs source directory: {active_source_dir}")

        # Performance optimization: Only monitor if it's a local directory
        # Network drives (like Z:) can be unreliable and cause performance issues
        if self.is_network_drive(active_source_dir):
            print(f"WARNING: Monitoring network drive detected: {active_source_dir}")
            print("Network drive monitoring may cause performance issues with multiple users.")
            print("Consider using periodic refresh instead of real-time monitoring.")
            
            # For network drives, use less aggressive monitoring
            self.setup_limited_network_monitoring(active_source_dir)
        else:
            # For local drives, use full monitoring
            self.setup_full_local_monitoring(active_source_dir)

    def is_network_drive(self, path):
        """Check if the path is on a network drive."""
        import os
        if os.name == 'nt':  # Windows
            drive = os.path.splitdrive(path)[0]
            # Check if it's a mapped network drive (typically Z:, Y:, etc.)
            if drive and len(drive) == 2 and drive[1] == ':':
                return drive.upper() in ['Z:', 'Y:', 'X:', 'W:', 'V:', 'U:', 'T:', 'S:', 'R:', 'Q:', 'P:', 'O:', 'N:', 'M:', 'L:', 'K:', 'J:', 'I:', 'H:', 'G:', 'F:']
            # UNC paths (\\server\share)
            return path.startswith('\\\\')
        return False

    def setup_limited_network_monitoring(self, active_source_dir):
        """Setup limited monitoring for network drives to avoid performance issues."""
        print("Setting up LIMITED network monitoring (performance mode)")
        
        # DO NOT use the file watcher for network drives, it's unreliable and slow.
        # Rely on periodic refresh and manual refresh instead.
        
        # Schedule periodic refresh for network drives
        if not hasattr(self, 'periodic_refresh_timer'):
            from PySide6.QtCore import QTimer
            self.periodic_refresh_timer = QTimer()
            self.periodic_refresh_timer.timeout.connect(self.periodic_refresh)
            self.periodic_refresh_timer.start(config.PERIODIC_REFRESH_INTERVAL)
            print(f"Enabled periodic refresh every {config.PERIODIC_REFRESH_INTERVAL//1000} seconds for network drive")

    def setup_full_local_monitoring(self, active_source_dir):
        """Setup full monitoring for local drives."""
        print("Setting up FULL local monitoring")
        
        # Add the main directory to watcher
        if active_source_dir not in self.file_watcher.directories():
            success = self.file_watcher.addPath(active_source_dir)
            if success:
                print(f"Successfully started monitoring: {active_source_dir}")
            else:
                print(f"Failed to monitor: {active_source_dir}")

        # Monitor subdirectories but with configured limits
        self.add_subdirectories_to_watcher_limited(active_source_dir)
        
        # Use configured debounce timer for local drives
        self.refresh_timer.setInterval(config.REFRESH_DEBOUNCE_MS)
        print(f"Local debounce timer set to: {config.REFRESH_DEBOUNCE_MS}ms")

    def add_subdirectories_to_watcher_limited(self, directory, max_depth=None, max_directories=None):
        """Recursively add subdirectories with configurable limits to prevent performance issues."""
        # Use configured limits or defaults
        if max_depth is None:
            max_depth = config.MAX_MONITORING_DEPTH
        if max_directories is None:
            max_directories = config.MAX_MONITORED_DIRECTORIES
            
        try:
            monitored_count = 0
            for root, dirs, files in os.walk(directory):
                # Limit monitoring depth
                depth = root.replace(directory, '').count(os.sep)
                if depth >= max_depth:
                    dirs[:] = []  # Don't recurse deeper
                    continue
                
                # Limit total monitored directories
                if monitored_count >= max_directories:
                    print(f"Reached monitoring limit of {max_directories} directories (configurable)")
                    break
                
                if root not in self.file_watcher.directories():
                    success = self.file_watcher.addPath(root)
                    if success:
                        monitored_count += 1
                        if monitored_count <= 10:  # Only log first 10 to avoid spam
                            print(f"Added to monitoring: {root}")
                        elif monitored_count == 11:
                            print("... (additional directories added, logging suppressed)")
                    else:
                        print(f"Failed to add to monitoring: {root}")
                        
        except Exception as e:
            print(f"Error adding subdirectories to watcher: {e}")
        
        print(f"Total directories being monitored: {len(self.file_watcher.directories())} (max: {max_directories})")

    def manual_refresh_jobs(self):
        """Manually refresh the jobs table - useful when monitoring is disabled or unreliable."""
        print("=== Manual refresh triggered by user ===")
        self.load_jobs_in_background()

    def periodic_refresh(self):
        """Periodic refresh for network drives where file system watching is unreliable."""
        print("Performing periodic refresh for network drive...")
        self.refresh_jobs_table()

    def on_directory_changed(self, path):
        """Handle directory change events from the file system watcher."""
        print(f"Directory changed detected: {path}")

        # Re-add any new subdirectories to the watcher (only if not network drive)
        if not self.is_network_drive(config.ACTIVE_JOBS_SOURCE_DIR):
            self.add_subdirectories_to_watcher_limited(config.ACTIVE_JOBS_SOURCE_DIR)

        # Use timer to debounce rapid changes - interval set during setup
        self.refresh_timer.start()
        print(f"Refresh timer started ({self.refresh_timer.interval()}ms delay)")

    def refresh_jobs_table(self):
        """Refresh the jobs table by reloading data from the file system."""
        print("=== Refreshing jobs table due to file system changes ===")
        self.load_jobs_in_background()

    def restore_table_selection(self, job_identifiers):
        """Restore table selection based on job ticket and PO number."""
        job_ticket, po_num = job_identifiers
        for row in range(self.model.rowCount()):
            row_job_ticket = self.model.item(row, self.headers.index("Ticket#")).text()
            row_po_num = self.model.item(row, self.headers.index("PO#")).text()
            if row_job_ticket == job_ticket and row_po_num == po_num:
                self.jobs_table.selectRow(row)
                break

    def open_new_job_wizard(self):
        wizard = NewJobWizard(self, base_path=self.base_path)
        wizard.setWindowTitle("New Job")

        if wizard.exec():
            job_data = wizard.get_data()
            
            # Check for duplicates BEFORE creating any folders or files
            is_duplicate, conflict_type, conflicting_job = self.check_for_duplicate_job(job_data)
            
            if is_duplicate:
                # Show appropriate error message and abort job creation
                customer = job_data.get("Customer", "")
                po_number = job_data.get("PO#", "")
                job_ticket = job_data.get("Ticket#", job_data.get("Job Ticket#", ""))
                upc_number = job_data.get("UPC Number", "")
                
                if conflict_type == "ticket_duplicate":
                    conflict_customer = conflicting_job.get("Customer", "")
                    conflict_po = conflicting_job.get("PO#", "")
                    conflict_ticket = conflicting_job.get("Ticket#", conflicting_job.get("Job Ticket#", ""))
                    
                    QMessageBox.warning(
                        self, 
                        "Duplicate Ticket Number",
                        f"Cannot create job - a job with the same Ticket# already exists:\n\n"
                        f"Your Job:\n"
                        f"  Customer: {customer}\n"
                        f"  Ticket#: {job_ticket}\n\n"
                        f"Existing Job:\n"
                        f"  Customer: {conflict_customer}\n"
                        f"  PO#: {conflict_po}\n"
                        f"  Ticket#: {conflict_ticket}\n\n"
                        f"Ticket numbers must be unique. Please use a different ticket number."
                    )
                elif conflict_type == "upc_conflict":
                    conflict_customer = conflicting_job.get("Customer", "")
                    conflict_po = conflicting_job.get("PO#", "")
                    conflict_ticket = conflicting_job.get("Ticket#", conflicting_job.get("Job Ticket#", ""))
                    
                    QMessageBox.warning(
                        self,
                        "UPC Number Conflict",
                        f"Cannot create job - the UPC number '{upc_number}' is already in use:\n\n"
                        f"Your Job:\n"
                        f"  Customer: {customer}\n"
                        f"  UPC: {upc_number}\n\n"
                        f"Existing Job:\n"
                        f"  Customer: {conflict_customer}\n"
                        f"  PO#: {conflict_po}\n"
                        f"  Ticket#: {conflict_ticket}\n\n"
                        f"Please use a different UPC number."
                    )
                
                print(f"Job creation aborted - {conflict_type} detected")
                return  # Exit without creating the job
            
            # No duplicates detected - proceed with job creation
            print(f"No duplicates found - proceeding with job creation")
            job_created = self.create_job_folder_and_checklist(job_data)

            if job_created:
                # Let the file system watcher automatically detect and add the new job
                # No manual add_job_to_table() call needed - this prevents duplicates
                self.ensure_directory_monitoring()
                # No longer need to call save_data() as persistence is handled by folder creation
                print(
                    "Job created successfully - will be automatically detected by file system monitor"
                )
        else:
            print("job not created")

    def check_for_duplicate_job(self, job_data):
        """
        Check if the job data represents a duplicate of an existing job.
        Returns (is_duplicate, conflict_type, conflicting_job) tuple.
        
        Duplicate logic:
        1. Same Ticket# = TRUE DUPLICATE (not allowed) - ticket numbers must be unique
        2. Same UPC Number (if provided) = UPC CONFLICT (not allowed)
        3. Same PO# + Different Ticket# = ALLOWED (multiple tickets can share PO#)
        """
        customer = job_data.get("Customer", "").strip()
        po_number = job_data.get("PO#", "").strip()
        upc_number = job_data.get("UPC Number", "").strip()
        job_ticket = job_data.get("Ticket#", job_data.get("Job Ticket#", "")).strip()
        
        # Skip empty ticket numbers for meaningful duplicate detection
        if not job_ticket:
            return False, None, None
        
        for existing_job in self.all_jobs:
            existing_customer = existing_job.get("Customer", "").strip()
            existing_po = existing_job.get("PO#", "").strip()
            existing_upc = existing_job.get("UPC Number", "").strip()
            existing_ticket = existing_job.get("Ticket#", existing_job.get("Job Ticket#", "")).strip()
            
            # Check for exact ticket number match (primary duplicate check)
            if job_ticket and existing_ticket and job_ticket == existing_ticket:
                return True, "ticket_duplicate", existing_job
            
            # Check for UPC conflict (if both have UPC numbers)
            if (upc_number and existing_upc and 
                upc_number == existing_upc):
                return True, "upc_conflict", existing_job
        
        return False, None, None

    def add_job_to_table(self, job_data):
        """Add job to table with comprehensive duplicate checking."""
        job_ticket = job_data.get("Ticket#", job_data.get("Job Ticket#", ""))
        po_number = job_data.get("PO#", "")
        customer = job_data.get("Customer", "")
        upc_number = job_data.get("UPC Number", "")
        
        print(f"=== Attempting to add job to table ===")
        print(f"  Customer: {customer}")
        print(f"  Ticket#: {job_ticket}")
        print(f"  PO#: {po_number}")
        print(f"  UPC: {upc_number}")
        print(f"  Current table size: {len(self.all_jobs)} jobs")

        # Check for duplicates using the comprehensive method
        is_duplicate, conflict_type, conflicting_job = self.check_for_duplicate_job(job_data)
        
        if is_duplicate:
            conflict_customer = conflicting_job.get("Customer", "")
            conflict_po = conflicting_job.get("PO#", "")
            conflict_ticket = conflicting_job.get("Ticket#", conflicting_job.get("Job Ticket#", ""))
            conflict_upc = conflicting_job.get("UPC Number", "")
            
            if conflict_type == "ticket_duplicate":
                print(f"DUPLICATE REJECTED: Ticket# {job_ticket} already exists")
                print(f"  Existing job: {conflict_customer} - PO#{conflict_po} - Ticket#{conflict_ticket}")
                QMessageBox.warning(
                    self, 
                    "Duplicate Ticket Number",
                    f"A job with the same Ticket# already exists:\n\n"
                    f"Existing Job:\n"
                    f"  Customer: {conflict_customer}\n"
                    f"  PO#: {conflict_po}\n"
                    f"  Ticket#: {conflict_ticket}\n\n"
                    f"Ticket numbers must be unique. Please use a different ticket number."
                )
                return False
            
            elif conflict_type == "upc_conflict":
                print(f"UPC CONFLICT REJECTED: UPC {upc_number} already in use")
                print(f"  Existing job: {conflict_customer} - PO#{conflict_po} - Ticket#{conflict_ticket}")
                QMessageBox.warning(
                    self,
                    "UPC Number Conflict",
                    f"The UPC number '{upc_number}' is already in use by another job:\n\n"
                    f"Existing Job:\n"
                    f"  Customer: {conflict_customer}\n"
                    f"  PO#: {conflict_po}\n"
                    f"  Ticket#: {conflict_ticket}\n\n"
                    f"Each UPC number must be unique. Please use a different UPC number."
                )
                return False
        
        # If we get here, it's not a duplicate - proceed with adding
        print(f"  No conflicts found - proceeding to add job")

        # Format the due date to mm/dd/yyyy
        due_date_formatted = self.format_date_for_display(job_data.get("Due Date", ""))

        # Handle both old and new column names for backward compatibility
        quantity = job_data.get("Qty", job_data.get("Quantity", ""))

        # Format quantity with commas for display in table
        formatted_quantity = quantity
        if quantity and str(quantity).isdigit():
            formatted_quantity = f"{int(quantity):,}"

        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_ticket),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(formatted_quantity),
            QStandardItem(due_date_formatted),
        ]
        
        # Store the complete job data in the first column's item
        row_items[0].setData(job_data, Qt.ItemDataRole.UserRole)
        
        self.source_model.appendRow(row_items)
        # Add the full job data to our source of truth list
        self.all_jobs.append(job_data)
        print(f"SUCCESS: Added job to table - Customer: {customer}, PO#: {po_number}, Ticket#: {job_ticket}")
        print(f"Table now contains {len(self.all_jobs)} jobs")
        return True

    def format_date_for_display(self, date_string):
        """Convert date from ISO format (yyyy-mm-dd) to mm/dd/yyyy format."""
        if not date_string:
            return ""

        try:
            # Parse the ISO date format (yyyy-mm-dd)
            from datetime import datetime

            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            # Format as mm/dd/yyyy
            return date_obj.strftime("%m/%d/%Y")
        except ValueError:
            # If parsing fails, return the original string
            return date_string

    def load_jobs(self):
        """
        Loads jobs by scanning the ACTIVE_JOBS_SOURCE_DIR for job_data.json files.
        This is now the single source of truth for active jobs on startup.
        """
        # This method now starts the background loading process.
        self.load_jobs_in_background()

    def load_jobs_in_background(self):
        """Loads jobs in a background thread to prevent UI freezing."""
        if self.is_loading:
            print("Job loading already in progress. Skipping.")
            return

        print("Starting background job load...")
        self.is_loading = True
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")

        active_source_dir = config.ACTIVE_JOBS_SOURCE_DIR
        
        # Setup worker thread
        self.load_thread = QThread()
        self.worker = JobLoaderWorker(active_source_dir)
        self.worker.moveToThread(self.load_thread)
        
        # Connect signals
        self.load_thread.started.connect(self.worker.run)
        self.worker.jobs_loaded.connect(self.on_jobs_loaded)
        self.worker.error.connect(self.on_load_error)
        
        # Clean up thread
        self.worker.jobs_loaded.connect(self.load_thread.quit)
        self.worker.error.connect(self.load_thread.quit)
        self.load_thread.finished.connect(self.load_thread.deleteLater)
        self.worker.jobs_loaded.connect(self.worker.deleteLater)

        # Start the thread
        self.load_thread.start()

    def on_jobs_loaded(self, loaded_jobs):
        """Slot to handle the list of jobs loaded by the worker thread."""
        print(f"Background load complete. Found {len(loaded_jobs)} jobs.")

        # Preserve selection
        current_selection = None
        selection_model = self.jobs_table.selectionModel()
        if selection_model.hasSelection():
            selected_row = selection_model.selectedRows()[0].row()
            if 0 <= selected_row < len(self.all_jobs):
                current_job = self.all_jobs[selected_row]
                current_selection = (
                    self.get_job_data_value(current_job, "Ticket#", "Job Ticket#"),
                    current_job.get("PO#"),
                )

        # Clear existing data
        self.all_jobs = []
        self.source_model.removeRows(0, self.source_model.rowCount())

        # Add jobs to table (with duplicate checks)
        for job_data in loaded_jobs:
            self.add_job_to_table(job_data)
        
        # Restore selection
        if current_selection:
            self.restore_table_selection(current_selection)
        
        self.on_load_finished()

    def on_load_error(self, error_message):
        """Slot to handle errors from the worker thread."""
        print(f"Error loading jobs: {error_message}")
        QMessageBox.warning(self, "Load Error", f"Could not load jobs:\n{error_message}")
        self.on_load_finished()

    def on_load_finished(self):
        """Common cleanup after loading finishes or fails."""
        self.is_loading = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Jobs")
        print("Job loading process finished.")
        
    def save_data(self):
        """
        This function is deprecated. Job data is now managed directly as files
        in the user-selected directory and the active jobs source directory.
        """
        pass

    def contextMenuEvent(self, event):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return

        menu = QMenu(self)

        # Get the correct source index for the selected row
        proxy_index = selection_model.selectedRows()[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        
        # Get job data using the source index
        job_data = self.source_model.item(source_index.row(), 0).data(Qt.ItemDataRole.UserRole)

        menu.addAction(
            "Create Job Folder...",
            self.create_folder_for_selected_job_with_location_picker,
        )
        menu.addAction("Edit Job", lambda: self.edit_selected_job_in_details(source_index))
        menu.addSeparator()

        # Add Roll Tracker option
        menu.addAction("Open Roll Tracker", lambda: self.open_roll_tracker_for_job(job_data))
        menu.addSeparator()

        # Check if job has UPC and can generate EPC database
        upc = job_data.get("UPC Number", "")
        if upc and validate_upc(upc):
            menu.addAction(
                "Generate EPC Database...", 
                lambda: self.generate_epc_for_job(job_data, source_index)
            )
            menu.addSeparator()

        menu.addAction("Move to Archive", lambda: self.move_to_archive_for_job(source_index))
        menu.addAction("Delete Job", lambda: self.delete_job_by_index(source_index))

        menu.exec(event.globalPos())

    def edit_selected_job_in_details(self, source_index):
        """Open the job details dialog in edit mode for the selected job."""
        job_data = self.source_model.item(source_index.row(), 0).data(Qt.ItemDataRole.UserRole)

        if not job_data:
            QMessageBox.warning(self, "Error", "Could not retrieve job data.")
            return

        # Create and show the job details dialog
        dialog = JobDetailsDialog(job_data, self.base_path, self)

        # Connect signals to handle updates
        dialog.job_updated.connect(self.update_job_in_table)
        dialog.job_archived.connect(self.handle_job_archived)
        dialog.job_deleted.connect(self.handle_job_deleted_from_details)

        # Automatically enter edit mode
        dialog.enter_edit_mode()

        dialog.exec()

    def open_roll_tracker_for_job(self, job_data):
        """Open the interactive roll tracker for the given job."""
        if job_data:
            # Check if the job has the required data for roll tracking
            quantity = job_data.get('Quantity', job_data.get('Qty', 0))
            
            if not quantity or (isinstance(quantity, str) and not quantity.isdigit()):
                QMessageBox.warning(self, "Invalid Job Data", 
                                  "This job does not have valid quantity data for roll tracking.")
                return
            
            # Create and show the roll tracker dialog (non-modal)
            tracker_dialog = InteractiveRollTrackerDialog(job_data, self)
            tracker_dialog.show()  # Use show() instead of exec() to make it non-modal

    def generate_epc_for_job(self, job_data, source_index):
        """Generate EPC database files for the given job."""
        if not job_data:
            QMessageBox.warning(self, "Error", "Could not retrieve job data.")
            return

        upc = job_data.get("UPC Number", "")
        if not upc or not validate_upc(upc):
            QMessageBox.warning(
                self, "Invalid UPC", "Job does not have a valid 12-digit UPC."
            )
            return

        # Create a simple dialog for EPC generation parameters
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QFormLayout,
            QSpinBox,
            QDialogButtonBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Generate EPC Database")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        # Starting serial number
        serial_spin = QSpinBox()
        serial_spin.setRange(1, 999999999)
        serial_spin.setValue(int(job_data.get("Serial Number", "1")))
        form_layout.addRow("Starting Serial Number:", serial_spin)

        # Total quantity
        qty_spin = QSpinBox()
        qty_spin.setRange(1, 999999999)
        base_qty = job_data.get("Quantity", job_data.get("Qty", "0"))
        if isinstance(base_qty, str) and base_qty.replace(",", "").isdigit():
            qty_spin.setValue(int(base_qty.replace(",", "")))
        form_layout.addRow("Total Quantity:", qty_spin)

        # Quantity per database file
        qty_per_db_spin = QSpinBox()
        qty_per_db_spin.setRange(100, 100000)
        qty_per_db_spin.setValue(1000)
        form_layout.addRow("Quantity per DB File:", qty_per_db_spin)

        # Percentage buffers
        buffer_2_check = QCheckBox("Add 2% buffer")
        buffer_7_check = QCheckBox("Add 7% buffer")
        form_layout.addRow("Buffers:", buffer_2_check)
        form_layout.addRow("", buffer_7_check)

        layout.addLayout(form_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Get parameters from dialog
        start_serial = serial_spin.value()
        base_qty = qty_spin.value()
        qty_per_db = qty_per_db_spin.value()
        include_2_percent = buffer_2_check.isChecked()
        include_7_percent = buffer_7_check.isChecked()

        # Calculate total quantity with buffers
        total_qty = calculate_total_quantity_with_percentages(
            base_qty, include_2_percent, include_7_percent
        )

        # Determine where to save the EPC files
        job_folder_path = job_data.get("job_folder_path")
        if not job_folder_path or not os.path.exists(job_folder_path):
            QMessageBox.warning(
                self, "Path Error", "Job folder path not found or does not exist."
            )
            return

        # Check if this job already has EPC structure
        upc_folder_path = job_data.get("upc_folder_path")
        if upc_folder_path and os.path.exists(upc_folder_path):
            # Use existing EPC structure
            data_folder_path = job_data.get(
                "data_folder_path", os.path.join(upc_folder_path, "data")
            )
        else:
            # Create a data folder in the main job folder
            data_folder_path = os.path.join(job_folder_path, "data")
            os.makedirs(data_folder_path, exist_ok=True)

        # Store parameters for later use in callback
        self.temp_epc_params = {
            'job_data': job_data,
            'job_folder_path': job_folder_path,
            'data_folder_path': data_folder_path,
            'source_index': source_index,  # Store source index instead of row
            'total_qty': total_qty
        }

        # Use threaded generation to prevent UI freezing
        self.epc_progress_dialog = EPCProgressDialog(
            upc, start_serial, total_qty, qty_per_db, data_folder_path, self
        )
        
        # Connect completion signal
        self.epc_progress_dialog.generation_finished.connect(self.on_existing_job_epc_finished)
        
        # Show the dialog
        self.epc_progress_dialog.exec()

    def move_to_archive_for_job(self, source_index):
        """Move the specified job to archive."""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Are you sure you want to move this job to the archive?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return

        job_data = self.source_model.item(source_index.row(), 0).data(Qt.ItemDataRole.UserRole)
        job_folder_path = job_data.get("job_folder_path")

        if not job_folder_path or not os.path.exists(job_folder_path):
            QMessageBox.warning(
                self,
                "Archive Error",
                "Original job folder not found or path not set. Cannot archive.",
            )
            return

        # Set archive date and status before sending to archive
        from datetime import datetime
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        job_data['dateArchived'] = current_timestamp
        job_data['archivedDate'] = datetime.now().strftime('%Y-%m-%d')
        job_data['Status'] = 'Archived'
        
        print(f"Moving job to archive with timestamp: {current_timestamp}")

        # Emit the job data to the archive page
        self.job_to_archive.emit(job_data)

        # Since it's archived, we delete it from the active jobs directories
        self._delete_job_files(job_data)

        # Remove the job from the source model and active list
        self.source_model.removeRow(source_index.row())
        self.all_jobs = [j for j in self.all_jobs if j.get('job_folder_path') != job_folder_path]

        # Ensure monitoring continues after archiving
        self.ensure_directory_monitoring()

        QMessageBox.information(self, "Success", "Job has been successfully archived.")

    def delete_job_by_index(self, source_index):
        """Delete job by source model index, including all its files."""
        job_data = self.source_model.item(source_index.row(), 0).data(Qt.ItemDataRole.UserRole)

        if not job_data:
            QMessageBox.warning(self, "Error", "Could not find job data to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to permanently delete this job and all its associated files?\n\nJob: {job_data.get('PO#')} - {self.get_job_data_value(job_data, 'Ticket#', 'Job Ticket#')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_job_files(job_data)
            # Remove from the source model and active list
            self.source_model.removeRow(source_index.row())
            self.all_jobs = [j for j in self.all_jobs if j.get('job_folder_path') != job_data.get('job_folder_path')]

            # Ensure monitoring continues after deletion
            self.ensure_directory_monitoring()

    def create_folder_for_selected_job_with_location_picker(self):
        """Create job folder with user-selected directory location."""
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return

        selected_row_index = selection_model.selectedRows()[0]

        job_data = {}
        for col, header in enumerate(self.headers):
            cell_index = self.source_model.index(selected_row_index.row(), col)
            cell_value = self.source_model.data(cell_index, Qt.DisplayRole)

            # Map display headers back to data keys for backward compatibility
            if header == "Ticket#":
                job_data["Job Ticket#"] = cell_value  # Use old key for compatibility
            elif header == "Qty":
                job_data["Quantity"] = cell_value  # Use old key for compatibility
            else:
                job_data[header] = cell_value

        # Let user select where to create the job folder
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Create Job Folder",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )

        if not directory:
            return  # User cancelled

        try:
            customer = job_data.get("Customer", "UnknownCustomer")
            label_size = job_data.get("Label Size", "UnknownLabelSize")
            po_num = job_data.get("PO#", "UnknownPO")
            job_ticket_num = job_data.get("Ticket#", "UnknownTicket")

            # Use current date for folder creation
            current_date = datetime.now().strftime("%y-%m-%d")
            job_folder_name = f"{current_date} - {po_num} - {job_ticket_num}"

            # Create the directory structure: Selected Dir / Customer / Label Size / Job Folder
            customer_path = os.path.join(directory, customer)
            label_size_path = os.path.join(customer_path, label_size)
            job_path = os.path.join(label_size_path, job_folder_name)

            # Create directories if they don't exist
            os.makedirs(customer_path, exist_ok=True)
            os.makedirs(label_size_path, exist_ok=True)

            if os.path.exists(job_path):
                QMessageBox.warning(
                    self, "Warning", f"Job folder already exists:\n{job_path}"
                )
                return

            os.makedirs(job_path)

            # Get the full job data for creating JSON and PDF
            full_job_data = self._get_job_data_for_row(selected_row_index.row())
            if full_job_data:
                # For folder creation, use the current data from table with proper field mapping
                folder_job_data = {}
                for col, header in enumerate(self.headers):
                    cell_index = self.source_model.index(selected_row_index.row(), col)
                    cell_value = self.source_model.data(cell_index, Qt.DisplayRole)

                    # Map display headers back to data keys for folder creation
                    if header == "Ticket#":
                        folder_job_data["Job Ticket#"] = (
                            cell_value  # Use old key for folder naming
                        )
                    elif header == "Qty":
                        folder_job_data["Quantity"] = (
                            cell_value  # Use old key for data consistency
                        )
                    else:
                        folder_job_data[header] = cell_value

                # Use current date for folder creation
                current_date = datetime.now().strftime("%y-%m-%d")
                customer = folder_job_data.get("Customer", "UnknownCustomer")
                label_size = folder_job_data.get("Label Size", "UnknownLabelSize")
                po_num = folder_job_data.get("PO#", "UnknownPO")
                job_ticket_num = folder_job_data.get("Job Ticket#", "UnknownTicket")
                job_folder_name = f"{current_date} - {po_num} - {job_ticket_num}"

                # Create the directory structure: Selected Dir / Customer / Label Size / Job Folder
                customer_path = os.path.join(directory, customer)
                label_size_path = os.path.join(customer_path, label_size)
                job_path = os.path.join(label_size_path, job_folder_name)

                # Create directories if they don't exist
                os.makedirs(customer_path, exist_ok=True)
                os.makedirs(label_size_path, exist_ok=True)

                if os.path.exists(job_path):
                    QMessageBox.warning(
                        self, "Warning", f"Job folder already exists:\n{job_path}"
                    )
                    return

                os.makedirs(job_path)

                # Save job data JSON in the new folder (preserve full job data structure)
                full_job_data["job_folder_path"] = job_path
                try:
                    with open(os.path.join(job_path, "job_data.json"), "w") as f:
                        json.dump(full_job_data, f, indent=4)
                except IOError as e:
                    print(f"Could not save job_data.json: {e}")

                # Create checklist PDF
                self.create_checklist_pdf(full_job_data, job_path)

            QMessageBox.information(
                self, "Success", f"Job folder created successfully at:\n{job_path}"
            )
            print(f"Successfully created job folder: {job_path}")

        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")

    def create_quality_control_sheet(self, job_data, job_folder_path):
        """Generate HTML quality control sheet for the job."""
        try:
            customer = job_data.get("Customer", "Unknown Customer")
            job_ticket = job_data.get("Ticket#", job_data.get("Job Ticket#", "Unknown"))
            po_number = job_data.get("PO#", "Unknown")
            
            # Create QC filename
            qc_filename = f"{customer}-{job_ticket}-{po_number}-QualityControl.html"
            qc_path = os.path.join(job_folder_path, qc_filename)
            
            # Generate the quality control sheet
            result_path = generate_quality_control_sheet(job_data, qc_path)
            
            if result_path:
                print(f"Quality control sheet created successfully: {result_path}")
            else:
                print("Warning: Quality control sheet generation failed")
                QMessageBox.warning(self, "QC Sheet Warning", 
                                  "Quality control sheet could not be generated, but job creation will continue.")
            
        except Exception as e:
            print(f"Error creating quality control sheet: {e}")
            # Don't show error dialog - this shouldn't block job creation
            print("Job creation will continue without quality control sheet")

    def create_checklist_pdf(self, job_data, job_path):
        """
        Generates a checklist for the job and saves it in the specified job_path using threaded generation.
        """
        template_path = os.path.join(
            self.base_path, "data", "Encoding Checklist V4.1.pdf"
        )

        if not os.path.exists(template_path):
            QMessageBox.warning(
                self,
                "Missing Template",
                "Could not find the PDF work order template. Skipping PDF generation.",
            )
            return

        output_file_name = f"{job_data.get('Customer', '')}-{self.get_job_data_value(job_data, 'Ticket#', 'Job Ticket#')}-{job_data.get('PO#', '')}-Checklist.pdf"
        save_path = os.path.join(job_path, output_file_name)

        # Use threaded PDF generation for better performance
        self.pdf_progress_dialog = PDFProgressDialog(
            template_path, job_data, save_path, self
        )
        
        # Connect completion signal
        self.pdf_progress_dialog.generation_finished.connect(
            lambda success, result: self.on_pdf_generation_finished(
                success, result, save_path
            )
        )
        
        # Show the dialog
        self.pdf_progress_dialog.exec()

    def on_pdf_generation_finished(self, success, result, expected_path):
        """Handle completion of PDF generation."""
        if success:
            print(f"Checklist created successfully at:\n{result}")
        else:
            if "cancelled" not in result.lower():
                QMessageBox.critical(
                    self, "PDF Error", f"Could not generate checklist PDF:\n{result}"
                )
            print(f"PDF generation failed: {result}")

    def open_job_details(self, index):
        """Open job details window when job is double-clicked"""
        if not index.isValid():
            return

        # Map the proxy index to source index
        source_index = self.proxy_model.mapToSource(index)
        
        # Get the job data from the first column's UserRole data
        job_data = self.source_model.item(source_index.row(), 0).data(Qt.ItemDataRole.UserRole)

        if not job_data:
            QMessageBox.warning(self, "Error", "Could not retrieve job data.")
            return

        # Create and show the job details dialog
        dialog = JobDetailsDialog(job_data, self.base_path, self)

        # Connect signals
        dialog.job_updated.connect(self.update_job_in_table)
        dialog.job_archived.connect(self.handle_job_archived)
        dialog.job_deleted.connect(self.handle_job_deleted_from_details)

        dialog.exec()

    def update_job_in_table(self, updated_job_data):
        """Update job data in the table and filesystem. Called from details dialog."""
        # Find the row with matching job data and update it
        for i, job in enumerate(self.all_jobs):
            # Use a reliable identifier to find the job
            if job.get("job_folder_path") == updated_job_data.get("job_folder_path"):
                # Update the source of truth
                self.all_jobs[i] = updated_job_data

                # Update the view with proper formatting
                for col, header in enumerate(self.headers):
                    if header in updated_job_data:
                        # Special handling for Due Date formatting
                        if header == "Due Date":
                            formatted_value = self.format_date_for_display(
                                updated_job_data[header]
                            )
                            item = QStandardItem(formatted_value)
                        # Special handling for Qty formatting
                        elif header == "Qty":
                            qty_value = updated_job_data[header]
                            if qty_value and str(qty_value).isdigit():
                                formatted_value = f"{int(qty_value):,}"
                            else:
                                formatted_value = str(qty_value)
                            item = QStandardItem(formatted_value)
                        else:
                            item = QStandardItem(str(updated_job_data[header]))
                        self.source_model.setItem(i, col, item)
                break

    def handle_job_archived(self, job_data):
        """Handle job being archived from details dialog"""
        # Set archive date and status before sending to archive
        from datetime import datetime
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        job_data['dateArchived'] = current_timestamp
        job_data['archivedDate'] = datetime.now().strftime('%Y-%m-%d')
        job_data['Status'] = 'Archived'
        
        print(f"Archiving job from details dialog with timestamp: {current_timestamp}")
        
        self.job_to_archive.emit(job_data)

        # Find the row and remove it, deleting files as part of the process
        for i, job in enumerate(self.all_jobs):
            if job.get("job_folder_path") == job_data.get("job_folder_path"):
                self._delete_job_files(job_data)
                self.source_model.removeRow(i)
                del self.all_jobs[i]
                break

        # Ensure monitoring continues after archiving
        self.ensure_directory_monitoring()

    def handle_job_deleted_from_details(self, job_data):
        """Handle job being deleted from details dialog with the same logic as context menu."""
        # Find the row in the source model that matches this job
        for i in range(self.source_model.rowCount()):
            row_job_data = self.source_model.item(i, 0).data(Qt.ItemDataRole.UserRole)
            if row_job_data and row_job_data.get("job_folder_path") == job_data.get("job_folder_path"):
                # Use the same deletion logic as delete_job_by_index
                self._delete_job_files(job_data)
                # Remove from the source model and active list
                self.source_model.removeRow(i)
                self.all_jobs = [j for j in self.all_jobs if j.get('job_folder_path') != job_data.get('job_folder_path')]
                # Ensure monitoring continues after deletion
                self.ensure_directory_monitoring()
                break

    def delete_job_by_row(self, row):
        """Delete job by row index, including all its files."""
        if 0 <= row < self.source_model.rowCount():
            job_data = self._get_job_data_for_row(row)

            reply = QMessageBox.question(
                self,
                "Delete Job",
                f"This will permanently delete the job and all its files. Are you sure?\n\nFolder: {job_data.get('job_folder_path')}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._delete_job_files(job_data)
                self.source_model.removeRow(row)
                del self.all_jobs[row]

                # Ensure monitoring continues after deletion
                self.ensure_directory_monitoring()

    def _delete_job_files(self, job_data):
        """Deletes job folders from primary and active source locations using threaded operations."""
        # First, remove all paths related to this job from the file watcher
        primary_path = job_data.get("job_folder_path")

        if primary_path:
            # Remove all subdirectories of this job from the file watcher
            paths_to_remove = []
            for watched_path in self.file_watcher.directories():
                if (
                    watched_path.startswith(primary_path)
                    or primary_path in watched_path
                ):
                    paths_to_remove.append(watched_path)

            # Also check for active source paths
            try:
                old_folder_name = os.path.basename(primary_path)
                active_source_path = os.path.join(
                    config.ACTIVE_JOBS_SOURCE_DIR,
                    job_data.get("Customer", ""),
                    job_data.get("Label Size", ""),
                    old_folder_name,
                )
                for watched_path in self.file_watcher.directories():
                    if (
                        watched_path.startswith(active_source_path)
                        or active_source_path in watched_path
                    ):
                        paths_to_remove.append(watched_path)
            except:
                pass

            # Remove all identified paths from the watcher
            for path in paths_to_remove:
                self.file_watcher.removePath(path)
                print(f"Removed from file watcher: {path}")

            # Give the system a moment to release file handles
            import time
            time.sleep(0.1)

        # Store paths for deletion
        paths_to_delete = []
        
        # 1. Primary location
        if primary_path and os.path.exists(primary_path):
            paths_to_delete.append(('primary', primary_path))

        # 2. Active jobs source location
        try:
            if primary_path:
                old_folder_name = os.path.basename(primary_path)
                active_source_path = os.path.join(
                    config.ACTIVE_JOBS_SOURCE_DIR,
                    job_data.get("Customer", ""),
                    job_data.get("Label Size", ""),
                    old_folder_name,
                )
                if os.path.exists(active_source_path):
                    paths_to_delete.append(('active_source', active_source_path))
        except Exception as e:
            print(f"Error checking active source path: {e}")

        # Delete paths using threaded operations
        if paths_to_delete:
            self.delete_paths_with_progress(paths_to_delete)
        else:
            print("No paths found to delete")

    def delete_paths_with_progress(self, paths_to_delete):
        """Delete multiple paths sequentially with progress feedback."""
        if not paths_to_delete:
            return
            
        # Store remaining paths for sequential deletion
        self.pending_deletions = paths_to_delete.copy()
        self.delete_next_path()

    def delete_next_path(self):
        """Delete the next path in the queue."""
        if not hasattr(self, 'pending_deletions') or not self.pending_deletions:
            print("All deletions completed")
            return
            
        location_type, path = self.pending_deletions.pop(0)
        
        print(f"Deleting {location_type} folder: {path}")
        
        # Use threaded deletion for potentially large folders
        self.file_op_progress_dialog = FileOperationProgressDialog(
            'delete', path, None, None, self
        )
        
        # Connect completion signal
        self.file_op_progress_dialog.operation_finished.connect(
            lambda success, message: self.on_delete_operation_finished(
                success, message, location_type, path
            )
        )
        
        # Show the dialog
        self.file_op_progress_dialog.exec()

    def on_delete_operation_finished(self, success, message, location_type, path):
        """Handle completion of delete operation and continue with next deletion."""
        if success:
            print(f"Successfully deleted {location_type} folder: {path}")
        else:
            print(f"Failed to delete {location_type} folder: {message}")
            # Continue with remaining deletions even if one fails
            
        # Continue with next deletion
        self.delete_next_path()

    def create_job_folder_and_checklist(self, job_data):
        """Enhanced job creation with EPC functionality, improved folder structure, and template copying."""
        if job_data.get("Shared Drive"):
            base_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        elif job_data.get("Desktop"):
            base_path = os.path.expanduser("~/Desktop")
        elif job_data.get("Custom Path"):
            base_path = job_data["Custom Path"]
        else:
            QMessageBox.warning(self, "Error", "No save location selected.")
            return

        try:
            customer = job_data.get("Customer")
            label_size = job_data.get("Label Size")
            po_num = job_data.get("PO#")
            job_ticket = self.get_job_data_value(job_data, "Ticket#", "Job Ticket#")
            upc = job_data.get("UPC Number", "")

            if not all([customer, label_size, po_num, job_ticket]):
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    "Customer, Label Size, PO#, and Ticket# are required to create a folder.",
                )
                return

            # Determine whether to use EPC folder structure or traditional structure
            enable_epc = job_data.get("Enable EPC Generation", False)

            if enable_epc and upc and validate_upc(upc):
                # Use EPC script's enhanced folder structure
                folder_info = create_upc_folder_structure(
                    base_path,
                    customer,
                    label_size,
                    po_num,
                    job_ticket,
                    upc,
                    config.get_template_base_path(),
                )
                job_folder_path = folder_info["job_folder_path"]
                upc_folder_path = folder_info["upc_folder_path"]
                data_folder_path = folder_info["data_folder_path"]
                print_folder_path = folder_info["print_folder_path"]

                job_data["job_folder_path"] = job_folder_path
                job_data["upc_folder_path"] = upc_folder_path
                job_data["data_folder_path"] = data_folder_path
                job_data["print_folder_path"] = print_folder_path

                print(f"Successfully created EPC job structure: {job_folder_path}")

                # Generate EPC database files if requested
                if job_data.get("Enable EPC Generation", False):
                    # Use threaded generation to prevent UI freezing
                    self.generate_epc_with_progress(job_data, job_folder_path)
                    return True  # Early return since EPC generation is async
                else:
                    # No EPC generation, continue with normal flow
                    return self.finalize_job_creation(job_data, job_folder_path)

            else:
                # Use traditional folder structure for non-EPC jobs
                current_date = datetime.now().strftime("%y-%m-%d")
                job_folder_name = f"{current_date} - {po_num} - {job_ticket}"
                customer_path = os.path.join(base_path, customer)
                label_size_path = os.path.join(customer_path, label_size)
                job_folder_path = os.path.join(label_size_path, job_folder_name)

                # Create main job folder
                job_data["job_folder_path"] = job_folder_path
                os.makedirs(job_folder_path, exist_ok=True)
                
                # Create print folder for traditional structure
                print_folder_path = os.path.join(job_folder_path, "print")
                os.makedirs(print_folder_path, exist_ok=True)
                job_data["print_folder_path"] = print_folder_path
                
                # Copy template for traditional structure
                self.copy_template_to_job(job_data, customer, label_size, print_folder_path)
                
                # Calculate and store serial range for traditional jobs (for PDF generation)
                try:
                    base_qty = int(job_data.get("Quantity", "0"))
                    manual_override = job_data.get("Manual Serial Override", False)
                    
                    if manual_override:
                        start_serial = int(job_data.get("Serial Number", "1"))
                        print(f"Traditional job using manual serial override: starting at {start_serial}")
                    else:
                        # Try centralized serial allocation for traditional jobs too
                        try:
                            from src.utils.serial_manager import allocate_serials_for_job
                            start_serial, end_serial = allocate_serials_for_job(base_qty, job_data)
                            print(f"Traditional job allocated serials {start_serial} - {end_serial}")
                        except Exception as e:
                            print(f"Warning: Centralized serial allocation failed for traditional job: {e}")
                            start_serial = int(job_data.get("Serial Number", "1000"))
                            end_serial = start_serial + base_qty - 1
                            print(f"Traditional job fallback: using serials {start_serial} - {end_serial}")
                    
                    # For traditional jobs without buffers, end_serial is start + quantity - 1
                    if manual_override or "end_serial" not in locals():
                        end_serial = start_serial + base_qty - 1
                    
                    # Store serial range information for PDF generation
                    job_data["Start"] = str(start_serial)
                    job_data["End"] = str(end_serial)
                    job_data["Serial Range Start"] = start_serial
                    job_data["Serial Range End"] = end_serial
                    
                    print(f"Stored traditional job serial range: Start={start_serial}, End={end_serial}")
                    
                except Exception as e:
                    print(f"Warning: Could not calculate serial range for traditional job: {e}")
                    # Set default values for PDF generation
                    job_data["Start"] = "1"
                    job_data["End"] = job_data.get("Quantity", "1")
                
                print(f"Successfully created traditional job folder: {job_folder_path}")

                # Continue with normal job creation flow
                return self.finalize_job_creation(job_data, job_folder_path)

        except Exception as e:
            print(f"Job not created: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job:\n{e}")
            return False

    def copy_template_to_job(self, job_data, customer, label_size, print_folder_path):
        """Copy .btw template file to the job's print folder."""
        try:
            from src.utils.epc_conversion import get_template_path_with_inlay
            from src.utils.template_mapping import get_template_manager
            
            # First, check template mappings
            template_manager = get_template_manager()
            template_path = template_manager.get_template(customer, label_size)
            
            if template_path:
                print(f"Using mapped template: {template_path}")
            else:
                # Fall back to directory scanning
                template_base_path = config.get_template_base_path()
                
                if not template_base_path or not os.path.exists(template_base_path):
                    print(f"Template base path not configured or doesn't exist: {template_base_path}")
                    return
                
                # Get inlay type for better template matching
                inlay_type = job_data.get("Inlay Type", "")
                
                # Use enhanced template lookup with inlay type
                template_path = get_template_path_with_inlay(template_base_path, customer, label_size, inlay_type)
            
            if template_path and os.path.exists(template_path):
                # Determine destination filename priority: UPC > Job Ticket > PO Number
                job_ticket = self.get_job_data_value(job_data, "Ticket#", "Job Ticket#")
                po_num = job_data.get("PO#", "")
                upc = job_data.get("UPC Number", "")
                
                if upc:
                    destination_filename = f"{upc}.btw"
                elif job_ticket:
                    destination_filename = f"{job_ticket}.btw"
                else:
                    destination_filename = f"{po_num}.btw"
                
                destination_template = os.path.join(print_folder_path, destination_filename)
                shutil.copy(template_path, destination_template)
                print(f"Template copied: {os.path.basename(template_path)} -> {destination_filename}")
            else:
                print(f"No template found for {customer} - {label_size} (Inlay: {inlay_type})")
                    
        except Exception as e:
            print(f"Error copying template: {e}")

    def generate_epc_with_progress(self, job_data, job_folder_path):
        """Generate EPC database files using threaded progress dialog."""
        try:
            base_qty = int(job_data.get("Quantity", "0"))
            
            # Check if manual serial override was used
            manual_override = job_data.get("Manual Serial Override", False)
            
            if manual_override:
                # Use the manually entered serial number
                start_serial = int(job_data.get("Serial Number", "1"))
                print(f"Using manual serial override: starting at {start_serial}")
            else:
                # Use centralized serial allocation
                from src.utils.serial_manager import allocate_serials_for_job
            
            # Calculate total quantity with buffers
            total_qty = calculate_total_quantity_with_percentages(
                base_qty,
                job_data.get("Include 2% Buffer", False),
                job_data.get("Include 7% Buffer", False),
            )
            
            if not manual_override:
                # Try centralized serial allocation, fallback to manual if fails
                try:
                    from src.utils.serial_manager import allocate_serials_for_job
                    start_serial, end_serial = allocate_serials_for_job(total_qty, job_data)
                    print(f"Allocated serials {start_serial} - {end_serial} for job {job_data.get('Ticket#', 'Unknown')}")
                except Exception as e:
                    print(f"Warning: Centralized serial allocation failed: {e}")
                    print("Falling back to manual serial from wizard input")
                    # Fallback to using the serial from wizard (which was auto-populated)
                    start_serial = int(job_data.get("Serial Number", "1000"))
                    end_serial = start_serial + total_qty - 1
                    print(f"Fallback: using serials {start_serial} - {end_serial} for job {job_data.get('Ticket#', 'Unknown')}")
            else:
                # Calculate end serial for manual override
                end_serial = start_serial + total_qty - 1
                print(f"Manual override: using serials {start_serial} - {end_serial} for job {job_data.get('Ticket#', 'Unknown')}")
            
            # Store serial range information in job_data for PDF generation
            job_data["Start"] = str(start_serial)
            job_data["End"] = str(end_serial)
            job_data["Serial Range Start"] = start_serial  # For internal use
            job_data["Serial Range End"] = end_serial    # For internal use
            job_data["Total Quantity with Buffers"] = total_qty
            
            print(f"Stored serial range in job data: Start={start_serial}, End={end_serial}")
            
            qty_per_db = int(job_data.get("Qty per DB", "1000"))
            upc = job_data.get("UPC Number", "")
            data_folder_path = job_data.get("data_folder_path", "")
            
            # Create and show progress dialog with job data for logging
            self.epc_progress_dialog = EPCProgressDialog(
                upc, start_serial, total_qty, qty_per_db, data_folder_path, self, job_data
            )
            
            # Connect completion signal
            self.epc_progress_dialog.generation_finished.connect(
                lambda success, result: self.on_epc_generation_finished(
                    success, result, job_data, job_folder_path
                )
            )
            
            # Show the dialog
            self.epc_progress_dialog.exec()
            
        except Exception as e:
            print(f"EPC generation setup failed: {e}")
            QMessageBox.warning(
                self,
                "EPC Generation Error",
                f"Failed to start EPC generation:\n{e}\n\nJob folder created without EPC files.",
            )
            # Continue with job creation without EPC files
            self.finalize_job_creation(job_data, job_folder_path)

    def on_epc_generation_finished(self, success, result, job_data, job_folder_path):
        """Handle completion of EPC generation."""
        if success:
            # result is the list of created files
            created_files = result
            print(f"Generated {len(created_files)} EPC database files")
            job_data["epc_files_created"] = len(created_files)
            
            # Calculate total quantity for display
            base_qty = int(job_data.get("Quantity", "0"))
            total_qty = calculate_total_quantity_with_percentages(
                base_qty,
                job_data.get("Include 2% Buffer", False),
                job_data.get("Include 7% Buffer", False),
            )
            job_data["total_qty_with_buffers"] = total_qty
        else:
            # result is the error message
            error_message = result
            print(f"EPC database generation failed: {error_message}")
            
            if "cancelled" not in error_message.lower():
                QMessageBox.warning(
                    self,
                    "EPC Generation Warning",
                    f"Job folder created successfully, but EPC database generation failed:\n{error_message}",
                )
        
        # Complete the job creation process
        self.finalize_job_creation(job_data, job_folder_path)

    def finalize_job_creation(self, job_data, job_folder_path):
        """Complete the job creation process after EPC generation (if any) is done."""
        try:
            # Check for duplicates BEFORE finalizing the job creation
            is_duplicate, conflict_type, conflicting_job = self.check_for_duplicate_job(job_data)
            
            if is_duplicate:
                # Duplicate detected - clean up any created folders and abort
                if os.path.exists(job_folder_path):
                    print(f"Duplicate detected - cleaning up folder: {job_folder_path}")
                    import shutil
                    try:
                        shutil.rmtree(job_folder_path)
                        print(f"Successfully cleaned up duplicate job folder")
                    except Exception as e:
                        print(f"Warning: Could not clean up folder {job_folder_path}: {e}")
                
                # Show appropriate error message based on conflict type
                if conflict_type == "ticket_duplicate":
                    conflict_customer = conflicting_job.get("Customer", "")
                    conflict_po = conflicting_job.get("PO#", "")
                    conflict_ticket = conflicting_job.get("Ticket#", conflicting_job.get("Job Ticket#", ""))
                    
                    QMessageBox.warning(
                        self, 
                        "Duplicate Ticket Number - Creation Cancelled",
                        f"Job creation was cancelled because a job with the same Ticket# already exists:\n\n"
                        f"Existing Job:\n"
                        f"  Customer: {conflict_customer}\n"
                        f"  PO#: {conflict_po}\n"
                        f"  Ticket#: {conflict_ticket}\n\n"
                        f"Ticket numbers must be unique. Please use a different ticket number."
                    )
                elif conflict_type == "upc_conflict":
                    conflict_upc = conflicting_job.get("UPC Number", "")
                    conflict_customer = conflicting_job.get("Customer", "")
                    conflict_po = conflicting_job.get("PO#", "")
                    
                    QMessageBox.warning(
                        self,
                        "UPC Conflict - Creation Cancelled", 
                        f"Job creation was cancelled because the UPC number '{conflict_upc}' is already in use:\n\n"
                        f"Existing Job:\n"
                        f"  Customer: {conflict_customer}\n"
                        f"  PO#: {conflict_po}\n\n"
                        f"Please use a different UPC number for this job."
                    )
                
                return False  # Indicate failure
            
            # No duplicates - proceed with job creation
            # Save job data to JSON file
            job_data_path = os.path.join(job_folder_path, "job_data.json")
            try:
                with open(job_data_path, "w") as f:
                    json.dump(job_data, f, indent=4)
            except IOError as e:
                QMessageBox.warning(
                    self, "Save Error", f"Could not save job_data.json.\n{e}"
                )

            # Generate quality control sheet
            self.create_quality_control_sheet(job_data, job_folder_path)

            # Create checklist PDF
            self.create_checklist_pdf(job_data, job_folder_path)

            # Copy to active jobs source directory
            self.copy_to_active_jobs_source(job_data, job_folder_path)

            # Try to add the job to the table - this should succeed since we checked for duplicates
            add_success = self.add_job_to_table(job_data)
            if not add_success:
                print("Warning: Job creation completed but failed to add to table (unexpected)")

            # Ensure new directories are being monitored
            self.ensure_directory_monitoring()

            # Show success message with details
            self.show_job_creation_success(job_data, job_folder_path)

            return True  # Indicate success

        except Exception as e:
            print(f"Job finalization failed: {e}")
            QMessageBox.critical(self, "Error", f"Could not finalize job creation:\n{e}")
            return False

    def copy_to_active_jobs_source(self, job_data, job_folder_path):
        """Copy job folder to active jobs source directory using threaded operation."""
        try:
            customer = job_data.get("Customer")
            label_size = job_data.get("Label Size")
            final_folder_name = os.path.basename(job_folder_path)
            source_dest_path = os.path.join(
                config.ACTIVE_JOBS_SOURCE_DIR, customer, label_size
            )
            os.makedirs(source_dest_path, exist_ok=True)

            destination_path = os.path.join(source_dest_path, final_folder_name)
            
            # Update job data with the expected active source path
            job_data["active_source_folder_path"] = destination_path
            
            # Check if destination already exists
            if os.path.exists(destination_path):
                print(f"Folder already exists in active source, skipping copy: {destination_path}")
                QMessageBox.warning(
                    self,
                    "Duplicate Warning",
                    f"A folder with the same name already exists in the active source directory. "
                    f"The job was created in the primary location, but not copied.",
                )
                return
            
            # Use threaded file operation for large copies
            self.copy_progress_dialog = FileOperationProgressDialog(
                'copy', job_folder_path, destination_path, job_data, self
            )
            
            # Connect completion signal
            self.copy_progress_dialog.operation_finished.connect(
                lambda success, message: self.on_copy_operation_finished(
                    success, message, destination_path
                )
            )
            
            # Show the dialog
            self.copy_progress_dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Copy Error",
                f"Could not copy job folder to active source directory.\n\nError: {e}",
            )

    def on_copy_operation_finished(self, success, message, destination_path):
        """Handle completion of copy operation."""
        if success:
            print(f"Successfully copied job folder to: {destination_path}")
            # Trigger a refresh to ensure the job appears in the table
            # This is a safety net in case the file system watcher didn't catch it
            self.refresh_timer.start(100)  # Quick refresh after copy completes
        else:
            QMessageBox.warning(
                self,
                "Copy Error", 
                f"Copy operation failed:\n{message}"
            )

    def show_job_creation_success(self, job_data, job_folder_path):
        """Show job creation success message."""
        success_msg = f"Job created successfully at:\n{job_folder_path}"
        
        enable_epc = job_data.get("Enable EPC Generation", False)
        if enable_epc and job_data.get("epc_files_created", 0) > 0:
            success_msg += (
                f"\n\nEPC Database files generated: {job_data['epc_files_created']}"
            )
            success_msg += f"\nTotal quantity (with buffers): {job_data.get('total_qty_with_buffers', 0):,}"

        QMessageBox.information(self, "Success", success_msg)
        
        # Emit signal to notify dashboard of new job
        self.job_created.emit()

    def closeEvent(self, event):
        """Clean up file system watcher when widget is destroyed."""
        if hasattr(self, "file_watcher"):
            # Remove all paths from watcher
            for path in self.file_watcher.directories():
                self.file_watcher.removePath(path)
            print("File system monitoring stopped.")
        event.accept()

    def update_active_jobs_source_directory(self, new_path):
        """Update the active jobs source directory and restart monitoring."""
        # Remove old paths from watcher
        for path in self.file_watcher.directories():
            self.file_watcher.removePath(path)

        # Update config
        config.ACTIVE_JOBS_SOURCE_DIR = new_path

        # Restart monitoring with new path
        self.setup_directory_monitoring()

        # Reload jobs from new location
        self.load_jobs()

        print(f"Updated active jobs source directory to: {new_path}")

    def ensure_directory_monitoring(self):
        """Ensure all necessary directories are being monitored."""
        active_source_dir = config.ACTIVE_JOBS_SOURCE_DIR

        # Re-setup monitoring if directory has changed
        if active_source_dir not in self.file_watcher.directories():
            self.setup_directory_monitoring()

    def edit_selected_job(self):
        """Original edit job method using wizard (kept for backward compatibility)."""
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
        selected_row_index = selection_model.selectedRows()[0]

        current_data = self._get_job_data_for_row(selected_row_index.row())

        wizard = NewJobWizard(self, base_path=self.base_path)
        wizard.setWindowTitle("Edit Job")
        wizard.set_all_data(current_data)

        wizard.page(2).setVisible(False)

        if wizard.exec():
            new_data = wizard.get_data()
            self._update_job(selected_row_index.row(), new_data)

    def create_folder_for_selected_job(self):
        """Original create folder method (kept for backward compatibility)."""
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return

        selected_row_index = selection_model.selectedRows()[0]

        job_data = {}
        for col, header in enumerate(self.headers):
            cell_index = self.source_model.index(selected_row_index.row(), col)
            job_data[header] = self.source_model.data(cell_index, Qt.DisplayRole)

        # Use default network path for context menu folder creation
        self._create_job_folders(job_data, [self.network_path])

    def _create_job_folders(self, job_data, save_locations=None):
        """Create job folders in specified locations with template copying (kept for backward compatibility)."""
        try:
            # If no save_locations provided, fall back to the default network path
            if not save_locations:
                save_locations = [self.network_path]

            current_date = datetime.now().strftime("%y-%m-%d")
            po_num = job_data.get("PO#", "UnknownPO")
            job_ticket_num = job_data.get("Ticket#", "UnknownTicket")
            customer = job_data.get("Customer", "UnknownCustomer")
            label_size = job_data.get("Label Size", "UnknownLabelSize")
            job_folder_name = f"{current_date} - {po_num} - {job_ticket_num}"

            created_folders = []

            for save_location in save_locations:
                if not os.path.exists(save_location):
                    QMessageBox.critical(
                        self, "Error", f"Save location not accessible: {save_location}"
                    )
                    continue

                customer_path = os.path.join(save_location, customer)
                label_size_path = os.path.join(customer_path, label_size)
                job_path = os.path.join(label_size_path, job_folder_name)

                # For custom paths, create the directory structure if it doesn't exist
                if save_location != self.network_path:
                    if not os.path.exists(customer_path):
                        os.makedirs(customer_path)
                        print(f"Created customer directory: {customer_path}")

                    if not os.path.exists(label_size_path):
                        os.makedirs(label_size_path)
                        print(f"Created label size directory: {label_size_path}")
                else:
                    # For network path, require existing structure
                    if not os.path.exists(customer_path):
                        QMessageBox.critical(
                            self,
                            "Error",
                            f"Customer folder not found: {customer}\nPlease make sure the customer folder exists in the network drive.",
                        )
                        continue

                    if not os.path.exists(label_size_path):
                        QMessageBox.critical(
                            self,
                            "Error",
                            f"Label size folder not found for customer {customer}: {label_size}\nPlease make sure the label size folder exists in the customer directory.",
                        )
                        continue

                if os.path.exists(job_path):
                    QMessageBox.warning(
                        self, "Warning", f"Job folder already exists:\n{job_path}"
                    )
                    continue

                os.makedirs(job_path)
                
                # Create print folder and copy template
                print_folder_path = os.path.join(job_path, "print")
                os.makedirs(print_folder_path, exist_ok=True)
                self.copy_template_to_job(job_data, customer, label_size, print_folder_path)
                
                created_folders.append(job_path)
                print(f"Successfully created job folder: {job_path}")

                # Return the first successfully created job path for checklist generation
                if created_folders:
                    return created_folders[0]

            if created_folders:
                folder_list = "\n".join(created_folders)
                QMessageBox.information(
                    self, "Success", f"Job folder(s) created at:\n{folder_list}"
                )
            else:
                QMessageBox.warning(self, "Warning", "No job folders were created.")
                return None

        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")
            return None

    def _update_job(self, row_index, new_data):
        """The core logic for updating a job's files and data."""
        current_data = self.all_jobs[row_index]
        old_primary_path = current_data.get("job_folder_path")

        if not old_primary_path:
            QMessageBox.critical(
                self,
                "Update Error",
                "Cannot update job: Original folder path is missing.",
            )
            return

        # --- 1. Determine new path for the primary job folder ---
        try:
            # Preserve creation date from the original folder name
            old_folder_name = os.path.basename(old_primary_path)
            date_match = re.match(r"(\d{2}-\d{2}-\d{2})", old_folder_name)
            creation_date = date_match.group(1) if date_match else "UnknownDate"

            new_po = new_data.get("PO#")
            new_ticket = self.get_job_data_value(new_data, "Ticket#", "Job Ticket#")
            new_folder_name = f"{creation_date} - {new_po} - {new_ticket}"

            # New primary path
            old_base_path = os.path.dirname(os.path.dirname(old_primary_path))
            new_primary_path = os.path.join(
                old_base_path, new_data.get("Label Size"), new_folder_name
            )
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Error determining new job path: {e}")
            return

        # --- 2. Rename the primary job folder ---
        try:
            if old_primary_path != new_primary_path and os.path.exists(old_primary_path):
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(new_primary_path), exist_ok=True)
                shutil.move(old_primary_path, new_primary_path)
                print(f"Renamed primary folder: {old_primary_path} -> {new_primary_path}")
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Could not rename primary job folder: {e}")
            # Attempt to revert if possible
            if not os.path.exists(old_primary_path) and os.path.exists(new_primary_path):
                shutil.move(new_primary_path, old_primary_path)
            return

        # --- 3. Update paths in job_data.json ---
        new_data["job_folder_path"] = new_primary_path
        # Update other paths if they exist
        if "upc_folder_path" in new_data:
            new_data["upc_folder_path"] = os.path.join(new_primary_path, os.path.basename(new_data["upc_folder_path"]))
        if "data_folder_path" in new_data:
            new_data["data_folder_path"] = os.path.join(new_data["upc_folder_path"], "data")
        if "print_folder_path" in new_data:
            new_data["print_folder_path"] = os.path.join(new_data["upc_folder_path"], "print")

        # --- 4. Save updated job_data.json ---
        try:
            with open(os.path.join(new_primary_path, "job_data.json"), "w") as f:
                json.dump(new_data, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Could not save updated job data: {e}")
            # Revert folder rename
            shutil.move(new_primary_path, old_primary_path)
            return

        # --- 5. Update active jobs source directory ---
        try:
            old_active_source_path = current_data.get("active_source_folder_path")
            if old_active_source_path and os.path.exists(old_active_source_path):
                active_base_path = os.path.dirname(os.path.dirname(old_active_source_path))
                new_active_source_path = os.path.join(
                    active_base_path, new_data.get("Label Size"), new_folder_name
                )

                if old_active_source_path != new_active_source_path:
                    os.makedirs(os.path.dirname(new_active_source_path), exist_ok=True)
                    shutil.move(old_active_source_path, new_active_source_path)
                    print(f"Renamed active source folder: {old_active_source_path} -> {new_active_source_path}")

                # Save updated job data to active source
                with open(os.path.join(new_active_source_path, "job_data.json"), "w") as f:
                    json.dump(new_data, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not update active jobs source folder: {e}")

        # --- 6. Update the UI ---
        self.all_jobs[row_index] = new_data
        self.update_job_in_table(new_data)
        
        QMessageBox.information(self, "Success", "Job updated successfully.")
        
        # Refresh monitoring
        self.ensure_directory_monitoring()

    def show_debug_info(self):
        """Show debug information about the current state of jobs."""
        debug_info = []
        debug_info.append("=== JOB TABLE DEBUG INFO ===")
        debug_info.append(f"Jobs in memory (all_jobs): {len(self.all_jobs)}")
        debug_info.append(f"Rows in table model: {self.source_model.rowCount()}")
        debug_info.append(f"Active jobs source dir: {config.ACTIVE_JOBS_SOURCE_DIR}")
        debug_info.append(f"Monitored directories: {len(self.file_watcher.directories())}")
        
        # Count actual job folders on disk
        disk_job_count = 0
        if os.path.exists(config.ACTIVE_JOBS_SOURCE_DIR):
            for root, _, files in os.walk(config.ACTIVE_JOBS_SOURCE_DIR):
                if "job_data.json" in files:
                    disk_job_count += 1
        debug_info.append(f"Job folders on disk: {disk_job_count}")
        
        # List jobs in memory with duplicate detection details
        debug_info.append("\nJobs in memory (with duplicate detection keys):")
        for i, job in enumerate(self.all_jobs):
            customer = job.get("Customer", "")
            ticket = job.get("Ticket#", job.get("Job Ticket#", ""))
            po = job.get("PO#", "")
            upc = job.get("UPC Number", "")
            debug_info.append(f"  {i+1}. Customer: '{customer}' | PO#: '{po}' | Ticket#: '{ticket}' | UPC: '{upc}'")
        
        # Show duplicate detection matrix
        debug_info.append("\nDuplicate Detection Analysis:")
        ticket_numbers = {}
        upc_numbers = {}
        
        for i, job in enumerate(self.all_jobs):
            customer = job.get("Customer", "").strip()
            po = job.get("PO#", "").strip()
            upc = job.get("UPC Number", "").strip()
            ticket = job.get("Ticket#", job.get("Job Ticket#", "")).strip()
            
            # Track Ticket numbers (primary duplicate check)
            if ticket:
                if ticket in ticket_numbers:
                    ticket_numbers[ticket].append(i+1)
                else:
                    ticket_numbers[ticket] = [i+1]
            
            # Track UPC numbers
            if upc:
                if upc in upc_numbers:
                    upc_numbers[upc].append(i+1)
                else:
                    upc_numbers[upc] = [i+1]
        
        # Report potential duplicates
        duplicates_found = False
        for ticket, job_indices in ticket_numbers.items():
            if len(job_indices) > 1:
                debug_info.append(f"  DUPLICATE Ticket#: {ticket} (Jobs: {job_indices})")
                duplicates_found = True
        
        for upc, job_indices in upc_numbers.items():
            if len(job_indices) > 1:
                debug_info.append(f"  DUPLICATE UPC: {upc} (Jobs: {job_indices})")
                duplicates_found = True
        
        if not duplicates_found:
            debug_info.append("  No duplicates detected.")
        
        # Show the info in a message box
        dialog = QDialog(self)
        dialog.setWindowTitle("Debug Information")
        dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText("\n".join(debug_info))
        layout.addWidget(text_edit)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec()

    def get_job_data_value(self, job_data, new_key, old_key=None):
        """Helper to get value from job_data, trying new key first then old key."""
        if new_key in job_data:
            return job_data[new_key]
        if old_key and old_key in job_data:
            return job_data[old_key]
        return ""
