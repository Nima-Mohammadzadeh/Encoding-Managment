from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QPushButton, QHBoxLayout, QFileDialog, QMessageBox
)
import webbrowser, os, platform
from src.widgets.job_details_dialog import PDFProgressDialog

class ChecklistGeneratorDialog(QDialog):
    def __init__(self, base_path, parent=None):
        super().__init__(parent)
        self.base_path = base_path
        self.setWindowTitle("Checklist Generator")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.fields = {}
        # These are the keys from PDFGenerationWorker's `fields_to_fill`
        field_keys = ["Customer", "Part#", "Ticket#", "PO#", "Inlay Type", "Label Size", "Qty", "Item", "UPC Number", "LPR", "Rolls", "Start", "End"]
        
        for key in field_keys:
            line_edit = QLineEdit()
            self.fields[key] = line_edit
            form_layout.addRow(f"{key}:", line_edit)
            
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
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Generate")
        self.buttons.accepted.connect(self.handle_generate)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def browse_for_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", "", QFileDialog.Option.ShowDirsOnly)
        if directory:
            self.output_dir_input.setText(directory)
            
    def handle_generate(self):
        job_data = {key: field.text() for key, field in self.fields.items()}
        output_dir = self.output_dir_input.text()

        if not all(job_data.values()):
             QMessageBox.warning(self, "Missing Information", "Please fill out all fields.")
             return
        
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Invalid Directory", "Please select a valid output directory.")
            return
            
        template_path = os.path.join(self.base_path, "data", "Encoding Checklist V4.1.pdf")
        if not os.path.exists(template_path):
            QMessageBox.critical(self, "Error", "Checklist template 'Encoding Checklist V4.1.pdf' not found in data directory.")
            return

        # Sanitize filename components
        customer = job_data.get('Customer', 'UnknownCustomer').replace('/', '-').replace('\\', '-')
        ticket = job_data.get('Ticket#', 'UnknownTicket').replace('/', '-').replace('\\', '-')
        po = job_data.get('PO#', 'UnknownPO').replace('/', '-').replace('\\', '-')
        
        output_file_name = f"{customer}-{ticket}-{po}-Checklist.pdf"
        save_path = os.path.join(output_dir, output_file_name)
        
        self.progress_dialog = PDFProgressDialog(template_path, job_data, save_path, self)
        self.progress_dialog.generation_finished.connect(self.on_generation_finished)
        self.progress_dialog.exec()

    def on_generation_finished(self, success, result):
        if success:
            pdf_path = result
            QMessageBox.information(self, "Success", f"Checklist generated successfully:\n{pdf_path}")
            self.open_pdf(pdf_path)
            self.accept()
        else:
            error_message = result
            if "cancelled" not in error_message.lower():
                QMessageBox.critical(self, "Generation Error", f"Failed to generate checklist:\n{error_message}")

    def open_pdf(self, pdf_path):
        try:
            # Use webbrowser for cross-platform compatibility
            webbrowser.open(f"file:///{os.path.abspath(pdf_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open PDF file: {e}") 