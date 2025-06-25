import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QCheckBox, QPushButton, QLabel, QFileDialog, QSizePolicy, QWidget, QMessageBox
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
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)



        


    
    def accept(self):

        print("Wizard accepted")
        super().accept()




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
    
        #self.layout.addRow("Qty:", self.qty)
        #self.layout.addRow("Save Location:", save_location_widget)
        #self.layout.addRow("", self.custom_path_label)  # Add the path labe


    def get_lists(self):
        try:
            # Go up two levels from src/wizards/ to reach project root where data/ is located
            project_root = os.path.dirname(os.path.dirname(self.base_path))
            self._populate_combo_from_file(self.customer_name, os.path.join(project_root, "data", "Customer_names.txt"))
            self._populate_combo_from_file(self.inlay_type, os.path.join(project_root, "data", "Inlay_types.txt"))
            self._populate_combo_from_file(self.label_size, os.path.join(project_root, "data", "Label_sizes.txt"))
        except Exception as e:
            print(f"Error getting lists: {e}")
            QMessageBox.warning(
                self,
                "Loading Error",
                f"There was an error loading the lists: {e}\n"
                f"Base path used: {self.base_path}"
            )

    def _populate_combo_from_file(self, combo, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                items = [line.strip() for line in file if line.strip()]
                combo.clear()
                combo.addItem("")
                combo.addItems(items)
        except FileNotFoundError:
            print(f"File not found: {file_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = NewJobWizard()
    wizard.exec()

    sys.exit(app.exec())