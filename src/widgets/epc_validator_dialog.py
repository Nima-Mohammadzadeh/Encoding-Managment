"""
EPC Validator Dialog

This dialog provides comprehensive EPC validation including:
- EPC format validation
- Reverse conversion to UPC and serial number
- Binary breakdown of EPC components
- Round-trip validation testing
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
    reverse_epc_to_upc_and_serial, generate_epc, hex_to_bin, bin_to_dec, validate_upc
)


class EPCValidatorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EPC Validator")
        self.setModal(True)
        self.setMinimumSize(700, 650)  # Match UPC validator size
        self.resize(750, 700)  # Match UPC validator initial size
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the EPC validator UI"""
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
        
        title_label = QLabel("EPC Code Validator")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        subtitle_label = QLabel("Validate and analyze EPC codes with detailed breakdown")
        subtitle_label.setStyleSheet("color: #888888;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        
        content_layout.addLayout(header_layout)
        
        # Input section
        input_group = QGroupBox("EPC Input")
        input_layout = QFormLayout(input_group)
        input_layout.setLabelAlignment(Qt.AlignRight)
        
        self.epc_input = QLineEdit()
        self.epc_input.setPlaceholderText("Enter EPC hex code (24 characters, e.g., 3034257BF7194E4000001F40)")
        self.epc_input.textChanged.connect(self.on_epc_changed)
        
        self.validate_btn = QPushButton("Validate EPC")
        self.validate_btn.clicked.connect(self.validate_epc)
        self.validate_btn.setEnabled(False)
        
        input_layout.addRow("EPC Code:", self.epc_input)
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
        
        self.status_label = QLabel("Enter an EPC code to validate")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(12)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        
        status_layout.addWidget(self.status_label)
        results_layout.addWidget(self.status_frame)
        
        # Extracted data
        extracted_layout = QGridLayout()
        extracted_layout.setSpacing(8)
        extracted_layout.setColumnStretch(1, 1)  # Make second column stretch
        
        extracted_layout.addWidget(QLabel("Format Valid:"), 0, 0)
        self.format_valid_label = QLabel("—")
        extracted_layout.addWidget(self.format_valid_label, 0, 1)
        
        extracted_layout.addWidget(QLabel("Extracted UPC:"), 1, 0)
        self.extracted_upc_label = QLabel("—")
        extracted_layout.addWidget(self.extracted_upc_label, 1, 1)
        
        extracted_layout.addWidget(QLabel("Serial Number:"), 2, 0)
        self.serial_number_label = QLabel("—")
        extracted_layout.addWidget(self.serial_number_label, 2, 1)
        
        extracted_layout.addWidget(QLabel("Round-trip Test:"), 3, 0)
        self.round_trip_label = QLabel("—")
        extracted_layout.addWidget(self.round_trip_label, 3, 1)
        
        results_layout.addLayout(extracted_layout)
        
        # Binary breakdown section
        binary_group = QGroupBox("Binary Breakdown")
        binary_layout = QGridLayout(binary_group)
        binary_layout.setSpacing(8)
        binary_layout.setColumnStretch(1, 1)  # Make second column stretch
        
        # Create labels for each EPC component
        binary_layout.addWidget(QLabel("Header (8 bits):"), 0, 0)
        self.header_label = QLabel("—")
        self.header_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 2px;")
        binary_layout.addWidget(self.header_label, 0, 1)
        
        binary_layout.addWidget(QLabel("Filter (3 bits):"), 1, 0)
        self.filter_label = QLabel("—")
        self.filter_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 2px;")
        binary_layout.addWidget(self.filter_label, 1, 1)
        
        binary_layout.addWidget(QLabel("Partition (3 bits):"), 2, 0)
        self.partition_label = QLabel("—")
        self.partition_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 2px;")
        binary_layout.addWidget(self.partition_label, 2, 1)
        
        binary_layout.addWidget(QLabel("Company Prefix (24 bits):"), 3, 0)
        self.company_prefix_binary_label = QLabel("—")
        self.company_prefix_binary_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 2px;")
        binary_layout.addWidget(self.company_prefix_binary_label, 3, 1)
        
        binary_layout.addWidget(QLabel("Item Reference (20 bits):"), 4, 0)
        self.item_reference_binary_label = QLabel("—")
        self.item_reference_binary_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 2px;")
        binary_layout.addWidget(self.item_reference_binary_label, 4, 1)
        
        binary_layout.addWidget(QLabel("Serial Number (38 bits):"), 5, 0)
        self.serial_binary_label = QLabel("—")
        self.serial_binary_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 2px;")
        binary_layout.addWidget(self.serial_binary_label, 5, 1)
        
        results_layout.addWidget(binary_group)
        
        # Detailed results text area
        self.results_text = QTextEdit()
        self.results_text.setMinimumHeight(150)
        self.results_text.setMaximumHeight(300)  # Increased from 120 to 300
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Detailed validation results will appear here...")
        
        results_layout.addWidget(QLabel("Detailed Analysis:"))
        results_layout.addWidget(self.results_text)
        
        content_layout.addWidget(results_group)
        
        # Round-trip Test section
        test_group = QGroupBox("Round-trip Validation Test")
        test_layout = QFormLayout(test_group)
        test_layout.setLabelAlignment(Qt.AlignRight)
        
        self.test_btn = QPushButton("Test Round-trip Conversion")
        self.test_btn.clicked.connect(self.test_round_trip)
        self.test_btn.setEnabled(False)
        
        self.test_result_label = QLabel("—")
        self.test_result_label.setWordWrap(True)
        self.test_result_label.setMinimumHeight(80)
        self.test_result_label.setAlignment(Qt.AlignTop)
        self.test_result_label.setStyleSheet("font-family: monospace; background: #2b2b2b; padding: 8px; border: 1px solid #555;")
        
        test_layout.addRow("", self.test_btn)
        test_layout.addRow("Test Result:", self.test_result_label)
        
        content_layout.addWidget(test_group)
        
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
        
    def on_epc_changed(self):
        """Handle EPC input changes"""
        epc = self.epc_input.text().strip().upper()
        
        # Basic format check: should be 24 hex characters
        is_valid_format = len(epc) == 24 and all(c in '0123456789ABCDEF' for c in epc)
        
        self.validate_btn.setEnabled(is_valid_format)
        self.test_btn.setEnabled(False)
        
        if len(epc) < 24:
            self.clear_results()
        
    def validate_epc(self):
        """Validate the entered EPC code"""
        epc = self.epc_input.text().strip().upper()
        
        if not epc:
            return
            
        # Clear previous results
        self.clear_results(keep_status=False)
        
        try:
            # Basic format validation
            format_valid = len(epc) == 24 and all(c in '0123456789ABCDEF' for c in epc)
            self.format_valid_label.setText("✅ Valid" if format_valid else "❌ Invalid")
            
            if not format_valid:
                self.status_label.setText("❌ Invalid EPC Format")
                self.status_frame.setStyleSheet("background-color: #4a2c2c; border: 1px solid #8b0000;")
                self.results_text.setPlainText("EPC must be exactly 24 hexadecimal characters.")
                return
            
            # Convert to binary for analysis
            try:
                epc_binary = hex_to_bin(epc)
                if len(epc_binary) != 96:
                    raise ValueError(f"Expected 96 bits, got {len(epc_binary)}")
            except Exception as e:
                self.status_label.setText("❌ Binary Conversion Failed")
                self.status_frame.setStyleSheet("background-color: #4a2c2c; border: 1px solid #8b0000;")
                self.results_text.setPlainText(f"Failed to convert EPC to binary: {str(e)}")
                return
            
            # Extract EPC components
            header = epc_binary[0:8]
            filter_value = epc_binary[8:11]
            partition = epc_binary[11:14]
            gs1_binary = epc_binary[14:38]
            item_reference_binary = epc_binary[38:58]
            serial_binary = epc_binary[58:96]
            
            # Update binary breakdown display
            self.header_label.setText(f"{header} ({bin_to_dec(header)})")
            self.filter_label.setText(f"{filter_value} ({bin_to_dec(filter_value)})")
            self.partition_label.setText(f"{partition} ({bin_to_dec(partition)})")
            self.company_prefix_binary_label.setText(f"{gs1_binary} ({bin_to_dec(gs1_binary)})")
            self.item_reference_binary_label.setText(f"{item_reference_binary} ({bin_to_dec(item_reference_binary)})")
            self.serial_binary_label.setText(f"{serial_binary} ({bin_to_dec(serial_binary)})")
            
            # Attempt reverse conversion
            extracted_upc, extracted_serial = reverse_epc_to_upc_and_serial(epc)
            
            if extracted_upc and extracted_serial is not None:
                self.extracted_upc_label.setText(extracted_upc)
                self.serial_number_label.setText(f"{extracted_serial:,}")
                
                # Validate extracted UPC
                upc_valid = validate_upc(extracted_upc)
                
                # Test round-trip conversion
                if upc_valid:
                    test_epc = generate_epc(extracted_upc, extracted_serial)
                    round_trip_valid = test_epc.upper() == epc.upper()
                    self.round_trip_label.setText("✅ Passed" if round_trip_valid else "❌ Failed")
                    self.test_btn.setEnabled(True)
                else:
                    self.round_trip_label.setText("❌ Invalid UPC")
                
                # Overall status
                overall_valid = format_valid and extracted_upc and upc_valid
                
                if overall_valid:
                    self.status_label.setText("✅ EPC is Valid")
                    self.status_frame.setStyleSheet("background-color: #2c4a2c; border: 1px solid #008000;")
                else:
                    self.status_label.setText("⚠️ EPC has Issues")
                    self.status_frame.setStyleSheet("background-color: #4a4a2c; border: 1px solid #ffaa00;")
                
            else:
                self.extracted_upc_label.setText("❌ Extraction Failed")
                self.serial_number_label.setText("❌ Extraction Failed")
                self.round_trip_label.setText("❌ Cannot Test")
                
                self.status_label.setText("❌ Invalid EPC Structure")
                self.status_frame.setStyleSheet("background-color: #4a2c2c; border: 1px solid #8b0000;")
            
            # Detailed results
            results = []
            results.append(f"EPC Analysis for: {epc}")
            results.append("=" * 50)
            results.append(f"Binary: {epc_binary}")
            results.append("")
            results.append("Component Breakdown:")
            results.append(f"  Header:         {header} (decimal: {bin_to_dec(header)})")
            results.append(f"  Filter:         {filter_value} (decimal: {bin_to_dec(filter_value)})")
            results.append(f"  Partition:      {partition} (decimal: {bin_to_dec(partition)})")
            results.append(f"  Company Prefix: {gs1_binary} (decimal: {bin_to_dec(gs1_binary)})")
            results.append(f"  Item Reference: {item_reference_binary} (decimal: {bin_to_dec(item_reference_binary)})")
            results.append(f"  Serial Number:  {serial_binary} (decimal: {bin_to_dec(serial_binary)})")
            results.append("")
            
            # Expected values validation
            expected_header = "00110000"
            expected_filter = "001"
            expected_partition = "101"
            
            if header == expected_header:
                results.append("✅ Header matches expected value (00110000)")
            else:
                results.append(f"❌ Header mismatch: expected {expected_header}, got {header}")
                
            if filter_value == expected_filter:
                results.append("✅ Filter matches expected value (001)")
            else:
                results.append(f"❌ Filter mismatch: expected {expected_filter}, got {filter_value}")
                
            if partition == expected_partition:
                results.append("✅ Partition matches expected value (101)")
            else:
                results.append(f"❌ Partition mismatch: expected {expected_partition}, got {partition}")
            
            results.append("")
            if extracted_upc:
                results.append(f"✅ Extracted UPC: {extracted_upc}")
                results.append(f"✅ Extracted Serial: {extracted_serial:,}")
            else:
                results.append("❌ Failed to extract UPC and serial number")
            
            self.results_text.setPlainText("\n".join(results))
            
        except Exception as e:
            self.status_label.setText("❌ Validation Error")
            self.status_frame.setStyleSheet("background-color: #4a2c2c; border: 1px solid #8b0000;")
            self.results_text.setPlainText(f"Error during validation: {str(e)}")
    
    def test_round_trip(self):
        """Test round-trip conversion: EPC -> UPC/Serial -> EPC"""
        epc = self.epc_input.text().strip().upper()
        
        try:
            # Extract UPC and serial from EPC
            extracted_upc, extracted_serial = reverse_epc_to_upc_and_serial(epc)
            
            if not extracted_upc or extracted_serial is None:
                self.test_result_label.setText("❌ Cannot perform round-trip test - extraction failed")
                return
            
            # Generate EPC from extracted data
            regenerated_epc = generate_epc(extracted_upc, extracted_serial)
            
            # Compare original and regenerated EPCs
            if regenerated_epc.upper() == epc.upper():
                result_text = f"✅ Round-trip SUCCESSFUL\n"
                result_text += f"Original EPC:  {epc}\n"
                result_text += f"Regenerated:   {regenerated_epc}\n"
                result_text += f"UPC: {extracted_upc}, Serial: {extracted_serial:,}"
            else:
                result_text = f"❌ Round-trip FAILED\n"
                result_text += f"Original EPC:  {epc}\n"
                result_text += f"Regenerated:   {regenerated_epc}\n"
                result_text += f"UPC: {extracted_upc}, Serial: {extracted_serial:,}"
            
            self.test_result_label.setText(result_text)
            
        except Exception as e:
            self.test_result_label.setText(f"❌ Round-trip test error: {str(e)}")
    
    def clear_results(self, keep_status=True):
        """Clear all validation results"""
        if not keep_status:
            self.status_label.setText("Enter an EPC code to validate")
            self.status_frame.setStyleSheet("")
            
        self.format_valid_label.setText("—")
        self.extracted_upc_label.setText("—")
        self.serial_number_label.setText("—")
        self.round_trip_label.setText("—")
        
        # Clear binary breakdown
        self.header_label.setText("—")
        self.filter_label.setText("—")
        self.partition_label.setText("—")
        self.company_prefix_binary_label.setText("—")
        self.item_reference_binary_label.setText("—")
        self.serial_binary_label.setText("—")
        
        self.test_result_label.setText("—")
        self.results_text.clear()
        self.test_btn.setEnabled(False) 