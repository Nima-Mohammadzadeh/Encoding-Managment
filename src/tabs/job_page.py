import os
import json
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
)
import fitz
import pymupdf, shutil, os, sys
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt, Signal, QFileSystemWatcher, QTimer
from src.wizards.new_job_wizard import NewJobWizard
from src.widgets.job_details_dialog import JobDetailsDialog
import src.config as config

class JobPageWidget(QWidget):
    job_to_archive = Signal(dict)
    
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.save_file = os.path.join(self.base_path, "data", "active_jobs.json")
        self.network_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        self.all_jobs = [] # This will be the source of truth
        
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

        actions_layout.addWidget(self.add_job_button)
        layout.addLayout(actions_layout)

        self.model = QStandardItemModel()
        self.headers = ([
        "Customer", "Part#", "Job Ticket#", "PO#",
         "Inlay Type", "Label Size", "Quantity", "Due Date"
        ])      
        self.model.setHorizontalHeaderLabels(self.headers)

        self.jobs_table = QTableView()
        self.jobs_table.setModel(self.model)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setSortingEnabled(True)
        self.jobs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.jobs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.jobs_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header = self.jobs_table.horizontalHeader()
        header.setSectionResizeMode(self.headers.index("Customer"), QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.headers.index("Part#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Job Ticket#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("PO#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Inlay Type"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Label Size"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Quantity"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Due Date"), QHeaderView.ResizeMode.ResizeToContents)
        self.jobs_table.verticalHeader().hide()
       
        layout.addWidget(self.jobs_table)
        self.setLayout(layout)

        self.load_jobs()
        self.setup_directory_monitoring()

        # Add double-click handler for the table
        self.jobs_table.doubleClicked.connect(self.open_job_details)

    def setup_directory_monitoring(self):
        """Set up file system monitoring for the active jobs source directory."""
        active_source_dir = config.ACTIVE_JOBS_SOURCE_DIR
        
        # Ensure the directory exists
        if not os.path.exists(active_source_dir):
            os.makedirs(active_source_dir, exist_ok=True)
            print(f"Created active jobs source directory: {active_source_dir}")
        
        # Add the main directory to watcher
        if active_source_dir not in self.file_watcher.directories():
            success = self.file_watcher.addPath(active_source_dir)
            if success:
                print(f"Successfully started monitoring: {active_source_dir}")
            else:
                print(f"Failed to monitor: {active_source_dir}")
        
        # Also monitor all subdirectories recursively
        self.add_subdirectories_to_watcher(active_source_dir)
        
        print(f"Currently monitoring {len(self.file_watcher.directories())} directories")

    def add_subdirectories_to_watcher(self, directory):
        """Recursively add all subdirectories to the file system watcher."""
        try:
            for root, dirs, files in os.walk(directory):
                if root not in self.file_watcher.directories():
                    success = self.file_watcher.addPath(root)
                    if success:
                        print(f"Added to monitoring: {root}")
                    else:
                        print(f"Failed to add to monitoring: {root}")
        except Exception as e:
            print(f"Error adding subdirectories to watcher: {e}")

    def on_directory_changed(self, path):
        """Handle directory change events from the file system watcher."""
        print(f"Directory changed detected: {path}")
        
        # Re-add any new subdirectories to the watcher
        self.add_subdirectories_to_watcher(config.ACTIVE_JOBS_SOURCE_DIR)
        
        # Use timer to debounce rapid changes (wait 500ms after last change)
        self.refresh_timer.start(500)
        print("Refresh timer started (500ms delay)")

    def refresh_jobs_table(self):
        """Refresh the jobs table by reloading data from the file system."""
        print("=== Refreshing jobs table due to file system changes ===")
        
        # Store current selection if any
        current_selection = None
        selection_model = self.jobs_table.selectionModel()
        if selection_model.hasSelection():
            selected_row = selection_model.selectedRows()[0].row()
            if 0 <= selected_row < len(self.all_jobs):
                current_job = self.all_jobs[selected_row]
                current_selection = (current_job.get('Job Ticket#'), current_job.get('PO#'))
                print(f"Preserving selection: {current_selection}")
        
        # Reload jobs from directory
        old_count = len(self.all_jobs)
        self.load_jobs()
        new_count = len(self.all_jobs)
        
        print(f"Job count changed from {old_count} to {new_count}")
        
        # Restore selection if possible
        if current_selection:
            self.restore_table_selection(current_selection)
            print("Selection restored")

    def restore_table_selection(self, job_identifiers):
        """Restore table selection based on job ticket and PO number."""
        job_ticket, po_num = job_identifiers
        for row in range(self.model.rowCount()):
            row_job_ticket = self.model.item(row, self.headers.index("Job Ticket#")).text()
            row_po_num = self.model.item(row, self.headers.index("PO#")).text()
            if row_job_ticket == job_ticket and row_po_num == po_num:
                self.jobs_table.selectRow(row)
                break

    def open_new_job_wizard(self):
        wizard = NewJobWizard(self, base_path=self.base_path)
        wizard.setWindowTitle("New Job")

        if wizard.exec():
            job_data = wizard.get_data()
            # create_job_folder_and_checklist handles folder creation, json saving, and copying
            job_created = self.create_job_folder_and_checklist(job_data)
            
            if job_created:
                # Add to table and our in-memory list
                self.add_job_to_table(job_data)
                # Ensure new directories are monitored
                self.ensure_directory_monitoring()
                # No longer need to call save_data() as persistence is handled by folder creation
        else:
            print("job not created")

    def add_job_to_table(self, job_data):
        # This function will now just handle the view
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Job Ticket#", "")),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(job_data.get("Quantity", "")),
            QStandardItem(job_data.get("Due Date", ""))
        ]
        self.model.appendRow(row_items)
        # Add the full job data to our source of truth list
        if job_data not in self.all_jobs:
            self.all_jobs.append(job_data)

    def load_jobs(self):
        """
        Loads jobs by scanning the ACTIVE_JOBS_SOURCE_DIR for job_data.json files.
        This is now the single source of truth for active jobs on startup.
        """
        self.all_jobs = []
        self.model.removeRows(0, self.model.rowCount())

        active_source_dir = config.ACTIVE_JOBS_SOURCE_DIR
        if not os.path.exists(active_source_dir):
            print(f"Active jobs source directory not found, creating it: {active_source_dir}")
            os.makedirs(active_source_dir)
            return

        for root, _, files in os.walk(active_source_dir):
            if "job_data.json" in files:
                job_data_path = os.path.join(root, "job_data.json")
                try:
                    with open(job_data_path, "r", encoding='utf-8') as f:
                        job_data = json.load(f)
                    
                    # The path in the json might be from another system.
                    # The folder it resides in is the canonical path for the active source copy.
                    job_data['active_source_folder_path'] = root

                    # The primary path is also stored in the json, which is what we want.
                    self.add_job_to_table(job_data)

                except json.JSONDecodeError:
                    print(f"Error decoding JSON from {job_data_path}")
                except Exception as e:
                    print(f"Error loading job from {job_data_path}: {e}")

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

        menu.addAction("Create Job Folder...", self.create_folder_for_selected_job_with_location_picker)
        menu.addAction("Edit Job", self.edit_selected_job_in_details)
        menu.addSeparator()
        
        menu.addAction("Move to Archive", self.move_to_archive)
        menu.addAction("Delete Job", self.delete_selected_job)

        menu.exec(event.globalPos())

    def create_folder_for_selected_job_with_location_picker(self):
        """Create job folder with user-selected directory location."""
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return

        selected_row_index = selection_model.selectedRows()[0]
        
        job_data = {}
        for col, header in enumerate(self.headers):
            cell_index = self.model.index(selected_row_index.row(), col)
            job_data[header] = self.model.data(cell_index, Qt.DisplayRole)

        # Let user select where to create the job folder
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Directory to Create Job Folder", 
            "", 
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not directory:
            return  # User cancelled
        
        try:
            customer = job_data.get("Customer", "UnknownCustomer")
            label_size = job_data.get("Label Size", "UnknownLabelSize")
            po_num = job_data.get("PO#", "UnknownPO")
            job_ticket_num = job_data.get("Job Ticket#", "UnknownJobTicket")
            
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
                QMessageBox.warning(self, "Warning", f"Job folder already exists:\n{job_path}")
                return
            
            os.makedirs(job_path)
            
            # Get the full job data for creating JSON and PDF
            full_job_data = self._get_job_data_for_row(selected_row_index.row())
            if full_job_data:
                # Save job data JSON in the new folder
                full_job_data['job_folder_path'] = job_path
                try:
                    with open(os.path.join(job_path, "job_data.json"), "w") as f:
                        json.dump(full_job_data, f, indent=4)
                except IOError as e:
                    print(f"Could not save job_data.json: {e}")
                
                # Create checklist PDF
                self.create_checklist_pdf(full_job_data, job_path)
            
            QMessageBox.information(self, "Success", f"Job folder created successfully at:\n{job_path}")
            print(f"Successfully created job folder: {job_path}")
            
        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")

    def edit_selected_job_in_details(self):
        """Open the job details dialog in edit mode for the selected job."""
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
            
        selected_row_index = selection_model.selectedRows()[0]
        job_data = self._get_job_data_for_row(selected_row_index.row())
        
        if not job_data:
            QMessageBox.warning(self, "Error", "Could not retrieve job data.")
            return
        
        # Create and show the job details dialog
        dialog = JobDetailsDialog(job_data, self.base_path, self)
        
        # Connect signals to handle updates
        dialog.job_updated.connect(self.update_job_in_table)
        dialog.job_archived.connect(self.handle_job_archived)
        dialog.job_deleted.connect(lambda: self.delete_job_by_row(selected_row_index.row()))
        
        # Automatically enter edit mode
        dialog.enter_edit_mode()
        
        dialog.exec()

    def delete_selected_job(self):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return

        selected_row_index = selection_model.selectedRows()[0]
        job_to_delete = self._get_job_data_for_row(selected_row_index.row())

        if not job_to_delete:
            QMessageBox.warning(self, "Error", "Could not find job data to delete.")
            return

        reply = QMessageBox.question(self, 
                                     "Confirmation", 
                                     f"Are you sure you want to permanently delete this job and all its associated files?\n\nJob: {job_to_delete.get('PO#')} - {job_to_delete.get('Job Ticket#')}",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_job_files(job_to_delete)
            # Remove from the in-memory list and the table view
            del self.all_jobs[selected_row_index.row()]
            self.model.removeRow(selected_row_index.row())
        
        # Ensure monitoring continues after deletion
        self.ensure_directory_monitoring()

    def _get_job_data_for_row(self, row):
        if 0 <= row < len(self.all_jobs):
            return self.all_jobs[row]
        return None

    def move_to_archive(self):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
            
        reply = QMessageBox.question(self, "Confirmation", "Are you sure you want to move this job to the archive?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        selected_row = selection_model.selectedRows()[0].row()
        job_data = self._get_job_data_for_row(selected_row)
        
        job_folder_path = job_data.get('job_folder_path')
        
        if not job_folder_path or not os.path.exists(job_folder_path):
            QMessageBox.warning(self, "Archive Error", "Original job folder not found or path not set. Cannot archive.")
            # We should also check the active source folder and offer to archive from there.
            # For now, we stick to the original logic.
            return

        # Emit the job data to the archive page
        self.job_to_archive.emit(job_data)

        # Since it's archived, we delete it from the active jobs directories
        self._delete_job_files(job_data)

        # Remove the job from the active list
        self.model.removeRow(selected_row)
        del self.all_jobs[selected_row]
        
        # Ensure monitoring continues after archiving
        self.ensure_directory_monitoring()
        
        QMessageBox.information(self, "Success", "Job has been successfully archived.")

    def handle_new_job_creation(self, job_data, save_locations):
        '''
        This function is called when a new job is created.
        It will create a new job folder and fill the checklist with the job data.
        '''
        try:
            job_path = self._create_job_folders(job_data, save_locations)

            if not job_path:
                return
            
            self.add_job_to_table(job_data)
            
            self.create_checklist_pdf(job_data, job_path)


            QMessageBox.information(self, "Success", "Job created successfully")

        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")

    def create_checklist_pdf(self, job_data, job_path):
        """
        Generates a checklist for the job and saves it in the specified job_path.
        """
        template_path = os.path.join(self.base_path, "data", "Encoding Checklist V4.1.pdf")

        if not os.path.exists(template_path):
            QMessageBox.warning(self, "Missing Template", "Could not find the PDF work order template. Skipping PDF generation.")
            return
        
        fields_to_fill = {
            "Customer": "customer",
            "Part#": "part_num",
            "Job Ticket#": "job_ticket",
            "PO#": "customer_po",
            "Inlay Type": "inlay_type",
            "Label Size": "label_size",
            "Quantity": "qty",
            "Item": "item",
            "UPC Number": "upc",
            "LPR": "lpr",
            "Rolls": "rolls",
            "Start":"start",
            "End":"end",
            "Date": "Date",
        }

        output_file_name = f"{job_data.get('Customer', '')}-{job_data.get('Job Ticket#', '')}-{job_data.get('PO#', '')}-Checklist.pdf"
        save_path = os.path.join(job_path, output_file_name)

        
        try:
            doc = fitz.open(template_path)
            for page in doc:
                for widget in page.widgets():
                    for data_key, pdf_key in fields_to_fill.items():
                        if widget.field_name == pdf_key:
                            value = ""
                            if data_key == "Date":
                                value = datetime.now().strftime('%m/%d/%Y')
                            else:
                                value = job_data.get(data_key, "")
                            
                            widget.field_value = str(value)
                            widget.update()
                            break 
            
            doc.save(save_path, garbage=4, deflate=True)
            doc.close()
            print(f"Checklist created successfully at:\n{save_path}")
        except Exception as e:
            print(f"Error processing PDF: {e}")
            QMessageBox.critical(self, "PDF Error", f"Could not generate checklist PDF:\n{e}")

    def open_job_details(self, index):
        """Open job details window when job is double-clicked"""
        if not index.isValid():
            return
            
        row = index.row()
        job_data = self._get_job_data_for_row(row)
        
        # Create and show the job details dialog
        dialog = JobDetailsDialog(job_data, self.base_path, self)
        
        # Connect signals
        dialog.job_updated.connect(self.update_job_in_table)
        dialog.job_archived.connect(self.handle_job_archived)
        dialog.job_deleted.connect(lambda: self.delete_job_by_row(row))
        
        dialog.exec()
        
    def update_job_in_table(self, updated_job_data):
        """Update job data in the table and filesystem. Called from details dialog."""
        # Find the row with matching job data and update it
        for i, job in enumerate(self.all_jobs):
            # Use a reliable identifier to find the job
            if (job.get('job_folder_path') == updated_job_data.get('job_folder_path')):
                self._update_job(i, updated_job_data)
                break

    def _update_job(self, row_index, new_data):
        """The core logic for updating a job's files and data."""
        current_data = self.all_jobs[row_index]
        old_primary_path = current_data.get('job_folder_path')

        if not old_primary_path:
            QMessageBox.critical(self, "Update Error", "Cannot update job: Original folder path is missing.")
            return

        # --- 1. Determine new path for the primary job folder ---
        try:
            # Preserve creation date from the original folder name
            old_folder_name = os.path.basename(old_primary_path)
            date_part = old_folder_name.split(' - ')[0]
        except IndexError:
            date_part = datetime.now().strftime("%y-%m-%d") # Fallback
        
        customer = new_data.get("Customer")
        label_size = new_data.get("Label Size")
        po_num = new_data.get("PO#")
        job_ticket = new_data.get("Job Ticket#")
        new_folder_name = f"{date_part} - {po_num} - {job_ticket}"
        
        # Reconstruct the base path (e.g., C:/Users/../Desktop) from the old full path
        base_primary_path = os.path.dirname(os.path.dirname(os.path.dirname(old_primary_path)))
        new_primary_path = os.path.join(base_primary_path, customer, label_size, new_folder_name)

        # --- 2. Move the primary folder if its path has changed ---
        if old_primary_path != new_primary_path:
            try:
                print(f"Path changed. Moving from {old_primary_path} to {new_primary_path}")
                os.makedirs(os.path.dirname(new_primary_path), exist_ok=True)
                shutil.move(old_primary_path, new_primary_path)
            except Exception as e:
                QMessageBox.critical(self, "File Error", f"Could not move job folder: {e}.\nUpdate aborted.")
                return

        # --- 3. Update the job_data.json file inside the new primary folder location ---
        new_data['job_folder_path'] = new_primary_path
        try:
            with open(os.path.join(new_primary_path, "job_data.json"), "w") as f:
                json.dump(new_data, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Could not update job_data.json: {e}.\nUpdate aborted.")
            return

        # --- 4. Synchronize change with the active jobs source directory ---
        try:
            # First, remove the old version from the active source directory
            old_active_source_path = os.path.join(config.ACTIVE_JOBS_SOURCE_DIR, current_data.get("Customer"), current_data.get("Label Size"), old_folder_name)
            if os.path.exists(old_active_source_path):
                shutil.rmtree(old_active_source_path)
            
            # Then, copy the updated primary folder to the active source directory
            new_active_source_path = os.path.join(config.ACTIVE_JOBS_SOURCE_DIR, customer, label_size, new_folder_name)
            shutil.copytree(new_primary_path, new_active_source_path)
            print(f"Successfully synced update to {new_active_source_path}")
        except Exception as e:
            QMessageBox.warning(self, "Sync Error", f"Could not synchronize job update to the active source directory: {e}")

        # --- 5. Update the in-memory list and the UI table ---
        self.all_jobs[row_index] = new_data
        for col, header in enumerate(self.headers):
            if header in new_data:
                item = QStandardItem(str(new_data[header]))
                self.model.setItem(row_index, col, item)
        
        # Ensure directories are still being monitored after changes
        self.ensure_directory_monitoring()

    def handle_job_archived(self, job_data):
        """Handle job being archived from details dialog"""
        self.job_to_archive.emit(job_data)
        
        # Find the row and remove it, deleting files as part of the process
        for i, job in enumerate(self.all_jobs):
            if (job.get('job_folder_path') == job_data.get('job_folder_path')):
                self._delete_job_files(job_data)
                self.model.removeRow(i)
                del self.all_jobs[i]
                break
        
        # Ensure monitoring continues after archiving
        self.ensure_directory_monitoring()

    def delete_job_by_row(self, row):
        """Delete job by row index, including all its files."""
        if 0 <= row < self.model.rowCount():
            job_data = self._get_job_data_for_row(row)
            
            reply = QMessageBox.question(self, "Delete Job", 
                                       f"This will permanently delete the job and all its files. Are you sure?\n\nFolder: {job_data.get('job_folder_path')}",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)

            if reply == QMessageBox.StandardButton.Yes:
                self._delete_job_files(job_data)
                self.model.removeRow(row)
                del self.all_jobs[row]
                
                # Ensure monitoring continues after deletion
                self.ensure_directory_monitoring()

    def _delete_job_files(self, job_data):
        """Deletes job folders from primary and active source locations."""
        # 1. Delete from primary location
        primary_path = job_data.get('job_folder_path')
        if primary_path and os.path.exists(primary_path):
            try:
                shutil.rmtree(primary_path)
                print(f"Deleted primary folder: {primary_path}")
            except Exception as e:
                QMessageBox.warning(self, "Delete Error", f"Could not delete primary job folder.\n{e}")
        
        # 2. Delete from active jobs source
        try:
            old_folder_name = os.path.basename(primary_path)
            active_source_path = os.path.join(config.ACTIVE_JOBS_SOURCE_DIR, job_data.get("Customer"), job_data.get("Label Size"), old_folder_name)
            if os.path.exists(active_source_path):
                shutil.rmtree(active_source_path)
                print(f"Deleted active source folder: {active_source_path}")
        except Exception as e:
             QMessageBox.warning(self, "Delete Error", f"Could not delete active source job folder.\n{e}")

    def create_job_folder_and_checklist(self, job_data):
        if job_data.get('Shared Drive'):
            base_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        elif job_data.get('Desktop'):
            base_path = os.path.expanduser("~/Desktop")
        elif job_data.get('Custom Path'):
            base_path = job_data['Custom Path']
        else:
            QMessageBox.warning(self, "Error", "No save location selected.")
            return

        try:
            customer = job_data.get("Customer")
            label_size = job_data.get("Label Size")
            current_date = datetime.now().strftime("%y-%m-%d")
            po_num = job_data.get("PO#")
            job_ticket = job_data.get("Job Ticket#")
            
            if not all([customer, label_size, po_num, job_ticket]):
                QMessageBox.warning(self, "Missing Information", "Customer, Label Size, PO#, and Job Ticket# are required to create a folder.")
                return

            job_folder_name = f"{current_date} - {po_num} - {job_ticket}"
            customer_path = os.path.join(base_path, customer)
            label_size_path = os.path.join(customer_path, label_size)
            job_folder_path = os.path.join(label_size_path, job_folder_name)
            
            job_data['job_folder_path'] = job_folder_path

            os.makedirs(job_folder_path, exist_ok=True)
            print(f"Successfully created job folder: {job_folder_path}")

            # Save job data to a JSON file within the folder
            try:
                with open(os.path.join(job_folder_path, "job_data.json"), "w") as f:
                    json.dump(job_data, f, indent=4)
            except IOError as e:
                QMessageBox.warning(self, "Save Error", f"Could not save job_data.json.\n{e}")
            
            self.create_checklist_pdf(job_data, job_folder_path)

            # Copy to active jobs source directory
            source_dest_path = os.path.join(config.ACTIVE_JOBS_SOURCE_DIR, customer, label_size)
            os.makedirs(source_dest_path, exist_ok=True)
            
            try:
                shutil.copytree(job_folder_path, os.path.join(source_dest_path, job_folder_name))
                print(f"Successfully copied job folder to: {os.path.join(source_dest_path, job_folder_name)}")
            except FileExistsError:
                print(f"Folder already exists in active source, skipping copy: {os.path.join(source_dest_path, job_folder_name)}")
                # For a new job, this indicates a likely duplicate. We should warn the user.
                QMessageBox.warning(self, "Duplicate Warning", f"A folder with the same name already exists in the active source directory. The job was created in the primary location, but not copied.")
                pass
            except Exception as e:
                QMessageBox.warning(self, "Copy Error", f"Could not copy job folder to active source directory.\n\nError: {e}")
            
            # Ensure new directories are being monitored
            self.ensure_directory_monitoring()
            
            return True # Indicate success

        except Exception as e:
            print(f"Job not created: {e}")
            return False

    def closeEvent(self, event):
        """Clean up file system watcher when widget is destroyed."""
        if hasattr(self, 'file_watcher'):
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
            cell_index = self.model.index(selected_row_index.row(), col)
            job_data[header] = self.model.data(cell_index, Qt.DisplayRole)

        # Use default network path for context menu folder creation
        self._create_job_folders(job_data, [self.network_path])

    def _create_job_folders(self, job_data, save_locations=None):
        """Create job folders in specified locations (kept for backward compatibility)."""
        try:
            # If no save_locations provided, fall back to the default network path
            if not save_locations:
                save_locations = [self.network_path]
                  
            current_date = datetime.now().strftime("%y-%m-%d")
            po_num = job_data.get("PO#", "UnknownPO")
            job_ticket_num = job_data.get("Job Ticket#", "UnknownJobTicket")
            customer = job_data.get("Customer", "UnknownCustomer")
            label_size = job_data.get("Label Size", "UnknownLabelSize")
            job_folder_name = f"{current_date} - {po_num} - {job_ticket_num}"

            created_folders = []
            
            for save_location in save_locations:
                if not os.path.exists(save_location):
                    QMessageBox.critical(self, "Error", f"Save location not accessible: {save_location}")
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
                        QMessageBox.critical(self, "Error", f"Customer folder not found: {customer}\nPlease make sure the customer folder exists in the network drive.")
                        continue
                        
                    if not os.path.exists(label_size_path):
                        QMessageBox.critical(self, "Error", f"Label size folder not found for customer {customer}: {label_size}\nPlease make sure the label size folder exists in the customer directory.")
                        continue
                
                if os.path.exists(job_path):
                    QMessageBox.warning(self, "Warning", f"Job folder already exists:\n{job_path}")
                    continue
                    
                os.makedirs(job_path)
                created_folders.append(job_path)
                print(f"Successfully created job folder: {job_path}")

                # Return the first successfully created job path for checklist generation
                if created_folders:
                    return created_folders[0]
            
            if created_folders:
                folder_list = "\n".join(created_folders)
                QMessageBox.information(self, "Success", f"Job folder(s) created at:\n{folder_list}")
            else:
                QMessageBox.warning(self, "Warning", "No job folders were created.")
                return None
                
        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")
            return None
