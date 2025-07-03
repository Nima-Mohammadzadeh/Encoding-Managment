import os
import sys
from PySide6.QtWidgets import (
    QApplication, QDateEdit, QWizard, QWizardPage, QVBoxLayout, QFormLayout, QLineEdit, 
    QComboBox, QCheckBox, QPushButton, QLabel, QFileDialog, QSizePolicy, QWidget, QMessageBox, QHBoxLayout,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QValidator, QRegularExpressionValidator
import re
from qt_material import apply_stylesheet
import src.config as config
from src.utils.epc_conversion import (
    validate_upc, validate_upc_with_round_trip, generate_epc_preview_data, calculate_total_quantity_with_percentages,
    populate_customer_dropdown_from_templates, populate_label_sizes_for_customer,
    get_template_path, reverse_epc_to_upc_and_serial
)

class QuantityLineEdit(QLineEdit):
    """Custom QLineEdit that formats numbers with commas for readability."""
    
    def __init__(self):
        super().__init__()
        self.textChanged.connect(self.format_number)
    
    def format_number(self):
        # Store current state
        current_text = self.text()
        cursor_pos = self.cursorPosition()
        
        # Remove commas and get the raw number
        digits_only = current_text.replace(',', '')
        
        # Only process if it's a valid number
        if digits_only and digits_only.isdigit():
            # Format with commas
            formatted = f"{int(digits_only):,}"
            
            # Only update if text actually changed
            if formatted != current_text:
                # Count digits before cursor in original text
                digits_before_cursor = len(current_text[:cursor_pos].replace(',', ''))
                
                # Find position in formatted text for the same number of digits
                new_cursor_pos = 0
                digit_count = 0
                for i, char in enumerate(formatted):
                    if char.isdigit():
                        digit_count += 1
                        if digit_count >= digits_before_cursor:
                            new_cursor_pos = i + 1
                            break
                    elif digit_count > 0:
                        # We're past our target digit count, position after this character
                        new_cursor_pos = i + 1
                
                # Ensure cursor position is within bounds
                new_cursor_pos = max(0, min(new_cursor_pos, len(formatted)))
                
                # Update text and cursor position
                self.blockSignals(True)
                self.setText(formatted)
                self.setCursorPosition(new_cursor_pos)
                self.blockSignals(False)
    
    def get_numeric_value(self):
        """Return the numeric value without commas."""
        return self.text().replace(',', '')
    
    def set_numeric_value(self, value):
        """Set the value and format it."""
        if value and str(value).isdigit():
            self.setText(f"{int(value):,}")
        else:
            self.setText(str(value) if value else "")

class UPCLineEdit(QLineEdit):
    """Custom QLineEdit for UPC input with spacing and validation."""
    
    def __init__(self):
        super().__init__()
        self.setMaxLength(15)  # 12 digits + 3 spaces (space after every 3 digits)
        self.setPlaceholderText("123 456 789 012")
        self.textChanged.connect(self.format_upc)
        
        # Set up validator for digits only
        self.validator = QRegularExpressionValidator(r'^[\d\s]*$')
        self.setValidator(self.validator)
    
    def format_upc(self):
        # Store current state
        current_text = self.text()
        cursor_pos = self.cursorPosition()
        
        # Remove spaces and get only digits
        digits_only = re.sub(r'[^\d]', '', current_text)
        
        # Limit to 12 digits
        if len(digits_only) > 12:
            digits_only = digits_only[:12]
        
        # Format with spaces every 3 digits
        formatted = ''
        for i, char in enumerate(digits_only):
            if i > 0 and i % 3 == 0:
                formatted += ' '
            formatted += char
        
        # Only update if text actually changed
        if formatted != current_text:
            # Calculate new cursor position more accurately
            # Count digits before cursor in original text
            digits_before_cursor = len(re.sub(r'[^\d]', '', current_text[:cursor_pos]))
            
            # Find position in formatted text for the same number of digits
            new_cursor_pos = 0
            digit_count = 0
            for i, char in enumerate(formatted):
                if char.isdigit():
                    digit_count += 1
                    if digit_count > digits_before_cursor:
                        new_cursor_pos = i
                        break
                new_cursor_pos = i + 1
            
            # Ensure cursor position is within bounds
            new_cursor_pos = max(0, min(new_cursor_pos, len(formatted)))
            
            # Update text and cursor position
            self.blockSignals(True)
            self.setText(formatted)
            self.setCursorPosition(new_cursor_pos)
            self.blockSignals(False)
    
    def get_upc_value(self):
        """Return the UPC value without spaces."""
        return re.sub(r'[^\d]', '', self.text())
    
    def set_upc_value(self, value):
        """Set the UPC value and format it."""
        if value:
            # Remove non-digits and limit to 12
            clean_value = re.sub(r'[^\d]', '', str(value))[:12]
            self.setText(clean_value)
            self.format_upc()
        else:
            self.setText("")
    
    def is_valid(self):
        """Check if UPC is exactly 12 digits."""
        return len(self.get_upc_value()) == 12

class NewJobWizard(QWizard):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.base_path = base_path if base_path else os.path.dirname(os.path.abspath(__file__))
        self.setWindowTitle("New Job Wizard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(700, 600)  # Increased minimum size
        self.resize(800, 700)  # Set initial size

        self.job_data = {}

        self.addPage(JobDetailsPage(base_path=self.base_path))
        self.addPage(EncodingPage(base_path=self.base_path))
        self.addPage(EPCDatabasePage(base_path=self.base_path))
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
        # The save location page is now the 4th page, index 3
        save_page = self.page(self.pageIds()[3])
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
        self.setSubTitle("Enter job ticket details, customer, part number, inlay type, etc.")
        

        # Create a vertical layout for the dialog
        self.customer_name = QComboBox()
        self.inlay_type = QComboBox()
        self.label_size = QComboBox()

        self.part_number = QLineEdit()
        self.job_ticket_number = QLineEdit()
        self.po_number = QLineEdit()
        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate())

        # Error label for validation messages
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.get_lists()

        # Connect customer, label size, and inlay type changes to update template info
        self.customer_name.currentTextChanged.connect(self.trigger_template_update)
        self.label_size.currentTextChanged.connect(self.trigger_template_update)
        self.inlay_type.currentTextChanged.connect(self.trigger_template_update)

        self.layout = QFormLayout(self)
        self.layout.addRow("Customer: *", self.customer_name)
        self.layout.addRow("Part#: *", self.part_number) 
        self.layout.addRow("Job Ticket#: *", self.job_ticket_number)
        self.layout.addRow("PO#: *", self.po_number)
        self.layout.addRow("Inlay Type: *", self.inlay_type)
        self.layout.addRow("Label Size: *", self.label_size)
        self.layout.addRow("Due Date: *", self.due_date)
        
        # Add error label at the bottom
        self.layout.addRow("", self.error_label)

    def trigger_template_update(self):
        """Trigger template info update when customer or label size changes."""
        # Get the wizard and find the EPC page to update template info
        try:
            wizard = self.wizard()
            if wizard:
                for page_id in wizard.pageIds():
                    page = wizard.page(page_id)
                    if hasattr(page, 'update_template_info'):
                        page.update_template_info()
                        break
        except Exception as e:
            print(f"Error updating template info: {e}")

    def validatePage(self):
        """Validate all required fields before proceeding to next page."""
        errors = []
        
        # Check required fields
        if not self.customer_name.currentText().strip():
            errors.append("Customer is required")
        
        if not self.part_number.text().strip():
            errors.append("Part# is required")
        
        if not self.job_ticket_number.text().strip():
            errors.append("Job Ticket# is required")
        
        if not self.po_number.text().strip():
            errors.append("PO# is required")
        
        if not self.inlay_type.currentText().strip():
            errors.append("Inlay Type is required")
        
        if not self.label_size.currentText().strip():
            errors.append("Label Size is required")
        
        # Display errors if any
        if errors:
            self.error_label.setText("Please fix the following errors:\n• " + "\n• ".join(errors))
            self.error_label.show()
            return False
        else:
            self.error_label.hide()
            return True

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
        
        due_date_str = data.get("Due Date", "")
        if due_date_str:
            self.due_date.setDate(QDate.fromString(due_date_str, Qt.DateFormat.ISODate))
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
            "Label Size": self.label_size.currentText(),
            "Due Date": self.due_date.date().toString(Qt.DateFormat.ISODate)
        }
    

