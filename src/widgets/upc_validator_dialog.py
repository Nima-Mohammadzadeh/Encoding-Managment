"""
UPC Validator Dialog

This dialog provides comprehensive UPC validation including:
- Format validation
- Check digit validation  
- Round-trip EPC conversion testing
- Detailed breakdown of UPC components
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QGroupBox, QFrame,
    QGridLayout, QMessageBox, QSizePolicy, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap, QPalette

from src.utils.epc_conversion import (
    validate_upc, validate_upc_with_round_trip, calculate_upc_check_digit,
    generate_epc, reverse_epc_to_upc_and_serial
)


class UPCValidatorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UPC Validator")
        self.setModal(True)
        self.setMinimumSize(700, 650)  # Increased minimum size
        self.resize(750, 700)  # Set initial size
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UPC validator UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # Create scroll area for main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create content widget for scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # Header section
        header_layout = QHBoxLayout()
        
        title_label = QLabel("UPC Code Validator")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        subtitle_label = QLabel("Validate UPC codes with comprehensive analysis")
        subtitle_label.setStyleSheet("color: #888888;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        
        content_layout.addLayout(header_layout)
        
        # Input section
        input_group = QGroupBox("UPC Input")
        input_layout = QFormLayout(input_group)
        input_layout.setLabelAlignment(Qt.AlignRight)
        
        self.upc_input = QLineEdit()
        self.upc_input.setPlaceholderText("Enter 12-digit UPC code (e.g., 012345678905)")
        self.upc_input.setMaxLength(12)
        self.upc_input.textChanged.connect(self.on_upc_changed)
        
        self.validate_btn = QPushButton("Validate UPC")
        self.validate_btn.clicked.connect(self.validate_upc)
        self.validate_btn.setEnabled(False)
        
        input_layout.addRow("UPC Code:", self.upc_input)
        input_layout.addRow("", self.validate_btn)
        
        content_layout.addWidget(input_group)
        
        # Results section
        results_group = QGroupBox("Validation Results")
        results_layout = QVBoxLayout(results_group)
        
        # Status indicator
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.StyledPanel)
        self.status_frame.setMinimumHeight(50)
        self.status_frame.setMaximumHeight(70)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("Enter a UPC code to validate")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(12)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        
        status_layout.addWidget(self.status_label)
        results_layout.addWidget(self.status_frame)
        
        # Detailed breakdown
        breakdown_layout = QGridLayout()
        breakdown_layout.setSpacing(8)
        breakdown_layout.setColumnStretch(1, 1)  # Make second column stretch
        
        # Basic validation info
        breakdown_layout.addWidget(QLabel("Format Valid:"), 0, 0)
        self.format_valid_label = QLabel("—")
        breakdown_layout.addWidget(self.format_valid_label, 0, 1)
        
        breakdown_layout.addWidget(QLabel("Check Digit Valid:"), 1, 0)
        self.check_digit_valid_label = QLabel("—")
        breakdown_layout.addWidget(self.check_digit_valid_label, 1, 1)
        
        breakdown_layout.addWidget(QLabel("EPC Round-trip Test:"), 2, 0)
        self.round_trip_label = QLabel("—")
        breakdown_layout.addWidget(self.round_trip_label, 2, 1)
        
        # UPC breakdown
        breakdown_layout.addWidget(QLabel("Company Prefix:"), 3, 0)
        self.company_prefix_label = QLabel("—")
        breakdown_layout.addWidget(self.company_prefix_label, 3, 1)
        
        breakdown_layout.addWidget(QLabel("Item Reference:"), 4, 0)
        self.item_reference_label = QLabel("—")
        breakdown_layout.addWidget(self.item_reference_label, 4, 1)
        
        breakdown_layout.addWidget(QLabel("Check Digit:"), 5, 0)
        self.check_digit_label = QLabel("—")
        breakdown_layout.addWidget(self.check_digit_label, 5, 1)
        
        results_layout.addLayout(breakdown_layout)
        
        # Detailed results text area
        self.results_text = QTextEdit()
        self.results_text.setMinimumHeight(120)
        self.results_text.setMaximumHeight(250)  # Increased from 150 to 250
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Detailed validation results will appear here...")
        
        results_layout.addWidget(QLabel("Detailed Analysis:"))
        results_layout.addWidget(self.results_text)
        
        content_layout.addWidget(results_group)
        
        # EPC Test section
        epc_group = QGroupBox("EPC Conversion Test")
        epc_layout = QFormLayout(epc_group)
        epc_layout.setLabelAlignment(Qt.AlignRight)
        
        self.test_serial_input = QLineEdit()
        self.test_serial_input.setPlaceholderText("1000")
        self.test_serial_input.setText("1000")
        
        self.test_epc_btn = QPushButton("Generate Test EPC")
        self.test_epc_btn.clicked.connect(self.test_epc_generation)
        self.test_epc_btn.setEnabled(False)
        
        self.epc_result_label = QLabel("—")
        self.epc_result_label.setWordWrap(True)
        self.epc_result_label.setMinimumHeight(60)
        self.epc_result_label.setAlignment(Qt.AlignTop)
        self.epc_result_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 8px; border: 1px solid #555;")
        
        epc_layout.addRow("Test Serial Number:", self.test_serial_input)
        epc_layout.addRow("", self.test_epc_btn)
        epc_layout.addRow("Generated EPC:", self.epc_result_label)
        
        content_layout.addWidget(epc_group)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Button row (outside scroll area for always visible)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_results)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        
        # Initialize UI state
        self.clear_results()
        
    def on_upc_changed(self):
        """Handle UPC input changes"""
        upc = self.upc_input.text().strip()
        self.validate_btn.setEnabled(len(upc) == 12 and upc.isdigit())
        self.test_epc_btn.setEnabled(False)
        
        if len(upc) < 12:
            self.clear_results()
        
    def validate_upc(self):
        """Validate the entered UPC code"""
        upc = self.upc_input.text().strip()
        
        if not upc:
            return
            
        # Clear previous results
        self.clear_results(keep_status=False)
        
        try:
            # Basic format validation
            format_valid = len(upc) == 12 and upc.isdigit()
            self.format_valid_label.setText("✅ Valid" if format_valid else "❌ Invalid")
            
            if not format_valid:
                self.status_label.setText("❌ Invalid UPC Format")
                self.status_frame.setStyleSheet("background-color: #4a2c2c; border: 1px solid #8b0000;")
                self.results_text.setPlainText("UPC must be exactly 12 digits.")
                return
            
            # UPC breakdown
            company_prefix = upc[:6]
            item_reference = upc[6:11]  
            check_digit = upc[11]
            
            self.company_prefix_label.setText(company_prefix)
            self.item_reference_label.setText(item_reference)
            self.check_digit_label.setText(check_digit)
            
            # Check digit validation
            calculated_check_digit = calculate_upc_check_digit(upc[:11])
            check_digit_valid = int(check_digit) == calculated_check_digit
            
            self.check_digit_valid_label.setText(
                f"✅ Valid ({calculated_check_digit})" if check_digit_valid 
                else f"❌ Invalid (expected {calculated_check_digit})"
            )
            
            # Round-trip EPC validation
            round_trip_valid, round_trip_details = validate_upc_with_round_trip(upc)
            self.round_trip_label.setText("✅ Passed" if round_trip_valid else "❌ Failed")
            
            # Overall status
            overall_valid = format_valid and check_digit_valid and round_trip_valid
            
            if overall_valid:
                self.status_label.setText("✅ UPC is Valid")
                self.status_frame.setStyleSheet("background-color: #2c4a2c; border: 1px solid #008000;")
                self.test_epc_btn.setEnabled(True)
            else:
                self.status_label.setText("❌ UPC has Issues")
                self.status_frame.setStyleSheet("background-color: #4a2c2c; border: 1px solid #8b0000;")
                
            # Detailed results
            results = []
            results.append(f"UPC Analysis for: {upc}")
            results.append("=" * 40)
            results.append(f"Company Prefix: {company_prefix}")
            results.append(f"Item Reference: {item_reference}")
            results.append(f"Check Digit: {check_digit} (calculated: {calculated_check_digit})")
            results.append("")
            
            if check_digit_valid:
                results.append("✅ Check digit validation: PASSED")
            else:
                results.append("❌ Check digit validation: FAILED")
                results.append(f"   Expected: {calculated_check_digit}, Got: {check_digit}")
            
            results.append("")
            if round_trip_valid:
                results.append("✅ EPC round-trip test: PASSED")
                results.append(f"   Test EPC: {round_trip_details.get('test_epc', 'N/A')}")
            else:
                results.append("❌ EPC round-trip test: FAILED")
                results.append(f"   Error: {round_trip_details.get('error', 'Unknown error')}")
            
            self.results_text.setPlainText("\n".join(results))
            
        except Exception as e:
            self.status_label.setText("❌ Validation Error")
            self.status_frame.setStyleSheet("background-color: #4a2c2c; border: 1px solid #8b0000;")
            self.results_text.setPlainText(f"Error during validation: {str(e)}")
    
    def test_epc_generation(self):
        """Generate a test EPC for the validated UPC"""
        upc = self.upc_input.text().strip()
        
        try:
            serial_str = self.test_serial_input.text().strip()
            if not serial_str.isdigit():
                QMessageBox.warning(self, "Invalid Serial", "Please enter a valid numeric serial number.")
                return
                
            serial_number = int(serial_str)
            epc_hex = generate_epc(upc, serial_number)
            
            # Test reverse conversion
            recovered_upc, recovered_serial = reverse_epc_to_upc_and_serial(epc_hex)
            
            result_text = f"EPC: {epc_hex}\n"
            result_text += f"Reverse UPC: {recovered_upc}\n"
            result_text += f"Reverse Serial: {recovered_serial}"
            
            if recovered_upc == upc and recovered_serial == serial_number:
                result_text += "\n✅ Round-trip successful"
            else:
                result_text += "\n❌ Round-trip failed"
            
            self.epc_result_label.setText(result_text)
            
        except Exception as e:
            self.epc_result_label.setText(f"Error generating EPC: {str(e)}")
    
    def clear_results(self, keep_status=True):
        """Clear all validation results"""
        if not keep_status:
            self.status_label.setText("Enter a UPC code to validate")
            self.status_frame.setStyleSheet("")
            
        self.format_valid_label.setText("—")
        self.check_digit_valid_label.setText("—")
        self.round_trip_label.setText("—")
        self.company_prefix_label.setText("—")
        self.item_reference_label.setText("—")
        self.check_digit_label.setText("—")
        self.epc_result_label.setText("—")
        self.results_text.clear()
        self.test_epc_btn.setEnabled(False) 