import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QCheckBox, QPushButton, QLabel, QFileDialog, QSizePolicy, QWidget, QMessageBox, QHBoxLayout
)
from PySide6.QtCore import Qt
from qt_material import apply_stylesheet

class NewJobWizard(QWizard):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.base_path = base_path if base_path else os.path.dirname(os.path.abspath(__file__))
        self.setWindowTitle("New Job Wizard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(500, 400)

        self.job_data = {}

        self.addPage(JobDetailsPage(base_path=self.base_path))
        self.addPage(EncodingPage(base_path=self.base_path))
        self.addPage(SaveLocationPage(base_path=self.base_path))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
    
    def accept(self):

        print("Wizard accepted")
        super().accept()

    def get_data(self):
        all_data = {}
        for page_id in range(self.pageIds().__len__()):
            page = self.page(self.pageIds()[page_id])
            if hasattr(page, 'get_data'):
                all_data.update(page.get_data())
        return all_data

    def set_all_data(self, data):
        for page_id in range(self.pageIds().__len__()):
            page = self.page(self.pageIds()[page_id])
            if hasattr(page, 'set_data'):
                page.set_data(data)

    def get_save_locations(self):
        # The save location page is the 3rd page, index 2
        save_page = self.page(self.pageIds()[2])
        save_data = save_page.get_data()
        
        locations = []
        if save_data.get("Shared Drive"):
            # Use raw string for windows paths
            locations.append(r"Z:\3 Encoding and Printing Files\Customers Encoding Files")
        if save_data.get("Desktop"):
            locations.append(os.path.expanduser("~/Desktop"))
        
        # Add custom path only if it exists
        if save_data.get("Custom Path"):
            locations.append(save_data.get("Custom Path"))
            
        return locations
    

class JobDetailsPage(QWizardPage):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.base_path = base_path
        self.setTitle("Step 1: Ticket Details")
        self.setSubTitle("Enter details of job ticket, customer, part number, qty etc.")
        

        # Create a vertical layout for the dialog
        self.customer_name = QComboBox()
        self.inlay_type = QComboBox()
        self.label_size = QComboBox()

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
    
        #
        #self.layout.addRow("Save Location:", save_location_widget)
        #self.layout.addRow("", self.custom_path_label)  # Add the path labe


    def get_lists(self):
        try:
            self._populate_combo_from_file(self.customer_name, os.path.join(self.base_path, "data", "Customer_names.txt"))
            self._populate_combo_from_file(self.inlay_type, os.path.join(self.base_path, "data", "Inlay_types.txt"))
            self._populate_combo_from_file(self.label_size, os.path.join(self.base_path, "data", "Label_sizes.txt"))
        except Exception as e:
            print(f"Error getting lists: {e}")
            QMessageBox.warning(
                self,
                "Loading Error",
                f"There was an error loading the lists: {e}\n"
                f"Base path used: {self.base_path}"
            )


    def set_data(self, data):
        self.job_data = data
        self.customer_name.setCurrentText(data.get("Customer", ""))
        self.part_number.setText(data.get("Part#", ""))
        self.job_ticket_number.setText(data.get("Job Ticket#", ""))
        self.po_number.setText(data.get("PO#", ""))
        self.inlay_type.setCurrentText(data.get("Inlay Type", ""))
        self.label_size.setCurrentText(data.get("Label Size", ""))
        print(f"Data set: {data}")

    def _populate_combo_from_file(self, combo, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                items = [line.strip() for line in file if line.strip()]
                combo.clear()
                combo.addItem("")
                combo.addItems(items)
        except FileNotFoundError:
            print(f"File not found: {file_path}")

    def get_data(self):
        return {
            "Customer": self.customer_name.currentText(),
            "Part#": self.part_number.text(),
            "Job Ticket#": self.job_ticket_number.text(),
            "PO#": self.po_number.text(),
            "Inlay Type": self.inlay_type.currentText(),
            "Label Size": self.label_size.currentText()
        }
    

class EncodingPage(QWizardPage):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.setTitle("Step 2: Encoding Information")
        self.setSubTitle("Enter encoding information for the job, UPC, Serial Number, etc.")

        self.upc_number = QLineEdit()
        self.serial_number = QLineEdit()
        self.item = QLineEdit()
        self.qty = QLineEdit()
        self.lpr = QLineEdit()
        
        # Add read-only field for calculated rolls
        self.rolls_display = QLineEdit()
        self.rolls_display.setReadOnly(True)
        self.rolls_display.setStyleSheet("background-color: #f0f0f0; color: #666;")
        self.rolls_display.setPlaceholderText("Calculated automatically")

        # Connect qty and lpr fields to trigger calculation
        self.qty.textChanged.connect(self.calculate_rolls)
        self.lpr.textChanged.connect(self.calculate_rolls)

        self.layout = QFormLayout(self)
        self.layout.addRow("Item:", self.item)
        self.layout.addRow("Qty:", self.qty)
        self.layout.addRow("UPC Number:", self.upc_number) 
        self.layout.addRow("Serial Number:", self.serial_number)
        self.layout.addRow("LPR:", self.lpr)
        self.layout.addRow("Rolls:", self.rolls_display)

    def calculate_rolls(self):
        """Calculate and display the number of rolls based on qty and lpr."""
        try:
            qty_text = self.qty.text().strip()
            lpr_text = self.lpr.text().strip()
            
            if qty_text and lpr_text:
                qty = int(qty_text)
                lpr = int(lpr_text)
                if lpr > 0:  # Avoid division by zero
                    rolls = qty // lpr
                    remainder = qty % lpr
                    if remainder > 0:
                        self.rolls_display.setText(f"{rolls} (+ {remainder} labels)")
                    else:
                        self.rolls_display.setText(str(rolls))
                else:
                    self.rolls_display.setText("LPR must be > 0")
            else:
                self.rolls_display.setText("")
        except ValueError:
            # Invalid input, clear the rolls display
            self.rolls_display.setText("Invalid input")

    def set_data(self, data):
        self.item.setText(data.get("Item", ""))
        self.qty.setText(data.get("Quantity", ""))
        self.lpr.setText(data.get("LPR", ""))
        self.upc_number.setText(data.get("UPC Number", ""))
        self.serial_number.setText(data.get("Serial Number", ""))
        # Trigger calculation after setting data
        self.calculate_rolls()

    def get_data(self):
        # Calculate rolls for return data
        calculated_rolls = 0
        try:
            qty_text = self.qty.text().strip()
            lpr_text = self.lpr.text().strip()
            if qty_text and lpr_text:
                qty = int(qty_text)
                lpr = int(lpr_text)
                if lpr > 0:
                    calculated_rolls = qty // lpr
        except ValueError:
            calculated_rolls = 0

        return {
            "Serial Number": self.serial_number.text(),
            "UPC Number": self.upc_number.text(),
            "Item": self.item.text(),
            "Quantity": self.qty.text(),
            "LPR": self.lpr.text(),
            "Rolls": str(calculated_rolls)
        }

class SaveLocationPage(QWizardPage):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.setTitle("Step 3: Save Location")
        self.setSubTitle("Select the location to save the job")

        self.custom_save_location = None

        self.SharedDrive_location = QCheckBox("Auto search/save")
        self.Desktop_location = QCheckBox("Desktop")
        self.Browse_Button = QPushButton("Browse")

        # Add a label to show selected custom path
        self.custom_path_label = QLabel("No custom path selected")
        self.custom_path_label.setWordWrap(True)
        self.custom_path_label.setStyleSheet("color: gray; font-size: 10px;")

        self.SharedDrive_location.stateChanged.connect(self.update_browse_button_state)
        self.Desktop_location.stateChanged.connect(self.update_browse_button_state)

        # Connect browse button to directory selection
        self.Browse_Button.clicked.connect(self.browse_for_directory)

        self.layout = QFormLayout(self)
        save_location_layout = QHBoxLayout()
        save_location_layout.addWidget(self.SharedDrive_location)
        save_location_layout.addWidget(self.Desktop_location)
        save_location_layout.addWidget(self.Browse_Button)
        save_location_layout.addStretch()  # Pushes controls to the left

        save_location_widget = QWidget()
        save_location_widget.setLayout(save_location_layout)
        self.layout.addRow("Save Location:", save_location_widget)
        self.layout.addRow("", self.custom_path_label)

        self.update_browse_button_state()


    def browse_for_directory(self):
        """Open directory selection dialog and store the selected path."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Save Directory", 
            "", 
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:  # User selected a directory (didn't cancel)
            self.custom_save_location = directory
            self.custom_path_label.setText(f"Custom path: {directory}")
            self.custom_path_label.setStyleSheet("color: black; font-size: 10px;")
        else:
            # User cancelled, keep existing selection if any
            if not self.custom_save_location:
                self.custom_path_label.setText("No custom path selected")
                self.custom_path_label.setStyleSheet("color: gray; font-size: 10px;")
        return directory

    def update_browse_button_state(self):
        """Enable/disable browse button based on checkbox states."""
        if self.SharedDrive_location.isChecked() or self.Desktop_location.isChecked():
            self.Browse_Button.setEnabled(False)
            self.Browse_Button.setStyleSheet("background-color: #f0f0f0; color: #000000;")
        else:
            self.Browse_Button.setEnabled(True)
            self.Browse_Button.setStyleSheet("")  # Reset to default style

    def get_data(self):
        return {
            "Shared Drive": self.SharedDrive_location.isChecked(),
            "Desktop": self.Desktop_location.isChecked(),
            "Custom Path": self.custom_save_location
        }
        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = NewJobWizard()
    wizard.exec()

    sys.exit(app.exec())