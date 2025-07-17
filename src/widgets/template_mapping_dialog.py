"""
Template Mapping Dialog
Dialog for managing Customer + Label Size to Template file mappings.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QFileDialog, QLabel, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit, QWidget
)
from PySide6.QtCore import Qt
from src.utils.template_mapping import get_template_manager
import src.config as config


class TemplateMappingDialog(QDialog):
    """Dialog for managing template mappings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Template Mappings")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        
        self.template_manager = get_template_manager()
        self.setup_ui()
        self.load_mappings()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Template Mappings")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # Reload button
        reload_btn = QPushButton("Reload from File")
        reload_btn.clicked.connect(self.reload_mappings)
        header_layout.addWidget(reload_btn)
        
        layout.addLayout(header_layout)
        
        # Info label
        info_label = QLabel("Map Customer + Label Size combinations to specific template files.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Customer", "Label Size", "Template File", "Actions"])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 120)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Mapping")
        add_btn.clicked.connect(self.add_mapping)
        button_layout.addWidget(add_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save to File")
        save_btn.clicked.connect(self.save_mappings)
        save_btn.setObjectName("saveButton")
        button_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_mappings(self):
        """Load mappings into the table."""
        self.table.setRowCount(0)
        
        mappings = self.template_manager.get_all_mappings()
        for customer, label_mappings in sorted(mappings.items()):
            for label_size, template_path in sorted(label_mappings.items()):
                self.add_mapping_row(customer, label_size, template_path)
    
    def add_mapping_row(self, customer: str, label_size: str, template_path: str):
        """Add a row to the mappings table."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Customer column
        customer_item = QTableWidgetItem(customer)
        customer_item.setFlags(customer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, customer_item)
        
        # Label size column
        label_item = QTableWidgetItem(label_size)
        label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 1, label_item)
        
        # Template path column
        template_item = QTableWidgetItem(template_path)
        template_item.setFlags(template_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        # Check if file exists
        if not os.path.exists(template_path):
            template_item.setForeground(Qt.GlobalColor.red)
            template_item.setToolTip("File not found!")
        else:
            template_item.setToolTip(template_path)
        
        self.table.setItem(row, 2, template_item)
        
        # Actions column - container widget with buttons
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda: self.edit_mapping(row))
        actions_layout.addWidget(edit_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_mapping(row))
        actions_layout.addWidget(remove_btn)
        
        self.table.setCellWidget(row, 3, actions_widget)
    
    def add_mapping(self):
        """Add a new mapping."""
        dialog = AddMappingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            customer, label_size, template_path = dialog.get_mapping()
            
            # Check if mapping already exists
            existing_template = self.template_manager.get_template(customer, label_size)
            if existing_template:
                reply = QMessageBox.question(
                    self,
                    "Mapping Exists",
                    f"A mapping already exists for {customer} - {label_size}.\n"
                    f"Current template: {existing_template}\n\n"
                    "Do you want to replace it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                
                # Remove the existing row from table
                for row in range(self.table.rowCount()):
                    if (self.table.item(row, 0).text() == customer and 
                        self.table.item(row, 1).text() == label_size):
                        self.table.removeRow(row)
                        break
            
            # Add to manager and table
            if self.template_manager.set_template(customer, label_size, template_path):
                self.add_mapping_row(customer, label_size, template_path)
    
    def edit_mapping(self, row: int):
        """Edit an existing mapping."""
        customer = self.table.item(row, 0).text()
        label_size = self.table.item(row, 1).text()
        current_template = self.table.item(row, 2).text()
        
        # Browse for new template file
        template_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select Template for {customer} - {label_size}",
            current_template,
            "BarTender Templates (*.btw);;All Files (*.*)"
        )
        
        if template_path:
            # Update manager and table
            if self.template_manager.set_template(customer, label_size, template_path):
                template_item = self.table.item(row, 2)
                template_item.setText(template_path)
                
                # Update color based on file existence
                if not os.path.exists(template_path):
                    template_item.setForeground(Qt.GlobalColor.red)
                    template_item.setToolTip("File not found!")
                else:
                    template_item.setForeground(self.palette().text().color())
                    template_item.setToolTip(template_path)
    
    def remove_mapping(self, row: int):
        """Remove a mapping."""
        customer = self.table.item(row, 0).text()
        label_size = self.table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Remove Mapping",
            f"Remove the template mapping for:\n{customer} - {label_size}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.template_manager.remove_template(customer, label_size):
                self.table.removeRow(row)
    
    def save_mappings(self):
        """Save mappings to file."""
        if self.template_manager.save_mappings():
            QMessageBox.information(self, "Success", "Template mappings saved successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save template mappings.")
    
    def reload_mappings(self):
        """Reload mappings from file."""
        reply = QMessageBox.question(
            self,
            "Reload Mappings",
            "This will discard any unsaved changes. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.template_manager.reload_mappings():
                self.load_mappings()
                QMessageBox.information(self, "Success", "Mappings reloaded from file.")
            else:
                QMessageBox.warning(self, "Warning", "Could not reload mappings.")


class AddMappingDialog(QDialog):
    """Dialog for adding a new template mapping."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Template Mapping")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Customer selection
        customer_layout = QHBoxLayout()
        customer_layout.addWidget(QLabel("Customer:"))
        
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        
        # Load customer list
        customers = config.read_txt_file(config.CUSTOMER_NAMES_FILE)
        self.customer_combo.addItems(customers)
        
        customer_layout.addWidget(self.customer_combo)
        layout.addLayout(customer_layout)
        
        # Label size selection
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Label Size:"))
        
        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        
        # Load label sizes
        label_sizes = config.read_txt_file(config.LABEL_SIZES_FILE)
        self.label_combo.addItems(label_sizes)
        
        label_layout.addWidget(self.label_combo)
        layout.addLayout(label_layout)
        
        # Template file selection
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template File:"))
        
        self.template_edit = QLineEdit()
        template_layout.addWidget(self.template_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_template)
        template_layout.addWidget(browse_btn)
        
        layout.addLayout(template_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.validate_and_accept)
        add_btn.setDefault(True)
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
    
    def browse_template(self):
        """Browse for a template file."""
        # Start in template base path if configured
        start_path = config.get_template_base_path()
        
        template_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template File",
            start_path,
            "BarTender Templates (*.btw);;All Files (*.*)"
        )
        
        if template_path:
            self.template_edit.setText(template_path)
    
    def validate_and_accept(self):
        """Validate inputs and accept dialog."""
        customer = self.customer_combo.currentText().strip()
        label_size = self.label_combo.currentText().strip()
        template_path = self.template_edit.text().strip()
        
        if not customer:
            QMessageBox.warning(self, "Invalid Input", "Please select or enter a customer.")
            return
        
        if not label_size:
            QMessageBox.warning(self, "Invalid Input", "Please select or enter a label size.")
            return
        
        if not template_path:
            QMessageBox.warning(self, "Invalid Input", "Please select a template file.")
            return
        
        if not os.path.exists(template_path):
            reply = QMessageBox.warning(
                self,
                "File Not Found",
                f"The template file does not exist:\n{template_path}\n\n"
                "Add mapping anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.accept()
    
    def get_mapping(self):
        """Get the mapping data."""
        return (
            self.customer_combo.currentText().strip(),
            self.label_combo.currentText().strip(),
            self.template_edit.text().strip()
        ) 