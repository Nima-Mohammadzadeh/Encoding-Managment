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
from PySide6.QtCore import Qt, Signal
from src.wizards.new_job_wizard import NewJobWizard
from src.shared_job_manager import sync_jobs, get_sync_status, is_shared_available

class JobPageWidget(QWidget):
    job_to_archive = Signal(dict)
    
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.save_file = os.path.join(self.base_path, "data", "active_jobs.json")
        self.network_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        layout = QVBoxLayout(self)

        actions_layout = QHBoxLayout()
        self.add_job_button = QPushButton("Add Job")
        self.add_job_button.clicked.connect(self.open_new_job_wizard)

        # Add sync button (square-ish shape)
        self.sync_button = QPushButton("🔄")
        self.sync_button.setFixedSize(32, 32)
        self.sync_button.setToolTip("Sync jobs with shared drive\nClick to refresh team jobs")
        self.sync_button.clicked.connect(self.sync_with_shared)
        
        actions_layout.addWidget(self.add_job_button)
        actions_layout.addWidget(self.sync_button)
        actions_layout.addStretch()  # Push buttons to the left
        layout.addLayout(actions_layout)

        self.model = QStandardItemModel()
        self.headers = ([
        "Customer", "Part#", "Job Ticket#", "PO#",
         "Inlay Type", "Label Size", "Quantity", "Status"
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
        header.setSectionResizeMode(self.headers.index("Status"), QHeaderView.ResizeMode.ResizeToContents)
        self.jobs_table.verticalHeader().hide()
       
        layout.addWidget(self.jobs_table)
        self.setLayout(layout)

        self.load_jobs()
        self.update_sync_button_status()

    def open_new_job_wizard(self):
        wizard = NewJobWizard(self, base_path=self.base_path)
        wizard.setWindowTitle("New Job")

        if wizard.exec():
            job_data = wizard.get_data()
            save_locations = wizard.get_save_locations()
            print("New Job Made: ", job_data)
            self.handle_new_job_creation(job_data, save_locations, wizard)            
        else:
            print("job not created")

    def add_job_to_table(self, job_data, status="New"):
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Job Ticket#", "")),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(job_data.get("Quantity", "")),
            QStandardItem(status)
        ]
        self.model.appendRow(row_items)

    def load_jobs(self):
        if not os.path.exists(self.save_file):
            print("save file does not exist. Starting fresh.")
            return

        try:
            with open(self.save_file, "r") as f:
                data = json.load(f)
                
            for job in data:
                status = job.pop("Status", "")
                self.add_job_to_table(job, status=status)
        except Exception as e:
            print("Error loading jobs:", e)

    def save_data(self):
        data_to_save = []

        for row_index in range(self.model.rowCount()):
            job_data = {}
            for col, header in enumerate(self.headers):
                item = self.model.item(row_index, col)
                job_data[header] = item.text() if item else ""
            data_to_save.append(job_data)

        try:
            with open(self.save_file, "w") as f:
                json.dump(data_to_save, f, indent=4)
            
            # Auto-sync to shared drive after saving locally (silent)
            self.auto_sync_to_shared()
            
        except IOError as e:
            print(f"Error saving data: {e}")

    def contextMenuEvent(self, event):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return

        menu = QMenu(self)

        menu.addAction("Create Job Folder", self.create_folder_for_selected_job)
        menu.addAction("Edit Job", self.edit_selected_job)
        menu.addSeparator()
        
        
        submenu = QMenu("Change Status:", self)
        submenu.addAction("New", self.set_status("New"))
        submenu.addAction("In Progress", self.set_status("In Progress"))
        submenu.addAction("On Hold", self.set_status("On Hold"))
        submenu.addAction("Completed", self.set_status("Completed"))
        submenu.addAction("Cancelled", self.set_status("Cancelled"))
        menu.addMenu(submenu)

        menu.addSeparator()

        menu.addAction("Move to Archive", self.move_to_archive)
        menu.addAction("Delete Job", self.delete_selected_job)

        menu.exec(event.globalPos())

    def set_status(self, status):
        def update_status():
            selection_model = self.jobs_table.selectionModel()
            if not selection_model.hasSelection():
                return
            
            selected_row_index = selection_model.selectedRows()[0]
            status_column = self.headers.index("Status")
            status_index = self.model.index(selected_row_index.row(), status_column)
            
            self.model.setData(status_index, status, Qt.EditRole)
            self.save_data()
        
        return update_status

    def create_folder_for_selected_job(self):
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

    def edit_selected_job(self):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
        selected_row_index = selection_model.selectedRows()[0]
        
        current_data = self._get_job_data_for_row(selected_row_index.row())

        wizard = NewJobWizard(self, base_path=self.base_path)
        wizard.setWindowTitle("Edit Job")
        wizard.set_all_data(current_data)

        # For editing, we don't need to re-select the save location
        # so we can hide that page.
        wizard.setPage(2, QWidget()) # Hides the save location page
        wizard.page(2).setVisible(False)


        if wizard.exec():
            new_data = wizard.get_data()
            for col, header in enumerate(self.headers):
                if header in new_data:
                    cell_index = self.model.index(selected_row_index.row(), col)
                    self.model.setData(cell_index, new_data[header], Qt.EditRole)
            
            self.save_data()

    def delete_selected_job(self):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
        reply = QMessageBox.question(self, 
                                     "Confirmation", 
                                     "Are you sure you want to delete this job?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            selected_row_index = selection_model.selectedRows()[0]
            
            # Get job data before deleting to track the deletion
            job_data = self._get_job_data_for_row(selected_row_index.row())
            
            # Track that this job was intentionally deleted locally
            from src.shared_job_manager import track_job_deletion
            track_job_deletion(job_data, "active")
            
            self.model.removeRow(selected_row_index.row())
        
        self.save_data()

    def _get_job_data_for_row(self, row):
        job_data = {}
        for col, header in enumerate(self.headers):
            item = self.model.item(row, col)
            job_data[header] = item.text() if item else ""
        return job_data

    def move_to_archive(self):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
        reply = QMessageBox.question(self, "Confirmation", "Are you sure you want to move this job to the archive?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            selected_row = selection_model.selectedRows()[0].row()

            job_data = self._get_job_data_for_row(selected_row)
            
            # Add archive date before emitting
            job_data['dateArchived'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            self.job_to_archive.emit(job_data)

            self.model.removeRow(selected_row)
            
            self.save_data() 

    def handle_new_job_creation(self, job_data, save_locations, wizard=None):
        '''
        This function is called when a new job is created.
        It will assign serial numbers, create a job folder and fill the checklist with the job data.
        '''
        try:
            # First, assign serial numbers if wizard is provided
            if wizard:
                success, message = wizard.assign_serial_numbers()
                if not success:
                    QMessageBox.warning(self, "Serial Number Warning", 
                                      f"Could not assign serial numbers: {message}\n\n"
                                      "Job will be created without serial numbers.")
                else:
                    print(f"✅ {message}")
                    # Update job_data with the newly assigned serial numbers
                    job_data.update(wizard.get_data())

            job_path = self._create_job_folders(job_data, save_locations)

            if not job_path:
                return
            
            self.add_job_to_table(job_data)
            
            self._generate_checklist(job_data, job_path)

            QMessageBox.information(self, "Success", "Job created successfully")

        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")

    def _generate_checklist(self, job_data, job_path):
        '''
        This function is called when a new job is created.
        It will generate a checklist for the job.
        '''
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
            "Start Serial": "start",
            "End Serial": "stop",
            "Date": "Date",
        }

        output_file_name = f"{job_data.get('Customer', '')}-{job_data.get('Job Ticket#', '')}-{job_data.get('PO#', '')}-Checklist.pdf"
        save_path = os.path.join(job_path, output_file_name)

        
        try:
            doc = fitz.open(template_path)
            for page in doc:
                for widget in page.widgets():
                    # First, let's find the field names in your PDF
                    print(f"Found PDF form field: '{widget.field_name}'")

                    # Now, let's try to fill it
                    for data_key, pdf_key in fields_to_fill.items():
                        if widget.field_name == pdf_key:
                            value = ""
                            if data_key == "Date":
                                value = datetime.now().strftime('%m/%d/%Y')
                            else:
                                value = job_data.get(data_key, "")
                            
                            widget.field_value = value
                            widget.update()
                            break # Found and updated, move to the next widget
            
            # The fields are filled, now we save the document.
            # To make fields non-editable (flatten), use garbage=4.
            doc.save(save_path, garbage=4, deflate=True)
            doc.close()
            print(f"Checklist created successfully at:\n{save_path}")
        except Exception as e:
            print(f"Error processing PDF: {e}")
            QMessageBox.critical(self, "PDF Error", f"Could not generate checklist PDF:\n{e}")

    def sync_with_shared(self):
        """Sync jobs with the shared drive."""
        # Show sync button as working
        self.sync_button.setText("⏳")
        self.sync_button.setEnabled(False)
        
        try:
            # Perform the sync
            result = sync_jobs()
            
            if result["success"]:
                # Reload the table with merged data
                self.reload_jobs_table()
                
                # Show success message with stats
                stats = result["stats"]
                message = f"✅ Sync completed successfully!\n\n"
                message += f"📊 Statistics:\n"
                message += f"• Active jobs: {stats['active_jobs_merged']} (local: {stats['active_jobs_local']}, shared: {stats['active_jobs_shared']})\n"
                message += f"• Archived jobs: {stats['archived_jobs_merged']} (local: {stats['archived_jobs_local']}, shared: {stats['archived_jobs_shared']})\n"
                
                if stats['conflicts_resolved'] > 0:
                    message += f"• Conflicts resolved: {stats['conflicts_resolved']}\n"
                
                message += f"• Sync duration: {stats['sync_duration']}s"
                
                QMessageBox.information(self, "Sync Complete", message)
                
            else:
                # Show error message
                QMessageBox.warning(self, "Sync Failed", f"Could not sync with shared drive:\n\n{result['message']}")
                
        except Exception as e:
            QMessageBox.critical(self, "Sync Error", f"An error occurred during sync:\n{str(e)}")
        
        finally:
            # Reset sync button
            self.update_sync_button_status()

    def reload_jobs_table(self):
        """Smart reload that preserves table formatting and state."""
        # Save current table state
        current_selection = None
        selection_model = self.jobs_table.selectionModel()
        if selection_model.hasSelection():
            selected_row = selection_model.selectedRows()[0].row()
            current_selection = self._get_job_data_for_row(selected_row)
        
        # Save current sort state
        header = self.jobs_table.horizontalHeader()
        sort_column = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        
        # Load updated jobs from file
        if not os.path.exists(self.save_file):
            print("No jobs file found during reload")
            return
            
        try:
            with open(self.save_file, "r") as f:
                updated_jobs = json.load(f)
        except Exception as e:
            print(f"Error loading jobs during reload: {e}")
            return
        
        # Smart update: only change what's different
        self._smart_update_table(updated_jobs, current_selection, sort_column, sort_order)

    def _smart_update_table(self, updated_jobs, previous_selection, sort_column, sort_order):
        """Update table content while preserving formatting."""
        
        # Create a map of existing jobs for quick lookup
        existing_jobs = {}
        for row in range(self.model.rowCount()):
            job_data = self._get_job_data_for_row(row)
            job_key = f"{job_data.get('Customer', '')}-{job_data.get('Job Ticket#', '')}-{job_data.get('PO#', '')}"
            existing_jobs[job_key] = row
        
        # Create a map of updated jobs
        updated_job_keys = set()
        
        # Process each updated job
        for job in updated_jobs:
            status = job.pop("Status", "New")
            job["Status"] = status  # Put it back for processing
            
            job_key = f"{job.get('Customer', '')}-{job.get('Job Ticket#', '')}-{job.get('PO#', '')}"
            updated_job_keys.add(job_key)
            
            if job_key in existing_jobs:
                # Update existing job
                row = existing_jobs[job_key]
                self._update_table_row(row, job)
            else:
                # Add new job
                self.add_job_to_table(job, job["Status"])
        
        # Remove jobs that no longer exist (in reverse order to maintain indices)
        rows_to_remove = []
        for job_key, row in existing_jobs.items():
            if job_key not in updated_job_keys:
                rows_to_remove.append(row)
        
        for row in sorted(rows_to_remove, reverse=True):
            self.model.removeRow(row)
        
        # Restore sort state
        if sort_column >= 0:
            self.jobs_table.sortByColumn(sort_column, sort_order)
        
        # Restore selection if possible
        if previous_selection:
            self._restore_selection(previous_selection)
        
        print(f"✅ Smart table update: {len(updated_jobs)} jobs processed")

    def _update_table_row(self, row, job_data):
        """Update a specific row with new job data."""
        for col, header in enumerate(self.headers):
            item = self.model.item(row, col)
            if item:
                new_value = job_data.get(header, "")
                if item.text() != new_value:
                    item.setText(new_value)

    def _restore_selection(self, job_data):
        """Try to restore the previously selected job."""
        target_key = f"{job_data.get('Customer', '')}-{job_data.get('Job Ticket#', '')}-{job_data.get('PO#', '')}"
        
        for row in range(self.model.rowCount()):
            current_job = self._get_job_data_for_row(row)
            current_key = f"{current_job.get('Customer', '')}-{current_job.get('Job Ticket#', '')}-{current_job.get('PO#', '')}"
            
            if current_key == target_key:
                # Restore selection
                selection_model = self.jobs_table.selectionModel()
                index = self.model.index(row, 0)
                selection_model.select(index, selection_model.SelectionFlag.ClearAndSelect | selection_model.SelectionFlag.Rows)
                break

    def update_sync_button_status(self):
        """Update the sync button appearance based on shared drive availability."""
        if is_shared_available():
            self.sync_button.setText("🔄")
            self.sync_button.setEnabled(True)
            self.sync_button.setStyleSheet("")
            
            # Get sync status for tooltip
            status = get_sync_status()
            if status.get("last_sync"):
                last_sync = status["last_sync"]
                sync_count = status.get("sync_count", 0)
                conflicts = status.get("conflicts_resolved", 0)
                
                tooltip = f"Sync jobs with shared drive\n"
                tooltip += f"Last sync: {last_sync[:16]}\n"
                tooltip += f"Total syncs: {sync_count}"
                if conflicts > 0:
                    tooltip += f"\nConflicts resolved: {conflicts}"
            else:
                tooltip = "Sync jobs with shared drive\nNever synced"
                
            self.sync_button.setToolTip(tooltip)
        else:
            self.sync_button.setText("⚠️")
            self.sync_button.setEnabled(False)
            self.sync_button.setStyleSheet("background-color: #ffcccc;")
            self.sync_button.setToolTip("Shared drive not accessible\nCannot sync at this time")

    def auto_sync_to_shared(self):
        """Automatically sync to shared drive in background (silent)."""
        try:
            if is_shared_available():
                result = sync_jobs()
                if result["success"]:
                    print(f"✅ Auto-sync completed: {result['stats']['active_jobs_merged']} active, {result['stats']['archived_jobs_merged']} archived")
                    # Update sync button status to reflect latest sync
                    self.update_sync_button_status()
                else:
                    print(f"⚠️  Auto-sync failed: {result['message']}")
        except Exception as e:
            print(f"Auto-sync error: {e}")