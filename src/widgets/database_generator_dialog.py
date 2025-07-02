from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QDialogButtonBox, QPushButton, QHBoxLayout, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from src.utils.epc_conversion import (
    validate_upc,
    calculate_total_quantity_with_percentages,
    generate_epc_database_files_with_progress
)
from src.widgets.job_details_dialog import EPCProgressDialog
import os


class DatabaseGeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database Generator")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # UPC Number
        self.upc_input = QLineEdit()
        self.upc_input.setPlaceholderText("Enter 12-digit UPC")
        form_layout.addRow("UPC Number:", self.upc_input)

        # Starting Serial
        self.serial_spin = QSpinBox()
        self.serial_spin.setRange(1, 999999999)
        self.serial_spin.setValue(1)
        form_layout.addRow("Starting Serial Number:", self.serial_spin)
        
        # Base Quantity
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 999999999)
        self.qty_spin.setValue(1000)
        form_layout.addRow("Base Quantity:", self.qty_spin)
        
        # Quantity per DB
        self.qty_per_db_spin = QSpinBox()
        self.qty_per_db_spin.setRange(100, 100000)
        self.qty_per_db_spin.setStepType(QSpinBox.StepType.AdaptiveDecimalStepType)
        self.qty_per_db_spin.setValue(1000)
        form_layout.addRow("Quantity per DB File:", self.qty_per_db_spin)
        
        # Buffers
        self.buffer_2_check = QCheckBox("Add 2% buffer")
        self.buffer_7_check = QCheckBox("Add 7% buffer")
        form_layout.addRow("Buffers:", self.buffer_2_check)
        form_layout.addRow("", self.buffer_7_check)

        # Output Directory
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setReadOnly(True)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_for_directory)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.output_dir_input)
        dir_layout.addWidget(self.browse_btn)
        form_layout.addRow("Output Directory:", dir_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.handle_generate)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def browse_for_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            self.output_dir_input.setText(directory)
            
    def handle_generate(self):
        upc = self.upc_input.text()
        output_dir = self.output_dir_input.text()

        if not validate_upc(upc):
            QMessageBox.warning(self, "Invalid UPC", "Please enter a valid 12-digit UPC.")
            return

        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Invalid Directory", "Please select a valid output directory.")
            return

        # All inputs are valid, proceed with generation
        self.accept()
        self.run_generation()

    def get_parameters(self):
        return {
            "upc": self.upc_input.text(),
            "start_serial": self.serial_spin.value(),
            "base_qty": self.qty_spin.value(),
            "qty_per_db": self.qty_per_db_spin.value(),
            "include_2_percent": self.buffer_2_check.isChecked(),
            "include_7_percent": self.buffer_7_check.isChecked(),
            "output_dir": self.output_dir_input.text()
        }

    def run_generation(self):
        params = self.get_parameters()
        
        total_qty = calculate_total_quantity_with_percentages(
            params['base_qty'], params['include_2_percent'], params['include_7_percent']
        )
        
        # Ensure the 'data' subdirectory exists, as this is where files are placed
        data_folder_path = os.path.join(params['output_dir'], 'data')
        os.makedirs(data_folder_path, exist_ok=True)
        
        self.progress_dialog = EPCProgressDialog(
            params['upc'], 
            params['start_serial'], 
            total_qty, 
            params['qty_per_db'], 
            data_folder_path, 
            self
        )
        
        self.progress_dialog.generation_finished.connect(self.on_generation_finished)
        self.progress_dialog.exec()

    def on_generation_finished(self, success, result):
        if success:
            created_files = result
            QMessageBox.information(
                self,
                "Generation Complete",
                f"Successfully generated {len(created_files)} database files in:\n{os.path.dirname(created_files[0])}"
            )
        else:
            error_message = result
            if "cancelled" not in error_message.lower():
                QMessageBox.critical(
                    self, "Generation Error", f"Failed to generate database:\n{error_message}"
                ) 