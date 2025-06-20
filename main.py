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
    QTableView,
    QMessageBox,
    QLineEdit,
    QFormLayout,
    QDialog,
    QDialogButtonBox,
    QComboBox,
)
import qdarktheme
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt, QSize, QDateTime
from datetime import datetime

import json, os

# It's good practice to create a class for your main window.
# This makes the code organized and allows us to manage state.

class NewJobDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.setWindowTitle("Create New Job")

        self.customer_name = QComboBox()
        self.inlay_type = QComboBox()
        self.label_size = QComboBox()
        self.customer_name.setInsertPolicy(QComboBox.InsertPolicy.InsertAtBottom)
        self.customer_name.setEditable(True)

        self.part_number = QLineEdit()
        self.job_ticket_number = QLineEdit()
        self.po_number = QLineEdit()
        
        self.qty = QLineEdit()

        self.get_lists()

        self.layout = QFormLayout(self)
        self.layout.addRow("Customer:", self.customer_name)
        self.layout.addRow("Part#:", self.part_number) 
        self.layout.addRow("Job Ticket#:", self.job_ticket_number)
        self.layout.addRow("PO#:", self.po_number)
        self.layout.addRow("Inlay Type:", self.inlay_type)
        self.layout.addRow("Label Size:", self.label_size)
        self.layout.addRow("Qty:", self.qty)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def accept(self):
        # This method now overrides the default behavior of the OK button.
        fields_to_check = {
            "Customer": self.customer_name.currentText(),
            "Part#": self.part_number.text(),
            "Job Ticket#": self.job_ticket_number.text(),
        }
        for field_name, value in fields_to_check.items():
            if not value.strip(): # Use strip() to ensure whitespace isn't considered valid
                QMessageBox.warning(self, "Validation Error", f"'{field_name}' is a required field.")
                return # Stop the process

        if not self.inlay_type.currentText().strip():
            QMessageBox.warning(self, "Validation Error", "Inlay Type is a required field.")
            return

        if not self.label_size.currentText().strip():
            QMessageBox.warning(self, "Validation Error", "Label Size is a required field.")
            return
        

        # If all checks pass, we call the original accept() method to close the dialog
        # and return a successful result.
        super().accept()
            

    def get_data(self):
        return {
            "Customer": self.customer_name.currentText(),
            "Part#": self.part_number.text(),
            "Job Ticket#": self.job_ticket_number.text(),
            "PO#": self.po_number.text(),
            "Inlay Type": self.inlay_type.currentText(),
            "Label Size": self.label_size.currentText(),
            "Qty": self.qty.text()
        }
    
    def _populate_combo_from_file(self, combo, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                items = [line.strip() for line in file if line.strip()]
                combo.clear()
                combo.addItem("")
                combo.addItems(items)
        except FileNotFoundError:
            print(f"File not found: {file_path}")
    
    def get_lists(self):
        try:
            # Try to load from the files in the current directory
            self._populate_combo_from_file(self.customer_name, os.path.join(self.base_path, "Customer_names.txt"))
            self._populate_combo_from_file(self.inlay_type, os.path.join(self.base_path, "Inlay_types.txt"))
            self._populate_combo_from_file(self.label_size, os.path.join(self.base_path, "Label_sizes.txt"))
            
            # Verify the combos were populated
            if self.customer_name.count() <= 1:  # Only has empty item
                print("Warning: Customer names combo box is empty")
            if self.inlay_type.count() <= 1:
                print("Warning: Inlay types combo box is empty")
            if self.label_size.count() <= 1:
                print("Warning: Label sizes combo box is empty")
                
        except Exception as e:
            print(f"Error loading combo box data: {e}")
            # Show error to user
            QMessageBox.warning(
                self,
                "Loading Error",
                f"There was an error loading the dropdown menus: {str(e)}\n"
                f"Base path used: {self.base_path}"
            )

    def set_data(self, data):
        """Fills the dialog's fields with data from an existing job."""
        self.customer_name.setCurrentText(data.get("Customer", ""))
        self.part_number.setText(data.get("Part#", ""))
        self.job_ticket_number.setText(data.get("Job Ticket#", ""))
        self.po_number.setText(data.get("PO#", ""))
        self.inlay_type.setCurrentText(data.get("Inlay Type", ""))
        self.label_size.setCurrentText(data.get("Label Size", ""))
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
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.network_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
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
        "Customer", "Part#", "Job Ticket#", "PO#",
         "Inlay Type", "Label Size", "Quantity", "Status"
        ])      
        self.model.setHorizontalHeaderLabels(self.headers)

        self.jobs_table = QTableView()

        from PySide6.QtWidgets import QHeaderView, QSizePolicy, QAbstractItemView
        from PySide6.QtCore import QAbstractItemModel

        self.jobs_table.setModel(self.model)
        self.jobs_table.setSizePolicy(QSizePolicy.Policy.Expanding,
    QSizePolicy.Policy.Expanding)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setSortingEnabled(True)
        
        self.jobs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.jobs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

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
        try:
            if not os.path.exists(self.network_path):
                QMessageBox.critical(self, "Error", f"Network path not accessible: {self.network_path}\nPlease make sure you have access to the Z: drive.")
                return

            current_date = datetime.now().strftime("%y-%m-%d")
            po_num = job_data.get("PO#", "UnknownPO")
            job_ticket_num = job_data.get("Job Ticket#", "UnknownJobTicket")
            customer = job_data.get("Customer", "UnknownCustomer")
            label_size = job_data.get("Label Size", "UnknownLabelSize")
            
            # Sanitize folder names to remove invalid characters
            customer = "".join(c for c in customer if c.isalnum() or c in " ._-")
            label_size = "".join(c for c in label_size if c.isalnum() or c in " ._-")        
            job_folder_name = f"{current_date}- PO{po_num} - {job_ticket_num}"

            # Check if customer and label size folders exist
            customer_path = os.path.join(self.network_path, customer)
            label_size_path = os.path.join(customer_path, label_size)
            
            if not os.path.exists(customer_path):
                QMessageBox.critical(self, "Error", f"Customer folder not found: {customer}\nPlease make sure the customer folder exists in the network drive.")
                return
                
            if not os.path.exists(label_size_path):
                QMessageBox.critical(self, "Error", f"Label size folder not found for customer {customer}: {label_size}\nPlease make sure the label size folder exists in the customer directory.")
                return
            
            # Create the job folder
            job_path = os.path.join(label_size_path, job_folder_name)
            if os.path.exists(job_path):
                QMessageBox.warning(self, "Warning", f"Job folder already exists:\n{job_path}")
                return
                
            os.makedirs(job_path)
            print(f"Successfully created job folder: {job_path}")
            QMessageBox.information(self, "Success", f"Job folder created at:\n{job_path}")
        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")


    def open_new_job_dialog(self):
        dialog = NewJobDialog(self)

        if dialog.exec():
            job_data = dialog.get_data()
            print("New Job Created:", job_data)
            self.add_job_to_table(job_data)
            print("job added to table")

            self._create_job_folders(job_data)
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
        except IOError as e:
            print(f"Error saving data: {e}")

# --- Standard boilerplate to run a PySide application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    qdarktheme.setup_theme("dark")


    window = MainWindow()
    window.show()
    sys.exit(app.exec())
