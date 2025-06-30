import os
import json
import subprocess
import platform
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QTextEdit, QComboBox, QListWidget,
    QTabWidget, QWidget, QMessageBox, QGridLayout, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
import fitz
import shutil
import src.config as config

class JobDetailsDialog(QDialog):
    job_updated = Signal(dict)
    job_archived = Signal(dict)
    job_deleted = Signal()
    
    def __init__(self, job_data, base_path, parent=None):
        super().__init__(parent)
        self.job_data = job_data.copy()
        self.base_path = base_path
        self.network_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        
        self.setWindowTitle(f"Job Details: {job_data.get('Job Ticket#', 'N/A')}")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        self.setStyleSheet(self.get_stylesheet())
        
        self.job_fields_read = {}
        self.encoding_fields_read = {}
        self.job_fields_edit = {}
        self.encoding_fields_edit = {}
        
        self.setup_ui()
        self.load_job_data()
        self.check_directories()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        main_layout.addWidget(self.tab_widget)

        # Create and add tabs
        self.overview_tab = QWidget()
        self.file_manager_tab = QWidget()
        
        self.tab_widget.addTab(self.overview_tab, "Job Overview")
        self.tab_widget.addTab(self.file_manager_tab, "File Manager")
        
        self.populate_overview_tab()
        self.populate_file_manager_tab()
        
    def create_header(self):
        header_widget = QWidget()
        header_widget.setObjectName("headerWidget")
        layout = QGridLayout(header_widget)
        
        # Job Title
        title_text = f"{self.job_data.get('Customer', 'Unknown Cust.')} - {self.job_data.get('Part#', 'N/A')}"
        title_label = QLabel(title_text)
        title_label.setObjectName("headerTitle")
        layout.addWidget(title_label, 0, 0, 1, 3)
        
        # Status
        status_label = QLabel(f"Status: {self.job_data.get('Status', 'New')}")
        status_label.setObjectName("headerStatus")
        layout.addWidget(status_label, 1, 0, 1, 3)
        
        # Action Buttons
        self.edit_btn = QPushButton("Edit Job")
        self.edit_btn.clicked.connect(self.enter_edit_mode)
        layout.addWidget(self.edit_btn, 0, 3)
        
        complete_btn = QPushButton("Complete Job")
        complete_btn.clicked.connect(self.complete_job)
        layout.addWidget(complete_btn, 1, 3)

        archive_btn = QPushButton("Archive Job")
        archive_btn.clicked.connect(self.archive_job)
        layout.addWidget(archive_btn, 0, 4)

        delete_btn = QPushButton("Delete Job")
        delete_btn.setObjectName("deleteButton")
        delete_btn.clicked.connect(self.delete_job)
        layout.addWidget(delete_btn, 1, 4)

        layout.setColumnStretch(2, 1)
        return header_widget
        
    def populate_overview_tab(self):
        layout = QVBoxLayout(self.overview_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Job Details Group
        job_details_group = QGroupBox("Job Information")
        form_layout = QFormLayout(job_details_group)
        job_field_keys = ["Customer", "Part#", "Job Ticket#", "PO#", "Inlay Type", "Label Size", "Quantity"]
        for key in job_field_keys:
            label = QLabel(f"{key}:")
            value = QLabel(self.job_data.get(key, ''))
            value.setObjectName("readOnlyField")
            form_layout.addRow(label, value)
            self.job_fields_read[key] = value
        layout.addWidget(job_details_group)
        
        # Encoding Details Group
        encoding_details_group = QGroupBox("Encoding Information")
        encoding_form_layout = QFormLayout(encoding_details_group)
        encoding_field_keys = ["Item", "UPC Number", "Serial Number", "LPR", "Rolls"]
        for key in encoding_field_keys:
            label = QLabel(f"{key}:")
            value = QLabel(self.job_data.get(key, ''))
            value.setObjectName("readOnlyField")
            encoding_form_layout.addRow(label, value)
            self.encoding_fields_read[key] = value
        layout.addWidget(encoding_details_group)
        
        layout.addStretch()

    def populate_file_manager_tab(self):
        layout = QVBoxLayout(self.file_manager_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Directory Status
        self.dir_status_label = QLabel("Checking directories...")
        layout.addWidget(self.dir_status_label)
        
        # Directory Actions
        dir_actions_layout = QHBoxLayout()
        self.open_dir_btn = QPushButton("Open Job Folder")
        self.open_dir_btn.clicked.connect(self.open_job_folder)
        self.create_dir_btn = QPushButton("Create Job Folder")
        self.create_dir_btn.clicked.connect(self.create_job_directory)
        dir_actions_layout.addWidget(self.open_dir_btn)
        dir_actions_layout.addWidget(self.create_dir_btn)
        dir_actions_layout.addStretch()
        layout.addLayout(dir_actions_layout)

        # File List
        self.files_list = QListWidget()
        self.files_list.doubleClicked.connect(self.open_selected_file)
        layout.addWidget(self.files_list)
        
        # Checklist Actions
        checklist_layout = QHBoxLayout()
        open_checklist_btn = QPushButton("Open Checklist PDF")
        open_checklist_btn.clicked.connect(self.open_checklist)
        regen_checklist_btn = QPushButton("Regenerate Checklist")
        regen_checklist_btn.clicked.connect(self.regenerate_checklist)
        checklist_layout.addWidget(open_checklist_btn)
        checklist_layout.addWidget(regen_checklist_btn)
        checklist_layout.addStretch()
        layout.addLayout(checklist_layout)

    def open_checklist(self):
        """Open the job checklist PDF in the default browser."""
        job_path = self.find_job_directory()
        if not job_path:
            QMessageBox.warning(self, "Checklist Not Found", "Job directory not found.")
            return

        try:
            for filename in os.listdir(job_path):
                if "checklist" in filename.lower() and filename.lower().endswith(".pdf"):
                    checklist_path = os.path.join(job_path, filename)
                    self.open_pdf_in_browser(checklist_path)
                    return
            
            QMessageBox.warning(self, "Checklist Not Found", "No checklist PDF found in the job directory.")
        except (OSError, PermissionError) as e:
            QMessageBox.critical(self, "Error", f"Could not access job directory: {e}")

    def enter_edit_mode(self):
        # Create edit tab if it doesn't exist
        if self.tab_widget.count() == 2:
            self.edit_tab = QWidget()
            self.populate_edit_tab()
            self.tab_widget.addTab(self.edit_tab, "Edit Job")
        
        self.tab_widget.setCurrentIndex(2)

    def populate_edit_tab(self):
        layout = QVBoxLayout(self.edit_tab)
        layout.setContentsMargins(15, 15, 15, 15)

        # Status
        status_group = QGroupBox("Job Status")
        status_layout = QHBoxLayout(status_group)
        self.status_combo = QComboBox()
        self.status_combo.addItems(["New", "In Progress", "On Hold", "Completed", "Cancelled"])
        self.status_combo.setCurrentText(self.job_data.get('Status', 'New'))
        status_layout.addWidget(QLabel("Status:"))
        status_layout.addWidget(self.status_combo)
        layout.addWidget(status_group)
        
        # Job Details Group
        job_details_group = QGroupBox("Job Information")
        form_layout = QFormLayout(job_details_group)
        job_field_keys = ["Customer", "Part#", "Job Ticket#", "PO#", "Inlay Type", "Label Size", "Quantity"]
        for key in job_field_keys:
            field = QLineEdit(self.job_data.get(key, ''))
            form_layout.addRow(f"{key}:", field)
            self.job_fields_edit[key] = field
        layout.addWidget(job_details_group)
        
        # Encoding Details Group
        encoding_details_group = QGroupBox("Encoding Information")
        encoding_form_layout = QFormLayout(encoding_details_group)
        encoding_field_keys = ["Item", "UPC Number", "Serial Number", "LPR", "Rolls"]
        for key in encoding_field_keys:
            field = QLineEdit(self.job_data.get(key, ''))
            encoding_form_layout.addRow(f"{key}:", field)
            self.encoding_fields_edit[key] = field
        layout.addWidget(encoding_details_group)
        
        # Save/Cancel Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("saveButton")
        save_btn.clicked.connect(self.save_changes)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.cancel_edit)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def save_changes(self):
        updated_data = {}
        for key, field in self.job_fields_edit.items():
            updated_data[key] = field.text()
        for key, field in self.encoding_fields_edit.items():
            updated_data[key] = field.text()
        updated_data['Status'] = self.status_combo.currentText()
        
        self.job_data.update(updated_data)
        self.job_updated.emit(self.job_data)
        
        # Update overview tab
        self.load_job_data()
        
        # Ask to regenerate checklist
        reply = QMessageBox.question(self, "Regenerate Checklist", 
                                   "Job data has been updated. Would you like to regenerate the checklist PDF?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.regenerate_checklist()
            
        self.cancel_edit() # Switch back to overview
        QMessageBox.information(self, "Success", "Job details have been updated.")

    def cancel_edit(self):
        self.tab_widget.setCurrentIndex(0)
    
    def complete_job(self):
        reply = QMessageBox.question(self, "Complete Job", "Are you sure you want to mark this job as completed?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.job_data['Status'] = 'Completed'
            self.job_updated.emit(self.job_data)
            self.load_job_data()
            QMessageBox.information(self, "Job Completed", "The job status has been set to 'Completed'.")

    def find_job_directory(self):
        job_paths = self.find_job_directories()
        for path in job_paths.values():
            if path and os.path.exists(path):
                return path
        return None

    def load_job_data(self):
        for key, field in self.job_fields_read.items():
            field.setText(self.job_data.get(key, ''))
        for key, field in self.encoding_fields_read.items():
            field.setText(self.job_data.get(key, ''))
        # Update header status
        header_status = self.findChild(QLabel, "headerStatus")
        if header_status:
            header_status.setText(f"Status: {self.job_data.get('Status', 'New')}")

    def check_directories(self):
        job_path = self.find_job_directory()
        if job_path:
            self.dir_status_label.setText(f"✅ Job directory found at: {job_path}")
            self.dir_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.open_dir_btn.setEnabled(True)
            self.create_dir_btn.setEnabled(False)
            self.refresh_files()
        else:
            self.dir_status_label.setText("❌ Job directory not found.")
            self.dir_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.open_dir_btn.setEnabled(False)
            self.create_dir_btn.setEnabled(True)

    def open_job_folder(self):
        job_path = self.find_job_directory()
        if job_path:
            self.open_path_in_explorer(job_path)

    def find_job_directories(self):
        # This is a simplified version for brevity. You can use your more complex one.
        customer = self.job_data.get('Customer', '')
        label_size = self.job_data.get('Label Size', '')
        po_num = self.job_data.get('PO#', '')
        job_ticket = self.job_data.get('Job Ticket#', '')
        
        if not all([customer, label_size, po_num, job_ticket]):
            return {}
            
        locations = {'shared_drive': self.network_path, 'desktop': os.path.expanduser("~/Desktop")}
        found_paths = {}

        for loc, base_path in locations.items():
            try:
                if os.path.exists(os.path.join(base_path, customer, label_size)):
                    label_path = os.path.join(base_path, customer, label_size)
                    for folder in os.listdir(label_path):
                        if po_num in folder and job_ticket in folder:
                            found_paths[loc] = os.path.join(label_path, folder)
                            break
            except (OSError, PermissionError):
                continue
        return found_paths

    def refresh_files(self):
        self.files_list.clear()
        job_path = self.find_job_directory()
        if job_path:
            try:
                for filename in os.listdir(job_path):
                    if os.path.isfile(os.path.join(job_path, filename)):
                        self.files_list.addItem(filename)
            except (OSError, PermissionError) as e:
                self.files_list.addItem(f"Error reading directory: {e}")

    def open_selected_file(self):
        item = self.files_list.currentItem()
        if not item: return
        
        job_path = self.find_job_directory()
        if job_path:
            file_path = os.path.join(job_path, item.text())
            if file_path.lower().endswith('.pdf'):
                self.open_pdf_in_browser(file_path)
            else:
                self.open_path_in_explorer(file_path)

    def open_pdf_in_browser(self, pdf_path):
        try:
            webbrowser.open(f"file:///{os.path.abspath(pdf_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open PDF: {e}")

    def open_path_in_explorer(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open path: {e}")
    
    def archive_job(self):
        reply = QMessageBox.question(self, "Archive Job", 
                                   "This will move the job's folder to the archive and remove it from the active list.\n\nAre you sure you want to proceed?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            job_folder_path = self.find_job_directory()
            
            # Move the job folder if it exists
            if job_folder_path and os.path.exists(job_folder_path):
                try:
                    archive_dir = config.ARCHIVE_DIR
                    destination_path = os.path.join(archive_dir, os.path.basename(job_folder_path))
                    
                    os.makedirs(archive_dir, exist_ok=True)
                    
                    # Prevent overwriting by making the destination path unique if it already exists
                    if os.path.exists(destination_path):
                        timestamp = datetime.now().strftime("_%Y%m%d%H%M%S")
                        destination_path += timestamp

                    shutil.move(job_folder_path, destination_path)
                    QMessageBox.information(self, "Folder Moved", 
                                          f"The job folder has been successfully moved to:\n{destination_path}")

                except Exception as e:
                    QMessageBox.warning(self, "Move Error", 
                                        f"Could not move the job folder. It will be archived without moving the files.\n\nError: {e}")
            else:
                 QMessageBox.information(self, "No Folder Found",
                                        "No job folder was found to move. The job data will be archived.")

            # Proceed with archiving the job data regardless of folder status
            self.job_data['dateArchived'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.job_archived.emit(self.job_data)
            self.accept()
            
    def delete_job(self):
        reply = QMessageBox.question(self, "Delete Job", "This action cannot be undone. Are you sure?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.job_deleted.emit()
            self.accept()

    def create_job_directory(self):
        # Re-using logic, assuming network path is the primary target
        try:
            customer = self.job_data.get("Customer")
            label_size = self.job_data.get("Label Size")
            current_date = datetime.now().strftime("%y-%m-%d")
            po_num = self.job_data.get("PO#")
            job_ticket = self.job_data.get("Job Ticket#")
            job_folder_name = f"{current_date} - {po_num} - {job_ticket}"
            
            customer_path = os.path.join(self.network_path, customer)
            label_size_path = os.path.join(customer_path, label_size)
            job_path = os.path.join(label_size_path, job_folder_name)
            
            if not os.path.exists(customer_path) or not os.path.exists(label_size_path):
                 QMessageBox.warning(self, "Missing Folders", "Customer or Label Size folder does not exist on the network drive.")
                 return

            os.makedirs(job_path, exist_ok=True)
            QMessageBox.information(self, "Success", f"Job folder created:\n{job_path}")
            self.check_directories()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create job folder: {e}")

    def regenerate_checklist(self):
        job_path = self.find_job_directory()
        if not job_path:
            QMessageBox.warning(self, "No Directory", "Cannot regenerate checklist without a job directory.")
            return
        
        template_path = os.path.join(self.base_path, "data", "Encoding Checklist V4.1.pdf")
        if not os.path.exists(template_path):
            QMessageBox.warning(self, "Missing Template", "Checklist template not found.")
            return

        try:
            # Re-use your existing checklist generation logic
            fields_to_fill = { "Customer": "customer", "Part#": "part_num", "Job Ticket#": "job_ticket", "PO#": "customer_po", "Inlay Type": "inlay_type", "Label Size": "label_size", "Quantity": "qty", "Item": "item", "UPC Number": "upc", "LPR": "lpr", "Rolls": "rolls", "Start":"start", "End":"end", "Date": "Date" }
            output_file_name = f"{self.job_data.get('Customer')}-{self.job_data.get('Job Ticket#')}-{self.job_data.get('PO#')}-Checklist.pdf"
            save_path = os.path.join(job_path, output_file_name)

            doc = fitz.open(template_path)
            for page in doc:
                for widget in page.widgets():
                    for data_key, pdf_key in fields_to_fill.items():
                        if widget.field_name == pdf_key:
                            value = datetime.now().strftime('%m/%d/%Y') if data_key == "Date" else self.job_data.get(data_key, "")
                            widget.field_value = str(value)
                            widget.update()
                            break
            doc.save(save_path, garbage=4, deflate=True)
            doc.close()
            QMessageBox.information(self, "Success", f"Checklist regenerated successfully.")
            self.refresh_files()
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Could not generate checklist:\n{e}")

    def get_stylesheet(self):
        return """
            QDialog {
                /* Let qt_material handle the base background */
            }
            QTabWidget#mainTabWidget::pane { 
                border: 1px solid #565656; 
                border-top: none;
            }
            QTabBar::tab { 
                background: #343a40; 
                border: 1px solid #565656; 
                border-bottom: none; 
                padding: 8px 20px; 
            }
            QTabBar::tab:selected { 
                background: #495057; 
            }
            QTabBar::tab:hover {
                background: #5a6268;
            }

            QGroupBox { 
                font-weight: bold; 
                margin-top: 10px; 
                border: 1px solid #565656;
                border-radius: 4px;
                padding: 10px;
            }
            
            QLabel#readOnlyField { 
                background-color: #495057; 
                border: 1px solid #6c757d; 
                border-radius: 4px; 
                padding: 5px; 
                min-height: 20px;
            }
            
            QWidget#headerWidget {
                background-color: #343a40;
                border-bottom: 2px solid #565656;
                padding: 10px;
            }
            QLabel#headerTitle { 
                font-size: 16px; 
                font-weight: bold; 
                color: #80c0ff; /* A nice blue for dark themes */
            }
            QLabel#headerStatus { 
                font-size: 12px; 
                /* Let qt_material set the default text color */
            }
            
            /* General button style is inherited from qt_material */
            QPushButton {
                padding: 8px 12px; 
                font-weight: bold;
                border-radius: 4px;
            }

            /* Specific button overrides for semantic meaning */
            QPushButton#deleteButton { 
                background-color: #dc3545; 
                color: white;
            }
            QPushButton#deleteButton:hover { background-color: #c82333; }
            
            QPushButton#saveButton { 
                background-color: #28a745; 
                color: white;
            }
            QPushButton#saveButton:hover { background-color: #218838; }
        """
