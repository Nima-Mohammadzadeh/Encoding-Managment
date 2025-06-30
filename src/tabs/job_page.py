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
from src.widgets.job_details_dialog import JobDetailsDialog

class JobPageWidget(QWidget):
    job_to_archive = Signal(dict)
    
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.save_file = os.path.join(self.base_path, "data", "active_jobs.json")
        self.network_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        self.all_jobs = [] # This will be the source of truth
        layout = QVBoxLayout(self)

        actions_layout = QHBoxLayout()
        self.add_job_button = QPushButton("Add Job")
        self.add_job_button.clicked.connect(self.open_new_job_wizard)

        actions_layout.addWidget(self.add_job_button)
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

        # Add double-click handler for the table
        self.jobs_table.doubleClicked.connect(self.open_job_details)

    def open_new_job_wizard(self):
        wizard = NewJobWizard(self, base_path=self.base_path)
        wizard.setWindowTitle("New Job")

        if wizard.exec():
            job_data = wizard.get_data()
            # Create the job folder first and set the job_folder_path
            self.create_job_folder_and_checklist(job_data)
            # Then add to table and save (now with the job_folder_path included)
            self.add_job_to_table(job_data)
            self.save_data()
        else:
            print("job not created")

    def add_job_to_table(self, job_data, status="New"):
        # This function will now just handle the view
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Job Ticket#", "")),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(job_data.get("Quantity", "")),
            QStandardItem(job_data.get("Status", "New"))
        ]
        self.model.appendRow(row_items)
        # Add the full job data to our source of truth list
        if job_data not in self.all_jobs:
            self.all_jobs.append(job_data)

    def load_jobs(self):
        if not os.path.exists(self.save_file):
            print("save file does not exist. Starting fresh.")
            return

        try:
            with open(self.save_file, "r") as f:
                self.all_jobs = json.load(f)
                
            for job in self.all_jobs:
                self.add_job_to_table(job, status=job.get("Status", "New"))
        except Exception as e:
            print("Error loading jobs:", e)

    def save_data(self):
        try:
            with open(self.save_file, "w") as f:
                json.dump(self.all_jobs, f, indent=4)
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
            self.model.removeRow(selected_row_index.row())
            # Also remove from our source of truth
            del self.all_jobs[selected_row_index.row()]
        
        self.save_data()

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
            return

        # Emit the job data to the archive page
        self.job_to_archive.emit(job_data)

        # Remove the job from the active list
        self.model.removeRow(selected_row)
        del self.all_jobs[selected_row]
        self.save_data()
        
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
        """Update job data in the table"""
        # Find the row with matching job data and update it
        for i, job in enumerate(self.all_jobs):
            if (job.get('Job Ticket#') == updated_job_data.get('Job Ticket#') and
                job.get('PO#') == updated_job_data.get('PO#')):
                
                # Update the source of truth
                self.all_jobs[i] = updated_job_data
                
                # Update the view
                for col, header in enumerate(self.headers):
                    if header in updated_job_data:
                        item = QStandardItem(str(updated_job_data[header]))
                        self.model.setItem(i, col, item)
                break
        self.save_data()
        
    def handle_job_archived(self, job_data):
        """Handle job being archived from details dialog"""
        self.job_to_archive.emit(job_data)
        # Remove from current table
        # Find the row with matching job data and remove it
        for i, job in enumerate(self.all_jobs):
            if (job.get('Job Ticket#') == job_data.get('Job Ticket#') and
                job.get('PO#') == job_data.get('PO#')):
                self.model.removeRow(i)
                del self.all_jobs[i]
                break
        self.save_data()
        
    def delete_job_by_row(self, row):
        """Delete job by row index"""
        if 0 <= row < self.model.rowCount():
            job_data = self._get_job_data_for_row(row)
            job_folder_path = job_data.get('job_folder_path')

            reply = QMessageBox.question(self, "Delete Job", 
                                       f"This will delete the job from the list. If a job folder exists, do you want to delete it as well?\n\nFolder: {job_folder_path}",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

            if reply == QMessageBox.StandardButton.Cancel:
                return

            if reply == QMessageBox.StandardButton.Yes:
                if job_folder_path and os.path.exists(job_folder_path):
                    try:
                        shutil.rmtree(job_folder_path)
                        QMessageBox.information(self, "Folder Deleted", "The job folder has been deleted.")
                    except Exception as e:
                        QMessageBox.warning(self, "Folder Error", f"Could not delete the job folder.\n{e}")
            
            self.model.removeRow(row)
            del self.all_jobs[row]
            self.save_data()

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
            
            self.create_checklist_pdf(job_data, job_folder_path)

        except Exception as e:
            print(f"Job not created: {e}")