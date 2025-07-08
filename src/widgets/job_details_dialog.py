import os
import json
import subprocess
import platform
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QTextEdit, QComboBox, QListWidget,
    QTabWidget, QWidget, QMessageBox, QGridLayout, QLineEdit, QProgressDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
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
        layout = QHBoxLayout(self.overview_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Job Details Group
        job_details_group = QGroupBox("Job Information")
        form_layout = QFormLayout(job_details_group)
        job_field_keys = ["Customer", "Part#", "Job Ticket#", "PO#", "Inlay Type", "Label Size", "Quantity", "Due Date"]
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

        # Main horizontal layout for the two group boxes
        main_edit_layout = QHBoxLayout()

        # Left side: Job Details
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        # Job Details Group
        job_details_group = QGroupBox("Job Information")
        form_layout = QFormLayout(job_details_group)
        job_field_keys = ["Customer", "Part#", "Job Ticket#", "PO#", "Inlay Type", "Label Size", "Quantity", "Due Date"]
        for key in job_field_keys:
            field = QLineEdit(self.job_data.get(key, ''))
            form_layout.addRow(f"{key}:", field)
            self.job_fields_edit[key] = field
        left_layout.addWidget(job_details_group)
        left_layout.addStretch()

        # Right side: Encoding Details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)

        # Encoding Details Group
        encoding_details_group = QGroupBox("Encoding Information")
        encoding_form_layout = QFormLayout(encoding_details_group)
        encoding_field_keys = ["Item", "UPC Number", "Serial Number", "LPR", "Rolls"]
        for key in encoding_field_keys:
            field = QLineEdit(self.job_data.get(key, ''))
            encoding_form_layout.addRow(f"{key}:", field)
            self.encoding_fields_edit[key] = field
        right_layout.addWidget(encoding_details_group)
        right_layout.addStretch()

        main_edit_layout.addWidget(left_widget)
        main_edit_layout.addWidget(right_widget)
        layout.addLayout(main_edit_layout)

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
        
    def save_changes(self):
        updated_data = {}
        for key, field in self.job_fields_edit.items():
            updated_data[key] = field.text()
        for key, field in self.encoding_fields_edit.items():
            updated_data[key] = field.text()
        
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
        # Remove the edit tab when cancelling
        if hasattr(self, 'edit_tab'):
            edit_tab_index = self.tab_widget.indexOf(self.edit_tab)
            if edit_tab_index != -1:
                self.tab_widget.removeTab(edit_tab_index)
                self.edit_tab.deleteLater()
                del self.edit_tab
                
        self.tab_widget.setCurrentIndex(0)
    
    def complete_job(self):
        reply = QMessageBox.question(self, "Complete Job", "Are you sure you want to mark this job as completed?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.job_data['Status'] = 'Completed'
            self.job_updated.emit(self.job_data)
            self.load_job_data()
            QMessageBox.information(self, "Job Completed", "The job status has been set to 'Completed'.")

            # Ask to archive
            archive_reply = QMessageBox.question(self, "Archive Job", 
                                               "Would you like to archive this completed job now?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if archive_reply == QMessageBox.StandardButton.Yes:
                self.archive_job()

    def find_job_directory(self):
        # First, check if the path is already stored in job_data
        if 'job_folder_path' in self.job_data and os.path.exists(self.job_data['job_folder_path']):
            return self.job_data['job_folder_path']
            
        # If not, fall back to searching for it
        job_paths = self.find_job_directories()
        for path in job_paths.values():
            if path and os.path.exists(path):
                # Optional: Store the found path for future use
                self.job_data['job_folder_path'] = path
                self.job_updated.emit(self.job_data) # Let the main page know to save it
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
        # Enhanced version that considers all possible save locations from job data
        customer = self.job_data.get('Customer', '')
        label_size = self.job_data.get('Label Size', '')
        po_num = self.job_data.get('PO#', '')
        job_ticket = self.job_data.get('Job Ticket#', '')
        
        if not all([customer, label_size, po_num, job_ticket]):
            return {}
        
        # Build list of possible locations based on job data
        locations = {}
        
        # Always check network drive and desktop
        locations['shared_drive'] = self.network_path
        locations['desktop'] = os.path.expanduser("~/Desktop")
        
        # Also check custom path if it exists in job data
        if self.job_data.get('Custom Path'):
            locations['custom'] = self.job_data['Custom Path']
            
        found_paths = {}

        for loc, base_path in locations.items():
            try:
                customer_path = os.path.join(base_path, customer)
                label_path = os.path.join(customer_path, label_size)
                
                if os.path.exists(label_path):
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
                # Add files from main job directory
                for filename in os.listdir(job_path):
                    file_path = os.path.join(job_path, filename)
                    if os.path.isfile(file_path):
                        self.files_list.addItem(f"📄 {filename}")
                
                # Check for EPC structure and add database files from data folder
                data_folder = os.path.join(job_path, "data")
                if os.path.exists(data_folder) and os.path.isdir(data_folder):
                    self.files_list.addItem("📁 EPC Database Files:")
                    for filename in os.listdir(data_folder):
                        file_path = os.path.join(data_folder, filename)
                        if os.path.isfile(file_path):
                            self.files_list.addItem(f"  📊 {filename}")
                
                # Check for UPC structure and add files from UPC/data folder
                upc_number = self.job_data.get("UPC Number", "")
                if upc_number:
                    upc_folder = os.path.join(job_path, upc_number)
                    if os.path.exists(upc_folder) and os.path.isdir(upc_folder):
                        # Add EPC database files from UPC/data folder
                        upc_data_folder = os.path.join(upc_folder, "data")
                        if os.path.exists(upc_data_folder) and os.path.isdir(upc_data_folder):
                            self.files_list.addItem(f"📁 {upc_number}/data (EPC Database Files):")
                            for filename in os.listdir(upc_data_folder):
                                file_path = os.path.join(upc_data_folder, filename)
                                if os.path.isfile(file_path):
                                    self.files_list.addItem(f"  📊 {filename}")
                        
                        # Add template files from UPC/print folder
                        upc_print_folder = os.path.join(upc_folder, "print")
                        if os.path.exists(upc_print_folder) and os.path.isdir(upc_print_folder):
                            self.files_list.addItem(f"📁 {upc_number}/print (Templates):")
                            for filename in os.listdir(upc_print_folder):
                                file_path = os.path.join(upc_print_folder, filename)
                                if os.path.isfile(file_path):
                                    self.files_list.addItem(f"  🖨️ {filename}")
                
                # If no files found, show a message
                if self.files_list.count() == 0:
                    self.files_list.addItem("No files found in job directory")
                    
            except (OSError, PermissionError) as e:
                self.files_list.addItem(f"Error reading directory: {e}")

    def open_selected_file(self):
        item = self.files_list.currentItem()
        if not item: 
            return
        
        item_text = item.text()
        
        # Skip folder headers and indented section headers
        if item_text.startswith("📁") or ":" in item_text:
            return
        
        job_path = self.find_job_directory()
        if not job_path:
            return
        
        # Determine the actual file path based on the item text format
        if item_text.startswith("📄"):
            # Main directory file
            filename = item_text.replace("📄 ", "")
            file_path = os.path.join(job_path, filename)
        elif item_text.startswith("  📊"):
            # EPC database file - could be in data folder or UPC/data folder
            filename = item_text.replace("  📊 ", "")
            
            # Check if it's in main data folder first
            main_data_path = os.path.join(job_path, "data", filename)
            if os.path.exists(main_data_path):
                file_path = main_data_path
            else:
                # Check in UPC/data folder
                upc_number = self.job_data.get("UPC Number", "")
                if upc_number:
                    upc_data_path = os.path.join(job_path, upc_number, "data", filename)
                    if os.path.exists(upc_data_path):
                        file_path = upc_data_path
                    else:
                        QMessageBox.warning(self, "File Not Found", f"Could not locate file: {filename}")
                        return
                else:
                    QMessageBox.warning(self, "File Not Found", f"Could not locate file: {filename}")
                    return
        elif item_text.startswith("  🖨️"):
            # Template file in UPC/print folder
            filename = item_text.replace("  🖨️ ", "")
            upc_number = self.job_data.get("UPC Number", "")
            if upc_number:
                file_path = os.path.join(job_path, upc_number, "print", filename)
            else:
                QMessageBox.warning(self, "File Not Found", f"Could not locate template file: {filename}")
                return
        else:
            # Fallback to original behavior
            file_path = os.path.join(job_path, item_text)
        
        # Open the file
        if os.path.exists(file_path):
            if file_path.lower().endswith('.pdf'):
                self.open_pdf_in_browser(file_path)
            elif file_path.lower().endswith(('.xlsx', '.xls')):
                # Open Excel files with default application
                self.open_path_in_explorer(file_path)
            else:
                self.open_path_in_explorer(file_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"File does not exist: {file_path}")

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
            # The dialog's responsibility is to signal the request, not perform the move.
            # The main window orchestrates the move by telling the archive page.
            
            # Find the job folder path to ensure it's in the job_data payload.
            job_folder_path = self.find_job_directory()

            if not job_folder_path:
                 QMessageBox.information(self, "No Folder Found",
                                        "No job folder was found. The job data will be archived without moving any files.")
            else:
                # Make sure the path is in the data we are about to emit
                self.job_data['job_folder_path'] = job_folder_path

            # Proceed with archiving the job data.
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
        # Determine the base path from the job data
        if self.job_data.get('Shared Drive'):
            base_path = self.network_path
        elif self.job_data.get('Desktop'):
            base_path = os.path.expanduser("~/Desktop")
        elif self.job_data.get('Custom Path'):
            base_path = self.job_data['Custom Path']
        else:
            # Default or error
            QMessageBox.warning(self, "No Path", "No valid save location (Desktop, Shared Drive, or Custom) is set for this job.")
            return
            
        try:
            customer = self.job_data.get("Customer")
            label_size = self.job_data.get("Label Size")
            current_date = datetime.now().strftime("%y-%m-%d")
            po_num = self.job_data.get("PO#")
            job_ticket = self.job_data.get("Job Ticket#")
            job_folder_name = f"{current_date} - {po_num} - {job_ticket}"
            
            customer_path = os.path.join(base_path, customer)
            label_size_path = os.path.join(customer_path, label_size)
            job_path = os.path.join(label_size_path, job_folder_name)
            
            # Check if the parent directories exist before creating the final job folder
            if not os.path.exists(customer_path):
                os.makedirs(customer_path)
            if not os.path.exists(label_size_path):
                os.makedirs(label_size_path)

            os.makedirs(job_path, exist_ok=True)
            
            # Create print folder and copy template
            print_folder_path = os.path.join(job_path, "print")
            os.makedirs(print_folder_path, exist_ok=True)
            self.copy_template_to_job(customer, label_size, print_folder_path)
            
            QMessageBox.information(self, "Success", f"Job folder created:\n{job_path}")
            self.check_directories()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create job folder: {e}")

    def copy_template_to_job(self, customer, label_size, print_folder_path):
        """Copy .btw template file to the job's print folder."""
        try:
            import src.config as config
            import shutil
            from src.utils.epc_conversion import get_template_path_with_inlay
            
            template_base_path = config.get_template_base_path()
            
            if not template_base_path or not os.path.exists(template_base_path):
                print(f"Template base path not configured or doesn't exist: {template_base_path}")
                return
            
            # Get inlay type for better template matching
            inlay_type = self.job_data.get("Inlay Type", "")
            
            # Use enhanced template lookup with inlay type
            template_path = get_template_path_with_inlay(template_base_path, customer, label_size, inlay_type)
            
            if template_path and os.path.exists(template_path):
                # Determine destination filename priority: UPC > Job Ticket > PO Number
                upc = self.job_data.get("UPC Number", "")
                job_ticket = self.job_data.get("Job Ticket#", "")
                po_num = self.job_data.get("PO#", "")
                
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

class EPCGenerationWorker(QThread):
    """Worker thread for EPC database generation to prevent UI freezing."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    generation_complete = Signal(list)   # list of created files
    generation_failed = Signal(str)      # error message
    
    def __init__(self, upc, start_serial, total_qty, qty_per_db, save_location, job_data=None):
        super().__init__()
        self.upc = upc
        self.start_serial = start_serial
        self.total_qty = total_qty
        self.qty_per_db = qty_per_db
        self.save_location = save_location
        self.job_data = job_data
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the generation process."""
        self.is_cancelled = True
        
    def run(self):
        """Run the EPC generation in background thread."""
        try:
            from src.utils.epc_conversion import generate_epc_database_files_with_progress
            
            # Use the new progress-aware function
            created_files = generate_epc_database_files_with_progress(
                self.upc, 
                self.start_serial, 
                self.total_qty, 
                self.qty_per_db, 
                self.save_location,
                progress_callback=self.emit_progress,
                cancel_check=self.check_cancelled
            )
            
            if not self.is_cancelled:
                self.generation_complete.emit(created_files)
                
        except Exception as e:
            if not self.is_cancelled:
                self.generation_failed.emit(str(e))
    
    def emit_progress(self, percentage, message):
        """Emit progress update signal."""
        if not self.is_cancelled:
            self.progress_updated.emit(percentage, message)
    
    def check_cancelled(self):
        """Check if generation should be cancelled."""
        return self.is_cancelled


class EPCProgressDialog(QProgressDialog):
    """Progress dialog for EPC generation with cancellation support."""
    
    generation_finished = Signal(bool, object)  # success, result (files list or error message)
    
    def __init__(self, upc, start_serial, total_qty, qty_per_db, save_location, parent=None, job_data=None):
        super().__init__(parent)
        
        self.setWindowTitle("Generating EPC Database")
        self.setLabelText("Preparing EPC generation...")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setModal(True)
        self.setMinimumDuration(500)  # Show after 500ms
        self.setCancelButtonText("Cancel")
        
        # Create worker thread
        self.worker = EPCGenerationWorker(upc, start_serial, total_qty, qty_per_db, save_location, job_data)
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.generation_complete.connect(self.on_generation_complete)
        self.worker.generation_failed.connect(self.on_generation_failed)
        self.canceled.connect(self.on_cancelled)
        
        # Start generation
        self.worker.start()
    
    def update_progress(self, percentage, message):
        """Update progress bar and message."""
        self.setValue(percentage)
        self.setLabelText(message)
    
    def on_generation_complete(self, created_files):
        """Handle successful completion."""
        self.setValue(100)
        self.setLabelText(f"Complete! Generated {len(created_files)} database files.")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(True, created_files))
        QTimer.singleShot(1500, self.accept)
    
    def on_generation_failed(self, error_message):
        """Handle generation failure."""
        self.setLabelText(f"Generation failed: {error_message}")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(False, error_message))
        QTimer.singleShot(1500, self.reject)
    
    def on_cancelled(self):
        """Handle user cancellation."""
        self.setLabelText("Cancelling generation...")
        self.worker.cancel()
        self.worker.wait(3000)  # Wait up to 3 seconds for clean shutdown
        if self.worker.isRunning():
            self.worker.terminate()
        self.generation_finished.emit(False, "Generation cancelled by user")

class FileOperationWorker(QThread):
    """Worker thread for file operations to prevent UI freezing."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    operation_complete = Signal(bool, str)  # success, result message
    operation_failed = Signal(str)  # error message
    
    def __init__(self, operation_type, source_path, destination_path=None, job_data=None):
        super().__init__()
        self.operation_type = operation_type  # 'copy', 'move', 'delete'
        self.source_path = source_path
        self.destination_path = destination_path
        self.job_data = job_data
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the operation."""
        self.is_cancelled = True
        
    def run(self):
        """Run the file operation in background thread."""
        try:
            if self.operation_type == 'copy':
                self.copy_with_progress()
            elif self.operation_type == 'move':
                self.move_with_progress()
            elif self.operation_type == 'delete':
                self.delete_with_progress()
            else:
                self.operation_failed.emit(f"Unknown operation type: {self.operation_type}")
                
        except Exception as e:
            if not self.is_cancelled:
                self.operation_failed.emit(str(e))
    
    def copy_with_progress(self):
        """Copy folder with progress updates."""
        import os
        import shutil
        
        if not os.path.exists(self.source_path):
            self.operation_failed.emit(f"Source path does not exist: {self.source_path}")
            return
            
        # Count total files for progress calculation
        total_files = 0
        for root, dirs, files in os.walk(self.source_path):
            total_files += len(files)
            if self.is_cancelled:
                return
        
        if total_files == 0:
            total_files = 1  # Avoid division by zero
            
        self.progress_updated.emit(0, f"Starting copy operation...")
        
        copied_files = 0
        
        def copy_function(src, dst, *, follow_symlinks=True):
            nonlocal copied_files
            if self.is_cancelled:
                raise InterruptedError("Operation cancelled")
                
            result = shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
            copied_files += 1
            
            progress = int((copied_files / total_files) * 100)
            filename = os.path.basename(src)
            self.progress_updated.emit(progress, f"Copying: {filename} ({copied_files}/{total_files})")
            
            return result
        
        try:
            shutil.copytree(self.source_path, self.destination_path, copy_function=copy_function)
            if not self.is_cancelled:
                self.operation_complete.emit(True, f"Successfully copied {copied_files} files")
        except InterruptedError:
            self.operation_failed.emit("Copy operation cancelled")
        except Exception as e:
            self.operation_failed.emit(f"Copy failed: {str(e)}")
    
    def move_with_progress(self):
        """Move folder with progress updates."""
        import os
        import shutil
        
        self.progress_updated.emit(0, "Starting move operation...")
        
        try:
            # For move operations, we can use a simple progress indicator
            self.progress_updated.emit(25, "Preparing move...")
            
            if self.is_cancelled:
                return
                
            self.progress_updated.emit(50, "Moving folder...")
            shutil.move(self.source_path, self.destination_path)
            
            if not self.is_cancelled:
                self.progress_updated.emit(100, "Move completed successfully")
                self.operation_complete.emit(True, f"Successfully moved to {self.destination_path}")
                
        except Exception as e:
            self.operation_failed.emit(f"Move failed: {str(e)}")
    
    def delete_with_progress(self):
        """Delete folder with progress updates."""
        import os
        import shutil
        
        if not os.path.exists(self.source_path):
            self.operation_complete.emit(True, "Path already deleted")
            return
            
        # Count files for progress
        total_items = 0
        for root, dirs, files in os.walk(self.source_path):
            total_items += len(files) + len(dirs)
            if self.is_cancelled:
                return
        
        self.progress_updated.emit(0, f"Deleting {total_items} items...")
        
        try:
            if self.is_cancelled:
                return
                
            self.progress_updated.emit(50, "Removing folder structure...")
            
            # Try normal deletion first
            try:
                shutil.rmtree(self.source_path)
                success = True
            except Exception:
                # Try forceful deletion on Windows
                success = False
                if os.name == "nt":
                    import subprocess
                    self.progress_updated.emit(75, "Using forceful deletion...")
                    
                    result = subprocess.run(
                        ["cmd", "/c", "rmdir", "/S", "/Q", self.source_path],
                        capture_output=True, text=True, shell=False
                    )
                    
                    if not os.path.exists(self.source_path):
                        success = True
                
            if success and not self.is_cancelled:
                self.progress_updated.emit(100, "Deletion completed")
                self.operation_complete.emit(True, "Successfully deleted folder")
            elif not success:
                self.operation_failed.emit("Could not delete folder completely")
                
        except Exception as e:
            self.operation_failed.emit(f"Delete failed: {str(e)}")


class FileOperationProgressDialog(QProgressDialog):
    """Progress dialog for file operations with cancellation support."""
    
    operation_finished = Signal(bool, str)  # success, message
    
    def __init__(self, operation_type, source_path, destination_path=None, job_data=None, parent=None):
        super().__init__(parent)
        
        operation_names = {
            'copy': 'Copying Files',
            'move': 'Moving Files', 
            'delete': 'Deleting Files'
        }
        
        self.setWindowTitle(operation_names.get(operation_type, 'File Operation'))
        self.setLabelText("Preparing operation...")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setModal(True)
        self.setMinimumDuration(500)
        self.setCancelButtonText("Cancel")
        
        # Create worker thread
        self.worker = FileOperationWorker(operation_type, source_path, destination_path, job_data)
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.operation_complete.connect(self.on_operation_complete)
        self.worker.operation_failed.connect(self.on_operation_failed)
        self.canceled.connect(self.on_cancelled)
        
        # Start operation
        self.worker.start()
    
    def update_progress(self, percentage, message):
        """Update progress bar and message."""
        self.setValue(percentage)
        self.setLabelText(message)
    
    def on_operation_complete(self, success, message):
        """Handle successful completion."""
        self.setValue(100)
        self.setLabelText("Operation completed successfully")
        QTimer.singleShot(1000, lambda: self.operation_finished.emit(True, message))
        QTimer.singleShot(1500, self.accept)
    
    def on_operation_failed(self, error_message):
        """Handle operation failure."""
        self.setLabelText(f"Operation failed: {error_message}")
        QTimer.singleShot(1000, lambda: self.operation_finished.emit(False, error_message))
        QTimer.singleShot(1500, self.reject)
    
    def on_cancelled(self):
        """Handle user cancellation."""
        self.setLabelText("Cancelling operation...")
        self.worker.cancel()
        self.worker.wait(3000)
        if self.worker.isRunning():
            self.worker.terminate()
        self.operation_finished.emit(False, "Operation cancelled by user")

class PDFGenerationWorker(QThread):
    """Worker thread for PDF generation to prevent UI freezing."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    generation_complete = Signal(str)    # output file path
    generation_failed = Signal(str)      # error message
    
    def __init__(self, template_path, job_data, output_path):
        super().__init__()
        self.template_path = template_path
        self.job_data = job_data
        self.output_path = output_path
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the PDF generation."""
        self.is_cancelled = True
        
    def run(self):
        """Run PDF generation in background thread."""
        try:
            import fitz
            from datetime import datetime
            
            self.progress_updated.emit(0, "Opening PDF template...")
            
            # Debug: Log serial range information available for PDF generation
            start_value = self.job_data.get("Start", "NOT_SET")
            end_value = self.job_data.get("End", "NOT_SET")
            print(f"=== PDF Generation Debug ===")
            print(f"Available Start value: {start_value}")
            print(f"Available End value: {end_value}")
            print(f"Job data keys: {list(self.job_data.keys())}")
            
            if self.is_cancelled:
                return
                
            # Define field mappings
            fields_to_fill = {
                "Customer": "customer",
                "Part#": "part_num",
                "Ticket#": "job_ticket",
                "PO#": "customer_po",
                "Inlay Type": "inlay_type",
                "Label Size": "label_size",
                "Qty": "qty",
                "Item": "item",
                "UPC Number": "upc",
                "LPR": "lpr",
                "Rolls": "rolls",
                "Start": "start",
                "End": "end",
                "Date": "Date",
            }
            
            self.progress_updated.emit(20, "Loading PDF document...")
            doc = fitz.open(self.template_path)
            
            if self.is_cancelled:
                doc.close()
                return
            
            total_fields = len(fields_to_fill)
            filled_fields = 0
            
            self.progress_updated.emit(40, "Processing form fields...")
            
            for page in doc:
                if self.is_cancelled:
                    break
                    
                for widget in page.widgets():
                    if self.is_cancelled:
                        break
                        
                    for data_key, pdf_key in fields_to_fill.items():
                        if widget.field_name == pdf_key:
                            value = ""
                            if data_key == "Date":
                                value = datetime.now().strftime("%m/%d/%Y")
                            elif data_key == "Ticket#":
                                value = self.job_data.get("Job Ticket#", self.job_data.get("Ticket#", ""))
                            elif data_key == "Qty":
                                qty_value = self.job_data.get("Quantity", self.job_data.get("Qty", ""))
                                # Format quantity with commas for display in PDF
                                if qty_value and str(qty_value).replace(',', '').isdigit():
                                    clean_qty = str(qty_value).replace(',', '')
                                    value = f"{int(clean_qty):,}"
                                else:
                                    value = str(qty_value) if qty_value else ""
                            elif data_key == "UPC Number":
                                upc_value = self.job_data.get(data_key, "")
                                # Format UPC with spaces for display in PDF
                                if (
                                    upc_value
                                    and len(upc_value) == 12
                                    and upc_value.isdigit()
                                ):
                                    value = f"{upc_value[:3]} {upc_value[3:6]} {upc_value[6:9]} {upc_value[9:12]}"
                                else:
                                    value = upc_value
                            elif data_key == "Start":
                                # Format start serial number with commas
                                start_value = self.job_data.get("Start", "")
                                if start_value and str(start_value).replace(',', '').isdigit():
                                    clean_start = str(start_value).replace(',', '')
                                    value = f"{int(clean_start):,}"
                                    print(f"PDF: Set Start field to {value}")
                                else:
                                    value = str(start_value) if start_value else ""
                                    print(f"PDF: Start field fallback value: {value}")
                            elif data_key == "End":
                                # Format end serial number with commas
                                end_value = self.job_data.get("End", "")
                                if end_value and str(end_value).replace(',', '').isdigit():
                                    clean_end = str(end_value).replace(',', '')
                                    value = f"{int(clean_end):,}"
                                    print(f"PDF: Set End field to {value}")
                                else:
                                    value = str(end_value) if end_value else ""
                                    print(f"PDF: End field fallback value: {value}")
                            else:
                                value = self.job_data.get(data_key, "")

                            widget.field_value = str(value)
                            widget.update()
                            
                            filled_fields += 1
                            progress = 40 + int((filled_fields / total_fields) * 40)
                            self.progress_updated.emit(progress, f"Filled field: {data_key}")
                            break
            
            if not self.is_cancelled:
                self.progress_updated.emit(90, "Saving PDF document...")
                doc.save(self.output_path, garbage=4, deflate=True)
                doc.close()
                
                self.progress_updated.emit(100, "PDF generation completed")
                self.generation_complete.emit(self.output_path)
            else:
                doc.close()
                
        except Exception as e:
            self.generation_failed.emit(str(e))


class PDFProgressDialog(QProgressDialog):
    """Progress dialog for PDF generation with cancellation support."""
    
    generation_finished = Signal(bool, str)  # success, result (file path or error message)
    
    def __init__(self, template_path, job_data, output_path, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Generating PDF Checklist")
        self.setLabelText("Preparing PDF generation...")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setModal(True)
        self.setMinimumDuration(500)
        self.setCancelButtonText("Cancel")
        
        # Create worker thread
        self.worker = PDFGenerationWorker(template_path, job_data, output_path)
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.generation_complete.connect(self.on_generation_complete)
        self.worker.generation_failed.connect(self.on_generation_failed)
        self.canceled.connect(self.on_cancelled)
        
        # Start generation
        self.worker.start()
    
    def update_progress(self, percentage, message):
        """Update progress bar and message."""
        self.setValue(percentage)
        self.setLabelText(message)
    
    def on_generation_complete(self, output_path):
        """Handle successful completion."""
        self.setValue(100)
        self.setLabelText("PDF generation completed successfully")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(True, output_path))
        QTimer.singleShot(1500, self.accept)
    
    def on_generation_failed(self, error_message):
        """Handle generation failure."""
        self.setLabelText(f"PDF generation failed: {error_message}")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(False, error_message))
        QTimer.singleShot(1500, self.reject)
    
    def on_cancelled(self):
        """Handle user cancellation."""
        self.setLabelText("Cancelling PDF generation...")
        self.worker.cancel()
        self.worker.wait(3000)
        if self.worker.isRunning():
            self.worker.terminate()
        self.generation_finished.emit(False, "PDF generation cancelled by user")
