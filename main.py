import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QLabel,
    QListWidgetItem,
    QVBoxLayout,
    QPushButton,
    QTableWidget,
    QTableView,
    QMessageBox,
    QLineEdit,
    QFormLayout,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
)
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt, QSize, QDateTime
from datetime import datetime

import json, os

# It's good practice to create a class for your main window.
# This makes the code organized and allows us to manage state.

class NewJobDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create New Job")
        self.customer_name = QLineEdit()
        self.part_number = QLineEdit()
        self.job_ticket_number = QLineEdit()
        self.po_number = QLineEdit()
        self.inlay_type = QLineEdit()
        self.label_size = QLineEdit()
        self.qty = QLineEdit()

        self.layout = QFormLayout(self)

        self.layout.addRow("Customer:", self.customer_name)
        self.layout.addRow("Part#:", self.part_number) 
        self.layout.addRow("Job Ticket#:", self.job_ticket_number)
        self.layout.addRow("PO#:", self.po_number)
        self.layout.addRow("Inlay Type:", self.inlay_type)
        self.layout.addRow("Label Size:", self.label_size)
        self.layout.addRow("Qty:", self.qty)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def validate_and_accept(self):

        self._create_job_folders(self.get_data())
        
        # Validate all required fields
        fields = {
            "Customer name": self.customer_name.text(),
            "Part number": self.part_number.text(), 
            "Job ticket number": self.job_ticket_number.text(),
            "PO number": self.po_number.text(),
            "Inlay type": self.inlay_type.text(),
            "Label size": self.label_size.text(),
            "Quantity": self.qty.text()
        }
        # Check for empty fields
        for field_name, value in fields.items():
            if not value:
                QMessageBox.warning(self, "Validation Error", f"{field_name} is required")
                return
                
        # Validate numeric fields
        numeric_fields = {
            "PO number": self.po_number.text(),
            "Label size": self.label_size.text(), 
            "Quantity": self.qty.text(),
            "Inlay type": self.inlay_type.text()
        }
        
        for field_name, value in numeric_fields.items():
            if not value.isdigit() or int(value) <= 0:
                QMessageBox.warning(self, "Validation Error", f"{field_name} must be a positive number")
                return
                
        print("Validation passed")
        self.accept()
            

    def get_data(self):
        return {
            "Customer": self.customer_name.text(),
            "Part#": self.part_number.text(),
            "Job Ticket#": self.job_ticket_number.text(),
            "PO#": self.po_number.text(),
            "Inlay Type": self.inlay_type.text(),
            "Label Size": self.label_size.text(),
            "Qty": self.qty.text()
        }
    
    def set_data(self, data):
        """Fills the dialog's fields with data from an existing job."""
        self.customer_name.setText(data.get("Customer", ""))
        self.part_number.setText(data.get("Part#", ""))
        self.job_ticket_number.setText(data.get("Job Ticket#", ""))
        self.po_number.setText(data.get("PO#", ""))
        self.inlay_type.setText(data.get("Inlay Type", ""))
        self.label_size.setText(data.get("Label Size", ""))
        self.qty.setText(data.get("Qty", ""))

    
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Workflow Optimizer")
        self.setGeometry(100, 100, 900, 600) # x, y, width, height

        # --- Create the main layout ---
        # A horizontal layout will hold our navigation bar and the content area.
        main_layout = QHBoxLayout()

        # --- Create the Navigation List ---
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(150) # Set a fixed width for the navigation
        main_layout.addWidget(self.nav_list)

        # --- Create the Content Stack ---
        # The QStackedWidget allows us to have multiple "pages" (widgets)
        # and switch between them.
        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)

        # Set the main layout's stretch factor. This tells the content area (page_stack)
        # to expand and fill available space, while the nav_list stays at its fixed width.
        main_layout.setStretchFactor(self.nav_list, 0)
        main_layout.setStretchFactor(self.page_stack, 1)

        self.jobs_page = JobPageWidget()

        # --- Add pages and navigation items ---
        # We'll create a simple function to keep our code clean (DRY principle).
        self.add_page("Dashboard", QLabel("This is the Dashboard Page.\n\nSummary info will go here."))
        self.add_page("QuickTools", QLabel("This is the QuickTools Page.\n\nWidgets for small, one-off tasks go here."))
        self.add_page("Jobs", self.jobs_page)
        self.add_page("Reports", QLabel("This is the Reports Page.\n\nCharts and data exports will live here."))
        self.add_page("Settings", QLabel("This is the Settings Page.\n\nApplication settings will be configured here."))
        self.add_page("Archive", QLabel("This is the Archive Page.\n\nAll archived jobs will be displayed here."))
        # --- Create the toolbar ---    

        # --- Connect the navigation list to the stacked widget ---
        # This is the core logic: when the selected item in the list changes,
        # it calls our `switch_page` method. This is a "signal and slot" connection.
        self.nav_list.currentItemChanged.connect(self.switch_page)

        # --- Finalize the layout ---
        # We need a central widget to hold our main_layout.
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Select the first item by default
        self.nav_list.setCurrentRow(0)

    def closeEvent(self, event):
        print("Closing application")
        self.jobs_page.save_data()
        event.accept()

    def add_page(self, title, widget):
        """A helper function to add a page to the stack and a corresponding nav item."""
        self.page_stack.addWidget(widget)
        
        # Create a QListWidgetItem and add it to the nav_list
        item = QListWidgetItem(title)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter) # Center the text
        item.setSizeHint(QSize(0, 35)) # Give it a bit more height
        self.nav_list.addItem(item)
        
    def switch_page(self, current_item):
        """Slot function to switch the visible page in the QStackedWidget."""
        # QListWidget.row(item) gives us the index of the item.
        # This index directly corresponds to the index of the page in the QStackedWidget.
        index = self.nav_list.row(current_item)
        self.page_stack.setCurrentIndex(index)


class JobPageWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.save_file = "jobs.json"
        layout = QVBoxLayout(self)


        actions_layout = QHBoxLayout()
        self.add_job_button = QPushButton("Add Job")
        self.add_job_button.clicked.connect(self.open_new_job_dialog)


        self.edit_job_button = QPushButton("Edit Selected Job")
        self.edit_job_button.clicked.connect(self.edit_selected_job)

        self.delete_job_button = QPushButton("Delete Selected Job")
        self.delete_job_button.clicked.connect(self.delete_selected_job)

        actions_layout.addWidget(self.add_job_button)
        actions_layout.addWidget(self.edit_job_button)
        actions_layout.addWidget(self.delete_job_button)
        layout.addLayout(actions_layout)


        self.model = QStandardItemModel()
        self.headers = ([
        "Customer", "Part#", "Job Ticket#", "PO#", "Inlay Type", "Label Size", "Quantity", "Status"
        ])      
        self.model.setHorizontalHeaderLabels(self.headers)

        self.jobs_table = QTableView()
        self.jobs_table.setModel(self.model)

        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setSortingEnabled(True)
        
        from PySide6.QtWidgets import QHeaderView, QSizePolicy

        self.jobs_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        header = self.jobs_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Rule 2: The "Customer" column should expand to fill empty space
        header.setSectionResizeMode(self.headers.index("Customer"), QHeaderView.ResizeMode.Stretch)
        
        # Rule 3: These specific columns should be narrow and fit their content
        header.setSectionResizeMode(self.headers.index("Part#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("PO#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Quantity"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Status"), QHeaderView.ResizeMode.ResizeToContents)
       
        layout.addWidget(self.jobs_table)
        self.setLayout(layout)



        self.jobs_table.selectionModel().selectionChanged.connect(self.update_button_states)
        self.update_button_states()
        self.load_jobs()


    def update_button_states(self):
        has_selection = bool(self.jobs_table.selectionModel().selectedRows())
        self.edit_job_button.setEnabled(has_selection)
        self.delete_job_button.setEnabled(has_selection)


    def edit_selected_job(self):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
        selected_row_index = selection_model.selectedRows()[0]
        
        #1. get the job data from the table
        current_data = {}
        for col, header in enumerate(self.headers):
            cell_index = self.model.index(selected_row_index.row(), col)
            current_data[header] = self.model.data(cell_index, Qt.DisplayRole)

        #2. open the dialog with the current data
        dialog = NewJobDialog(self)
        dialog.set_data(current_data)

        if dialog.exec():
            new_data = dialog.get_data()
            for col, header in enumerate(self.headers):
                if header in new_data:
                    cell_index = self.model.index(selected_row_index.row(), col)
                    self.model.setData(cell_index, new_data[header], Qt.EditRole)

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
            self.save_data()
        
        self.save_data()


    def _create_job_folders(self, job_data):
       
       
        # Get the current date in the required format

        try:
            current_date = datetime.now().strftime("%y-%m-%d")
            
            po_num = job_data.get("PO#", "UnknownPO")
            job_ticket_num = job_data.get("Job Ticket#", "UnknownJobTicket")
            inlay_type = job_data.get("Inlay Type", "UnknownInlayType")
            label_size = job_data.get("Label Size", "UnknownLabelSize")
            customer = job_data.get("Customer", "UnknownCustomer")
            
            # Create the job folder name in the required format
            job_folder_name = f"{current_date}- PO{po_num} - {job_ticket_num}"
            
            # Create the full path:
            # customer_name/label_size/job_folder
            base_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
            customer = job_data.get("Customer", "UnknownCustomer")
            label_size = job_data.get("Label Size", "UnknownLabelSize")

            customer = "".join(c for c in customer if c.isalnum() or c in "._-")
            label_size = "".join(c for c in label_size if c.isalnum() or c in "._-")
            job_path = os.path.join(base_path, customer, label_size, job_folder_name)
            
            # Create the directory
            os.makedirs(job_path, exist_ok=True)
            print(f"Created job folder: {job_path}")

            QMessageBox.information(self, "Job Folder Created", f"Job folder created at: {job_path}")
        except Exception as e:
                print(f"Error creating job folder: {e}")
                QMessageBox.critical(self, "Error", f"Error creating job folder: {e}")







    def open_new_job_dialog(self):
        dialog = NewJobDialog(self)

        if dialog.exec():
            job_data = dialog.get_data()
            print("New Job Created:", job_data)
            self.add_job_to_table(job_data)
        else:
            print("Job creation cancelled")

    def add_job_to_table(self, job_data, status="New"):
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Job Ticket#", "")),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(job_data.get("Qty", "")),
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
                print("Loaded jobs:", data)
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
                print(f"Successfully saved {len(data_to_save)} jobs to {self.save_file}")
        except IOError as e:
            print(f"Error saving data: {e}")

# --- Standard boilerplate to run a PySide application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