class EncodingPage(QWizardPage):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.setTitle("Step 2: Encoding Information")
        self.setSubTitle("Enter encoding information for the job, UPC, Serial Number, etc.")

        self.upc_number = UPCLineEdit()  # Use custom UPC input
        self.serial_number = QLineEdit()
        self.item = QLineEdit()
        self.qty = QuantityLineEdit()  # Use custom quantity input
        self.lpr = QLineEdit()
        
        # Add read-only field for calculated rolls
        self.rolls_display = QLineEdit()
        self.rolls_display.setReadOnly(True)
        self.rolls_display.setStyleSheet("background-color: #f0f0f0; color: #666;")
        self.rolls_display.setPlaceholderText("Calculated automatically")

        # Error label for validation messages
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        # Connect qty and lpr fields to trigger calculation
        self.qty.textChanged.connect(self.calculate_rolls)
        self.lpr.textChanged.connect(self.calculate_rolls)

        self.layout = QFormLayout(self)
        self.layout.addRow("Item: *", self.item)
        self.layout.addRow("Qty: *", self.qty)
        self.layout.addRow("UPC Number: *", self.upc_number) 
        self.layout.addRow("Serial Number: *", self.serial_number)
        self.layout.addRow("LPR: *", self.lpr)
        self.layout.addRow("Rolls:", self.rolls_display)
        
        # Add error label at the bottom
        self.layout.addRow("", self.error_label)

    def validatePage(self):
        """Validate all required fields before proceeding to next page."""
        errors = []
        
        # Check required fields
        if not self.item.text().strip():
            errors.append("Item is required")
        
        if not self.qty.get_numeric_value().strip():
            errors.append("Qty is required")
        elif not self.qty.get_numeric_value().isdigit():
            errors.append("Qty must be a valid number")
        
        if not self.upc_number.get_upc_value():
            errors.append("UPC Number is required")
        elif not self.upc_number.is_valid():
            errors.append("UPC Number must be exactly 12 digits")
        
        if not self.serial_number.text().strip():
            errors.append("Serial Number is required")
        
        if not self.lpr.text().strip():
            errors.append("LPR is required")
        elif not self.lpr.text().isdigit():
            errors.append("LPR must be a valid number")
        elif int(self.lpr.text()) <= 0:
            errors.append("LPR must be greater than 0")
        
        # Display errors if any
        if errors:
            self.error_label.setText("Please fix the following errors:\n• " + "\n• ".join(errors))
            self.error_label.show()
            return False
        else:
            self.error_label.hide()
            return True

    def calculate_rolls(self):
        """Calculate and display the number of rolls based on qty and lpr."""
        try:
            qty_text = self.qty.get_numeric_value().strip()
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
        
        # Handle quantity with proper formatting
        qty_value = data.get("Quantity", data.get("Qty", ""))
        self.qty.set_numeric_value(qty_value)
        
        self.lpr.setText(data.get("LPR", ""))
        
        # Handle UPC with proper formatting
        self.upc_number.set_upc_value(data.get("UPC Number", ""))
        
        self.serial_number.setText(data.get("Serial Number", ""))
        # Trigger calculation after setting data
        self.calculate_rolls()

    def get_data(self):
        # Calculate rolls for return data
        calculated_rolls = 0
        try:
            qty_text = self.qty.get_numeric_value().strip()
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
            "UPC Number": self.upc_number.get_upc_value(),  # Return clean UPC without spaces
            "Item": self.item.text(),
            "Quantity": self.qty.get_numeric_value(),  # Return numeric value without commas
            "LPR": self.lpr.text(),
            "Rolls": str(calculated_rolls)
        }


