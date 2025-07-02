import os
import webbrowser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox,
    QCheckBox, QDialogButtonBox, QPushButton, QHBoxLayout, QFileDialog, QMessageBox,
    QLabel, QGroupBox, QScrollArea, QWidget
)
from src.utils.epc_conversion import calculate_total_quantity_with_percentages, validate_upc
from src.utils.roll_tracker import generate_roll_tracker_html
from src.widgets.job_details_dialog import EPCProgressDialog

class RollTrackerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Roll Tracker Generator")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.resize(520, 600)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Scroll Area Setup ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("scrollArea")
        
        scroll_content_widget = QWidget()
        form_container_layout = QVBoxLayout(scroll_content_widget)

        # Job Info Group
        job_info_group = QGroupBox("Job Information")
        job_info_layout = QFormLayout(job_info_group)
        self.job_ticket_input = QLineEdit()
        self.customer_name_input = QLineEdit()
        job_info_layout.addRow("Job Ticket #:", self.job_ticket_input)
        job_info_layout.addRow("Customer Name:", self.customer_name_input)
        form_container_layout.addWidget(job_info_group)

        # EPC & Quantity Group
        epc_group = QGroupBox("EPC & Quantity Parameters")
        epc_layout = QFormLayout(epc_group)
        self.upc_input = QLineEdit()
        self.upc_input.setPlaceholderText("Enter 12-digit UPC")
        self.start_serial_input = QSpinBox()
        self.start_serial_input.setRange(1, 999999999)
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 999999999)
        self.quantity_input.setValue(1000)
        self.lpr_input = QSpinBox()
        self.lpr_input.setRange(1, 10000)
        self.lpr_input.setValue(100)
        self.qty_db_input = QSpinBox()
        self.qty_db_input.setRange(100, 100000)
        self.qty_db_input.setValue(1000)
        self.two_percent_check = QCheckBox("Add 2% buffer")
        self.seven_percent_check = QCheckBox("Add 7% buffer")
        
        epc_layout.addRow("UPC:", self.upc_input)
        epc_layout.addRow("Starting Serial #:", self.start_serial_input)
        epc_layout.addRow("Base Quantity:", self.quantity_input)
        epc_layout.addRow("LPR (Labels/Roll):", self.lpr_input)
        epc_layout.addRow("QTY per DB File:", self.qty_db_input)
        epc_layout.addRow("Buffers:", self.two_percent_check)
        epc_layout.addRow("", self.seven_percent_check)
        form_container_layout.addWidget(epc_group)
        
        # Output Group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setReadOnly(True)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_for_directory)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.output_dir_input)
        dir_layout.addWidget(self.browse_btn)
        
        self.generate_db_check = QCheckBox("Generate EPC database files along with tracker")
        self.generate_db_check.setChecked(True)

        output_layout.addRow("Output Directory:", dir_layout)
        output_layout.addRow(self.generate_db_check)
        form_container_layout.addWidget(output_group)
        
        form_container_layout.addStretch()

        # Add the container widget to the scroll area
        scroll_area.setWidget(scroll_content_widget)
        main_layout.addWidget(scroll_area)

        # Buttons (outside the scroll area)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Generate")
        self.buttons.accepted.connect(self.handle_generate)
        self.buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.buttons)

    def browse_for_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir_input.setText(directory)

    def handle_generate(self):
        params = self.get_params()
        if not params:
            return

        # Generate Roll Tracker
        html_file = generate_roll_tracker_html(params)
        if not html_file:
            QMessageBox.critical(self, "Error", "Failed to generate the Roll Tracker HTML file.")
            return
            
        # Optionally generate DB files
        if self.generate_db_check.isChecked():
            self.run_db_generation(params)
        else:
            QMessageBox.information(self, "Success", f"Roll Tracker generated successfully:\n{html_file}")
            self.open_file(html_file)
            self.accept()
            
    def run_db_generation(self, params):
        data_folder_path = os.path.join(params['output_directory'], 'data')
        os.makedirs(data_folder_path, exist_ok=True)
        
        self.progress_dialog = EPCProgressDialog(
            params['upc'], 
            params['start_serial'], 
            params['adjusted_qty'], 
            params['qty_per_db'], 
            data_folder_path, 
            self
        )
        self.progress_dialog.generation_finished.connect(
            lambda s, r: self.on_db_generation_finished(s, r, params)
        )
        self.progress_dialog.exec()

    def on_db_generation_finished(self, success, result, params):
        html_file = os.path.join(params['output_directory'], "roll tracker", f"roll_tracker_{params['upc']}.html")
        if success:
            QMessageBox.information(
                self, "Success", 
                f"Roll Tracker and {len(result)} database files generated successfully."
            )
            self.open_file(html_file)
            self.accept()
        else:
            error = result
            QMessageBox.warning(
                self, "DB Generation Failed",
                f"Roll Tracker was created, but database generation failed: {error}"
            )

    def get_params(self):
        # Validation
        upc = self.upc_input.text()
        if not validate_upc(upc):
            QMessageBox.warning(self, "Invalid UPC", "Please enter a valid 12-digit UPC.")
            return None
            
        output_dir = self.output_dir_input.text()
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Invalid Directory", "Please select a valid output directory.")
            return None

        base_qty = self.quantity_input.value()
        adjusted_qty = calculate_total_quantity_with_percentages(
            base_qty, self.two_percent_check.isChecked(), self.seven_percent_check.isChecked()
        )
        
        return {
            'job_ticket_number': self.job_ticket_input.text(),
            'customer_name': self.customer_name_input.text(),
            'upc': upc,
            'start_serial': self.start_serial_input.value(),
            'base_qty': base_qty,
            'adjusted_qty': adjusted_qty,
            'lpr': self.lpr_input.value(),
            'qty_per_db': self.qty_db_input.value(),
            'output_directory': output_dir
        }

    def open_file(self, file_path):
        try:
            webbrowser.open(f"file:///{os.path.abspath(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file: {e}") 