class EPCDatabasePage(QWizardPage):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.base_path = base_path
        self.setTitle("Step 3: EPC Database Generation & UPC Validation")
        self.setSubTitle("Configure EPC database generation settings, validate UPC, and preview data.")

        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Content widget for the scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)

        # UPC Validation Section
        self.validation_group = QGroupBox("UPC Validation")
        validation_layout = QVBoxLayout(self.validation_group)
        
        # Validation controls
        validation_controls_layout = QHBoxLayout()
        self.validate_upc_button = QPushButton("Validate UPC")
        self.validate_upc_button.clicked.connect(self.validate_current_upc)
        self.validate_upc_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        validation_controls_layout.addWidget(self.validate_upc_button)
        validation_controls_layout.addStretch()
        validation_layout.addLayout(validation_controls_layout)
        
        # Validation results display
        self.validation_result_display = QTextEdit()
        self.validation_result_display.setMaximumHeight(120)
        self.validation_result_display.setReadOnly(True)
        self.validation_result_display.setPlaceholderText("UPC validation results will appear here...")
        validation_layout.addWidget(self.validation_result_display)
        
        layout.addWidget(self.validation_group)

        # Enable EPC database generation checkbox
        self.enable_epc_generation = QCheckBox("Generate EPC Database Files")
        self.enable_epc_generation.stateChanged.connect(self.toggle_epc_options)
        layout.addWidget(self.enable_epc_generation)

        # EPC Options Group
        self.epc_options_group = QGroupBox("EPC Database Options")
        self.epc_options_group.setEnabled(False)
        epc_layout = QFormLayout(self.epc_options_group)

        # Quantity per database file
        self.qty_per_db = QLineEdit("1000")
        self.qty_per_db.setPlaceholderText("Number of records per database file")
        epc_layout.addRow("Qty per DB File:", self.qty_per_db)

        # Percentage buffers
        buffer_layout = QHBoxLayout()
        self.include_2_percent = QCheckBox("Add 2% buffer")
        self.include_7_percent = QCheckBox("Add 7% buffer")
        buffer_layout.addWidget(self.include_2_percent)
        buffer_layout.addWidget(self.include_7_percent)
        buffer_layout.addStretch()
        
        buffer_widget = QWidget()
        buffer_widget.setLayout(buffer_layout)
        epc_layout.addRow("Quantity Buffers:", buffer_widget)

        # Updated total quantity display
        self.total_qty_display = QLabel("Total Quantity: 0")
        self.total_qty_display.setStyleSheet("font-weight: bold; color: #2196F3;")
        epc_layout.addRow("", self.total_qty_display)

        # Connect percentage checkboxes to update total
        self.include_2_percent.stateChanged.connect(self.update_total_quantity)
        self.include_7_percent.stateChanged.connect(self.update_total_quantity)

        layout.addWidget(self.epc_options_group)

        # Preview section
        self.preview_group = QGroupBox("EPC Preview")
        self.preview_group.setEnabled(False)
        preview_layout = QVBoxLayout(self.preview_group)

        # Preview controls
        preview_controls_layout = QHBoxLayout()
        self.preview_button = QPushButton("Generate Preview")
        self.preview_button.clicked.connect(self.generate_preview)
        
        # Reverse validation button
        self.reverse_validate_button = QPushButton("Test Reverse Validation")
        self.reverse_validate_button.clicked.connect(self.test_reverse_validation)
        self.reverse_validate_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        preview_controls_layout.addWidget(self.preview_button)
        preview_controls_layout.addWidget(self.reverse_validate_button)
        preview_controls_layout.addStretch()
        preview_layout.addLayout(preview_controls_layout)

        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["UPC", "Serial #", "EPC"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setMaximumHeight(200)
        preview_layout.addWidget(self.preview_table)

        layout.addWidget(self.preview_group)

        # Reverse Validation Results
        self.reverse_validation_group = QGroupBox("Round-Trip Validation Results")
        reverse_layout = QVBoxLayout(self.reverse_validation_group)
        
        self.reverse_validation_display = QTextEdit()
        self.reverse_validation_display.setMaximumHeight(100)
        self.reverse_validation_display.setReadOnly(True)
        self.reverse_validation_display.setPlaceholderText("Round-trip validation results will appear here...")
        reverse_layout.addWidget(self.reverse_validation_display)
        
        layout.addWidget(self.reverse_validation_group)

        # Template information
        self.template_info_group = QGroupBox("Template Information")
        template_layout = QFormLayout(self.template_info_group)
        
        self.template_status_label = QLabel("No template information available")
        self.template_status_label.setWordWrap(True)
        template_layout.addRow("Template Status:", self.template_status_label)
        
        layout.addWidget(self.template_info_group)

        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def initializePage(self):
        """Initialize the page when it's first displayed."""
        super().initializePage()
        # Update template information when page is shown
        self.update_template_info()

    def validate_current_upc(self):
        """Validate the UPC from the previous page using round-trip conversion."""
        try:
            wizard = self.wizard()
            encoding_page = wizard.page(wizard.pageIds()[1])  # EncodingPage
            upc = encoding_page.upc_number.get_upc_value()
            
            if not upc:
                self.validation_result_display.setHtml("""
                <p style='color: red; font-weight: bold;'>❌ No UPC entered</p>
                <p>Please enter a UPC on the previous page before validation.</p>
                """)
                return
            
            # Perform round-trip validation
            is_valid, details = validate_upc_with_round_trip(upc)
            
            if is_valid:
                self.validation_result_display.setHtml(f"""
                <p style='color: green; font-weight: bold;'>✅ UPC Validation Successful</p>
                <p><strong>UPC:</strong> {details['original_upc']}</p>
                <p><strong>Test EPC Generated:</strong> {details['test_epc']}</p>
                <p><strong>Recovered UPC:</strong> {details['recovered_upc']}</p>
                <p><strong>Status:</strong> {details['success']}</p>
                """)
            else:
                error_msg = details.get('error', 'Unknown error')
                
                if 'Round-trip validation failed' in error_msg:
                    self.validation_result_display.setHtml(f"""
                    <p style='color: red; font-weight: bold;'>❌ Invalid UPC - Round-trip Validation Failed</p>
                    <p><strong>Original UPC:</strong> {details.get('original_upc', 'N/A')}</p>
                    <p><strong>Recovered UPC:</strong> {details.get('recovered_upc', 'N/A')}</p>
                    <p><strong>Generated EPC:</strong> {details.get('epc_generated', 'N/A')}</p>
                    <p style='color: orange;'><strong>Issue:</strong> The UPC does not convert back to itself when processed through EPC conversion. This indicates an invalid UPC format.</p>
                    """)
                else:
                    self.validation_result_display.setHtml(f"""
                    <p style='color: red; font-weight: bold;'>❌ UPC Validation Failed</p>
                    <p><strong>Error:</strong> {error_msg}</p>
                    """)
                    
        except Exception as e:
            self.validation_result_display.setHtml(f"""
            <p style='color: red; font-weight: bold;'>❌ Validation Error</p>
            <p><strong>Error:</strong> {str(e)}</p>
            """)

    def test_reverse_validation(self):
        """Test reverse validation by converting EPCs from the preview table back to UPC."""
        try:
            if self.preview_table.rowCount() == 0:
                self.reverse_validation_display.setHtml("""
                <p style='color: orange;'>⚠️ No preview data available. Generate preview first.</p>
                """)
                return
            
            # Get a few EPCs from the preview table
            test_results = []
            test_count = min(3, self.preview_table.rowCount())  # Test first 3 rows
            
            for row in range(test_count):
                original_upc = self.preview_table.item(row, 0).text()
                original_serial = int(self.preview_table.item(row, 1).text())
                epc_hex = self.preview_table.item(row, 2).text()
                
                # Reverse the EPC
                recovered_upc, recovered_serial = reverse_epc_to_upc_and_serial(epc_hex)
                
                success = (recovered_upc == original_upc and recovered_serial == original_serial)
                test_results.append({
                    'row': row + 1,
                    'original_upc': original_upc,
                    'original_serial': original_serial,
                    'epc': epc_hex,
                    'recovered_upc': recovered_upc,
                    'recovered_serial': recovered_serial,
                    'success': success
                })
            
            # Generate results display
            html_content = []
            all_passed = all(result['success'] for result in test_results)
            
            if all_passed:
                html_content.append("<p style='color: green; font-weight: bold;'>✅ All reverse validations passed!</p>")
            else:
                html_content.append("<p style='color: red; font-weight: bold;'>❌ Some reverse validations failed!</p>")
            
            for result in test_results:
                status = "✅" if result['success'] else "❌"
                color = "green" if result['success'] else "red"
                html_content.append(f"""
                <p style='color: {color};'><strong>Row {result['row']}:</strong> {status}</p>
                <p style='margin-left: 20px; font-size: 11px;'>
                UPC: {result['original_upc']} → {result['recovered_upc']}<br/>
                Serial: {result['original_serial']} → {result['recovered_serial']}
                </p>
                """)
            
            self.reverse_validation_display.setHtml("".join(html_content))
            
        except Exception as e:
            self.reverse_validation_display.setHtml(f"""
            <p style='color: red; font-weight: bold;'>❌ Reverse validation error</p>
            <p><strong>Error:</strong> {str(e)}</p>
            """)

    def toggle_epc_options(self, state):
        """Enable/disable EPC options based on checkbox state."""
        enabled = state == Qt.CheckState.Checked.value
        self.epc_options_group.setEnabled(enabled)
        self.preview_group.setEnabled(enabled)
        
        if enabled:
            self.update_total_quantity()
            self.update_template_info()

    def update_total_quantity(self):
        """Update the total quantity display based on base quantity and buffers."""
        try:
            # Get base quantity from previous page (EncodingPage)
            wizard = self.wizard()
            encoding_page = wizard.page(wizard.pageIds()[1])  # EncodingPage is index 1
            base_qty_text = encoding_page.qty.get_numeric_value().strip()
            
            if base_qty_text and base_qty_text.isdigit():
                base_qty = int(base_qty_text)
                total_qty = calculate_total_quantity_with_percentages(
                    base_qty,
                    self.include_2_percent.isChecked(),
                    self.include_7_percent.isChecked()
                )
                self.total_qty_display.setText(f"Total Quantity: {total_qty:,}")
            else:
                self.total_qty_display.setText("Total Quantity: Invalid base quantity")
        except Exception as e:
            self.total_qty_display.setText(f"Total Quantity: Error - {str(e)}")

    def update_template_info(self):
        """Update template information based on selected customer, label size, and inlay type."""
        try:
            wizard = self.wizard()
            job_details_page = wizard.page(wizard.pageIds()[0])  # JobDetailsPage is index 0
            
            customer = job_details_page.customer_name.currentText().strip()
            label_size = job_details_page.label_size.currentText().strip()
            inlay_type = job_details_page.inlay_type.currentText().strip()
            
            if customer and label_size:
                from src.utils.epc_conversion import get_template_path_with_inlay, list_available_templates
                
                # Use enhanced template lookup with inlay type
                template_path = get_template_path_with_inlay(config.get_template_base_path(), customer, label_size, inlay_type)
                
                if template_path and os.path.exists(template_path):
                    template_name = os.path.basename(template_path)
                    self.template_status_label.setText(f"✓ Template found: {template_name}\nWill be copied to print folder during job creation.")
                    self.template_status_label.setStyleSheet("color: green;")
                else:
                    # Show available templates for this label size
                    available_templates = list_available_templates(config.get_template_base_path())
                    
                    if label_size in available_templates:
                        template_list = available_templates[label_size]
                        template_names = [os.path.basename(t) for t in template_list[:2]]  # Show first 2
                        template_display = ", ".join(template_names)
                        if len(template_list) > 2:
                            template_display += f" (and {len(template_list) - 2} more)"
                        
                        self.template_status_label.setText(f"⚠ Best match not found for {customer} (Inlay: {inlay_type})\nAvailable for {label_size}: {template_display}\nFirst available template will be used.")
                        self.template_status_label.setStyleSheet("color: orange;")
                    else:
                        # Try to find label size directory with case-insensitive matching
                        template_base_path = config.get_template_base_path()
                        found_label_size = None
                        if template_base_path and os.path.exists(template_base_path):
                            try:
                                for item in os.listdir(template_base_path):
                                    if os.path.isdir(os.path.join(template_base_path, item)):
                                        if item.lower().replace(' ', '') == label_size.lower().replace(' ', ''):
                                            found_label_size = item
                                            break
                            except Exception:
                                pass
                        
                        if found_label_size and found_label_size in available_templates:
                            template_list = available_templates[found_label_size]
                            template_names = [os.path.basename(t) for t in template_list[:2]]
                            template_display = ", ".join(template_names)
                            if len(template_list) > 2:
                                template_display += f" (and {len(template_list) - 2} more)"
                            
                            self.template_status_label.setText(f"⚠ Best match not found for {customer} (Inlay: {inlay_type})\nAvailable for {found_label_size}: {template_display}\nFirst available template will be used.")
                            self.template_status_label.setStyleSheet("color: orange;")
                        else:
                            self.template_status_label.setText(f"⚠ No templates found for label size: {label_size}\nJob will be created without template file.")
                            self.template_status_label.setStyleSheet("color: red;")
            else:
                self.template_status_label.setText("Customer and Label Size required for template lookup")
                self.template_status_label.setStyleSheet("color: gray;")
        except Exception as e:
            self.template_status_label.setText(f"Error checking template: {str(e)}")
            self.template_status_label.setStyleSheet("color: red;")

    def generate_preview(self):
        """Generate and display EPC preview data."""
        try:
            wizard = self.wizard()
            encoding_page = wizard.page(wizard.pageIds()[1])  # EncodingPage
            
            upc = encoding_page.upc_number.get_upc_value()
            serial_text = encoding_page.serial_number.text().strip()
            
            # Use round-trip validation for UPC
            if not upc:
                self.show_error("UPC required for preview")
                return
                
            is_valid, details = validate_upc_with_round_trip(upc)
            if not is_valid:
                error_msg = details.get('error', 'Invalid UPC')
                self.show_error(f"UPC validation failed: {error_msg}")
                return
            
            if not serial_text or not serial_text.isdigit():
                self.show_error("Valid starting serial number required for preview")
                return
            
            start_serial = int(serial_text)
            
            # Generate preview data
            preview_df = generate_epc_preview_data(upc, start_serial, 10)
            
            # Populate table
            self.preview_table.setRowCount(len(preview_df))
            for row, (_, data) in enumerate(preview_df.iterrows()):
                self.preview_table.setItem(row, 0, QTableWidgetItem(data['UPC']))
                self.preview_table.setItem(row, 1, QTableWidgetItem(str(data['Serial #'])))
                self.preview_table.setItem(row, 2, QTableWidgetItem(data['EPC']))
            
            self.hide_error()
            
        except Exception as e:
            self.show_error(f"Preview generation failed: {str(e)}")

    def show_error(self, message):
        """Show error message."""
        self.error_label.setText(message)
        self.error_label.show()

    def hide_error(self):
        """Hide error message."""
        self.error_label.hide()

    def validatePage(self):
        """Validate EPC settings if enabled."""
        if not self.enable_epc_generation.isChecked():
            return True  # Skip validation if EPC generation is disabled
        
        # Validate qty per DB
        qty_per_db_text = self.qty_per_db.text().strip()
        if not qty_per_db_text or not qty_per_db_text.isdigit() or int(qty_per_db_text) <= 0:
            self.show_error("Qty per DB must be a positive number")
            return False
        
        # Validate UPC and serial from previous page with round-trip validation
        wizard = self.wizard()
        encoding_page = wizard.page(wizard.pageIds()[1])
        
        upc = encoding_page.upc_number.get_upc_value()
        
        # Use round-trip validation for more robust UPC checking
        is_valid, details = validate_upc_with_round_trip(upc)
        if not is_valid:
            error_msg = details.get('error', 'Invalid UPC')
            if 'Round-trip validation failed' in error_msg:
                self.show_error(f"UPC validation failed: {upc} does not convert properly through EPC conversion. Please verify the UPC is correct.")
            else:
                self.show_error(f"UPC validation failed: {error_msg}")
            return False
        
        serial_text = encoding_page.serial_number.text().strip()
        if not serial_text or not serial_text.isdigit():
            self.show_error("Valid starting serial number required for EPC generation")
            return False
        
        self.hide_error()
        return True

    def get_data(self):
        """Return EPC database configuration data."""
        data = {
            "Enable EPC Generation": self.enable_epc_generation.isChecked(),
            "Qty per DB": self.qty_per_db.text().strip(),
            "Include 2% Buffer": self.include_2_percent.isChecked(),
            "Include 7% Buffer": self.include_7_percent.isChecked()
        }
        
        if self.enable_epc_generation.isChecked():
            # Calculate total quantity for storage
            try:
                wizard = self.wizard()
                encoding_page = wizard.page(wizard.pageIds()[1])
                base_qty_text = encoding_page.qty.get_numeric_value().strip()
                if base_qty_text and base_qty_text.isdigit():
                    base_qty = int(base_qty_text)
                    total_qty = calculate_total_quantity_with_percentages(
                        base_qty,
                        self.include_2_percent.isChecked(),
                        self.include_7_percent.isChecked()
                    )
                    data["Total Quantity with Buffers"] = total_qty
            except:
                pass
        
        return data

    def set_data(self, data):
        """Set EPC database configuration data."""
        self.enable_epc_generation.setChecked(data.get("Enable EPC Generation", False))
        self.qty_per_db.setText(data.get("Qty per DB", "1000"))
        self.include_2_percent.setChecked(data.get("Include 2% Buffer", False))
        self.include_7_percent.setChecked(data.get("Include 7% Buffer", False))
        
        # Trigger updates
        self.toggle_epc_options(self.enable_epc_generation.checkState())


class SaveLocationPage(QWizardPage):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.setTitle("Step 4: Save Location")
        self.setSubTitle("Select the location to save the job")

        self.custom_save_location = None

        self.SharedDrive_location = QCheckBox("Auto search/save")
        self.Desktop_location = QCheckBox("Desktop")
        self.Browse_Button = QPushButton("Browse")

        # Add a label to show selected custom path
        self.custom_path_label = QLabel("No custom path selected")
        self.custom_path_label.setWordWrap(True)
        self.custom_path_label.setStyleSheet("color: gray; font-size: 10px;")

        # Error label for validation messages
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

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
        self.layout.addRow("Save Location: *", save_location_widget)
        self.layout.addRow("", self.custom_path_label)
        
        # Add error label at the bottom
        self.layout.addRow("", self.error_label)

        self.update_browse_button_state()

    def validatePage(self):
        """Validate that at least one save location is selected."""
        has_selection = (self.SharedDrive_location.isChecked() or 
                        self.Desktop_location.isChecked() or 
                        self.custom_save_location)
        
        if not has_selection:
            self.error_label.setText("Please select at least one save location")
            self.error_label.show()
            return False
        else:
            self.error_label.hide()
            return True

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