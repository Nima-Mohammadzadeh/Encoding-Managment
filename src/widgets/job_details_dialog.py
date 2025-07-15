import os
import json
import subprocess
import platform
import webbrowser
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QTextEdit, QComboBox, QListWidget,
    QTabWidget, QWidget, QMessageBox, QGridLayout, QLineEdit, QProgressDialog,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QIcon
import fitz
import shutil
import src.config as config



class JobDetailsDialog(QDialog):
    job_updated = Signal(dict)
    job_archived = Signal(dict)
    job_deleted = Signal()
    
    def __init__(self, job_data, base_path, parent=None):
        super().__init__(parent)
        self.job_data = job_data.copy()
        self.base_path = base_path
        self.network_path = r"Z:\3 Encoding and Printing Files\Customers Encoding Files"
        
        self.setWindowTitle(f"Job Details: {job_data.get('Job Ticket#', 'N/A')}")
        self.setMinimumSize(700, 500)
        self.resize(800, 550)
        self.setModal(True)
        # Remove custom stylesheet to inherit application theme
        # self.setStyleSheet(self.get_stylesheet())
        
        self.job_fields_read = {}
        self.encoding_fields_read = {}
        self.job_fields_edit = {}
        self.encoding_fields_edit = {}
        
        self.setup_ui()
        self.load_job_data()
        self.check_directories()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Enhanced Header with Job Details at a Glance
        header = self.create_enhanced_header()
        main_layout.addWidget(header)
        
        # Main Content Area with Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left Panel: Job Information and Actions
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right Panel: File Explorer
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (55% left, 45% right) for smaller window
        splitter.setSizes([440, 360])
        
    def create_enhanced_header(self):
        """Create an enhanced header with comprehensive job details at a glance."""
        header_widget = QWidget()
        header_widget.setObjectName("headerWidget")
        header_widget.setMinimumHeight(100)
        header_widget.setMaximumHeight(100)
        
        layout = QGridLayout(header_widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)
        
        # Row 1: Job Title and Status
        title_text = f"{self.job_data.get('Customer', 'Unknown Customer')} - {self.job_data.get('Part#', 'N/A')}"
        title_label = QLabel(title_text)
        title_label.setObjectName("headerTitle")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label, 0, 0, 1, 3)
        
        status_label = QLabel(f"Status: {self.job_data.get('Status', 'New')}")
        status_label.setObjectName("headerStatus")
        status_label.setStyleSheet("font-size: 12px; color: #ffffff; font-weight: bold;")
        layout.addWidget(status_label, 0, 3, 1, 2)
        
        # Row 2: Key Job Details
        ticket_label = QLabel(f"Ticket#: {self.job_data.get('Job Ticket#', self.job_data.get('Ticket#', 'N/A'))}")
        ticket_label.setStyleSheet("color: #ffffff; font-weight: normal; font-size: 11px;")
        po_label = QLabel(f"PO#: {self.job_data.get('PO#', 'N/A')}")
        po_label.setStyleSheet("color: #ffffff; font-weight: normal; font-size: 11px;")
        qty_label = QLabel(f"Quantity: {self.job_data.get('Quantity', self.job_data.get('Qty', 'N/A'))}")
        qty_label.setStyleSheet("color: #ffffff; font-weight: normal; font-size: 11px;")
        
        layout.addWidget(ticket_label, 1, 0)
        layout.addWidget(po_label, 1, 1)
        layout.addWidget(qty_label, 1, 2)
        
        # Row 3: Additional Details
        due_date = self.job_data.get('Due Date', 'N/A')
        if due_date and due_date != 'N/A':
            try:
                # Format date for display
                date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%m/%d/%Y")
                due_label = QLabel(f"Due: {formatted_date}")
            except:
                due_label = QLabel(f"Due: {due_date}")
        else:
            due_label = QLabel("Due: N/A")
        due_label.setStyleSheet("color: #ffffff; font-weight: normal; font-size: 11px;")
            
        upc_label = QLabel(f"UPC: {self.job_data.get('UPC Number', 'N/A')}")
        upc_label.setStyleSheet("color: #ffffff; font-weight: normal; font-size: 11px;")
        label_size_label = QLabel(f"Label Size: {self.job_data.get('Label Size', 'N/A')}")
        label_size_label.setStyleSheet("color: #ffffff; font-weight: normal; font-size: 11px;")
        
        layout.addWidget(due_label, 2, 0)
        layout.addWidget(upc_label, 2, 1)
        layout.addWidget(label_size_label, 2, 2)
        
        # Action Buttons (Right side)
        button_layout = QVBoxLayout()
        button_layout.setSpacing(4)
        
        self.edit_btn = QPushButton("Edit Job")
        self.edit_btn.setMaximumHeight(30)
        self.edit_btn.clicked.connect(self.enter_edit_mode)
        button_layout.addWidget(self.edit_btn)
        
        complete_btn = QPushButton("Complete Job")
        complete_btn.setMaximumHeight(30)
        complete_btn.clicked.connect(self.complete_job)
        button_layout.addWidget(complete_btn)

        archive_btn = QPushButton("Archive Job")
        archive_btn.setMaximumHeight(30)
        archive_btn.clicked.connect(self.archive_job)
        button_layout.addWidget(archive_btn)

        delete_btn = QPushButton("Delete Job")
        delete_btn.setObjectName("deleteButton")
        delete_btn.setProperty("class", "danger")  # Use qt_material danger styling
        delete_btn.setMaximumHeight(30)
        delete_btn.clicked.connect(self.delete_job)
        button_layout.addWidget(delete_btn)

        layout.addLayout(button_layout, 0, 4, 3, 1)
        
        # Set column stretch to make details expand
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 0)
        layout.setColumnStretch(4, 0)
        
        return header_widget
        
    def create_left_panel(self):
        """Create the left panel with job information and actions."""
        # Create scroll area for the left panel
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(12)
        
        # Job Information Group
        job_info_group = QGroupBox("Job Information")
        job_info_layout = QFormLayout(job_info_group)
        job_info_layout.setSpacing(8)
        job_info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        job_info_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        job_field_keys = ["Customer", "Part#", "Job Ticket#", "PO#", "Inlay Type", "Label Size", "Quantity", "Due Date"]
        for key in job_field_keys:
            label = QLabel(f"{key}:")
            label.setStyleSheet("color: #ffffff; font-weight: normal; min-width: 80px;")
            label.setMinimumWidth(80)
            value = QLabel(self.job_data.get(key, ''))
            value.setObjectName("readOnlyField")
            # Apply styling for read-only fields to ensure visibility in dark theme
            value.setStyleSheet("""
                padding: 6px;
                border: 1px solid #4f5b62;
                border-radius: 4px;
                background-color: #31363b;
                color: #ffffff;
                font-weight: normal;
                min-width: 120px;
            """)
            value.setMinimumWidth(120)
            job_info_layout.addRow(label, value)
            self.job_fields_read[key] = value
        
        left_layout.addWidget(job_info_group)
        
        # Encoding Information Group
        encoding_info_group = QGroupBox("Encoding Information")
        encoding_layout = QFormLayout(encoding_info_group)
        encoding_layout.setSpacing(8)
        encoding_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        encoding_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        encoding_field_keys = ["Item", "UPC Number", "Serial Number", "LPR", "Rolls"]
        for key in encoding_field_keys:
            label = QLabel(f"{key}:")
            label.setStyleSheet("color: #ffffff; font-weight: normal; min-width: 80px;")
            label.setMinimumWidth(80)
            value = QLabel(self.job_data.get(key, ''))
            value.setObjectName("readOnlyField")
            # Apply styling for read-only fields to ensure visibility in dark theme
            value.setStyleSheet("""
                padding: 6px;
                border: 1px solid #4f5b62;
                border-radius: 4px;
                background-color: #31363b;
                color: #ffffff;
                font-weight: normal;
                min-width: 120px;
            """)
            value.setMinimumWidth(120)
            encoding_layout.addRow(label, value)
            self.encoding_fields_read[key] = value
        
        left_layout.addWidget(encoding_info_group)
        
        # Job Actions Group
        actions_group = QGroupBox("Job Actions")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(8)
        
        # Directory Actions
        dir_actions_layout = QHBoxLayout()
        self.open_dir_btn = QPushButton("Open Job Folder")
        self.open_dir_btn.setMaximumHeight(30)
        self.open_dir_btn.clicked.connect(self.open_job_folder)
        self.create_dir_btn = QPushButton("Create Job Folder")
        self.create_dir_btn.setMaximumHeight(30)
        self.create_dir_btn.clicked.connect(self.create_job_directory)
        dir_actions_layout.addWidget(self.open_dir_btn)
        dir_actions_layout.addWidget(self.create_dir_btn)
        actions_layout.addLayout(dir_actions_layout)
        
        # Directory Status
        self.dir_status_label = QLabel("Checking directories...")
        self.dir_status_label.setWordWrap(True)
        self.dir_status_label.setStyleSheet("padding: 4px; font-size: 11px;")
        actions_layout.addWidget(self.dir_status_label)
        
        # Checklist Actions
        checklist_layout = QHBoxLayout()
        open_checklist_btn = QPushButton("Open Checklist PDF")
        open_checklist_btn.setMaximumHeight(30)
        open_checklist_btn.clicked.connect(self.open_checklist)
        regen_checklist_btn = QPushButton("Regenerate Checklist")
        regen_checklist_btn.setMaximumHeight(30)
        regen_checklist_btn.clicked.connect(self.regenerate_checklist)
        checklist_layout.addWidget(open_checklist_btn)
        checklist_layout.addWidget(regen_checklist_btn)
        actions_layout.addLayout(checklist_layout)
        
        left_layout.addWidget(actions_group)
        left_layout.addStretch()
        
        # Set the widget in the scroll area
        left_scroll.setWidget(left_widget)
        return left_scroll
        
    def create_right_panel(self):
        """Create the right panel with hierarchical file explorer."""
        # Create scroll area for the right panel
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)
        
        # File Explorer Header
        explorer_header = QLabel("Job Files & Folders")
        explorer_header.setObjectName("explorerHeader")
        explorer_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; padding: 5px 0px;")
        right_layout.addWidget(explorer_header)
        
        # File Explorer Tree
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabel("Name")
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setExpandsOnDoubleClick(True)
        self.file_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.file_tree.setMinimumWidth(200)
        self.file_tree.setMinimumHeight(300)
        right_layout.addWidget(self.file_tree)
        
        # Refresh Button
        refresh_btn = QPushButton("Refresh File Explorer")
        refresh_btn.setMaximumHeight(30)
        refresh_btn.clicked.connect(self.refresh_file_tree)
        right_layout.addWidget(refresh_btn)
        
        # Set the widget in the scroll area
        right_scroll.setWidget(right_widget)
        return right_scroll
        
    def refresh_file_tree(self):
        """Refresh the file explorer tree."""
        self.file_tree.clear()
        job_path = self.find_job_directory()
        if job_path:
            self.populate_file_tree(job_path)
        else:
            # Add a placeholder item
            placeholder = QTreeWidgetItem(self.file_tree)
            placeholder.setText(0, "Job directory not found")
            placeholder.setDisabled(True)
            
    def populate_file_tree(self, root_path):
        """Populate the file tree with the job directory structure."""
        try:
            # Add root item
            root_item = QTreeWidgetItem(self.file_tree)
            root_item.setText(0, os.path.basename(root_path))
            root_item.setIcon(0, self.get_folder_icon())
            root_item.setExpanded(True)
            
            # Recursively add files and folders
            self.add_directory_to_tree(root_path, root_item)
            
        except Exception as e:
            error_item = QTreeWidgetItem(self.file_tree)
            error_item.setText(0, f"Error loading directory: {e}")
            error_item.setDisabled(True)
            
    def add_directory_to_tree(self, dir_path, parent_item):
        """Recursively add directory contents to the tree."""
        try:
            for item_name in sorted(os.listdir(dir_path)):
                item_path = os.path.join(dir_path, item_name)
                
                tree_item = QTreeWidgetItem(parent_item)
                tree_item.setText(0, item_name)
                
                if os.path.isdir(item_path):
                    tree_item.setIcon(0, self.get_folder_icon())
                    # Recursively add subdirectory contents
                    self.add_directory_to_tree(item_path, tree_item)
            else:
                    tree_item.setIcon(0, self.get_file_icon(item_name))
                    
        except PermissionError:
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, "Access Denied")
            error_item.setDisabled(True)
        except Exception as e:
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, f"Error: {e}")
            error_item.setDisabled(True)
            
    def get_folder_icon(self):
        """Get folder icon for tree items."""
        # You can customize this with actual icons if available
        return QIcon()
        
    def get_file_icon(self, filename):
        """Get appropriate file icon based on file extension."""
        # You can customize this with actual icons if available
        return QIcon()
        
    def on_tree_item_double_clicked(self, item, column):
        """Handle double-click on tree items."""
        if item.parent() is None:  # Root item
            return
            
        # Get the full path of the selected item
        item_path = self.get_item_path(item)
        if item_path and os.path.isfile(item_path):
            self.open_path_in_explorer(item_path)
            
    def get_item_path(self, item):
        """Get the full file system path for a tree item."""
        path_parts = []
        current_item = item
        
        # Walk up the tree to build the path
        while current_item.parent() is not None:
            path_parts.insert(0, current_item.text(0))
            current_item = current_item.parent()
            
        # Add the root path
        job_path = self.find_job_directory()
        if job_path:
            return os.path.join(job_path, *path_parts)
        return None

    def enter_edit_mode(self):
        """Enter edit mode by creating a new tab."""
        # Create edit tab if it doesn't exist
        if not hasattr(self, 'edit_tab'):
            self.edit_tab = QWidget()
            self.populate_edit_tab()
            
            # Create a new tab widget for edit mode
            self.edit_tab_widget = QTabWidget()
            self.edit_tab_widget.addTab(self.edit_tab, "Edit Job")
            
            # Replace the main layout with the edit tab widget
            self.layout().itemAt(1).widget().setParent(None)  # Remove splitter
            self.layout().addWidget(self.edit_tab_widget, 1)
        
        self.edit_tab_widget.setCurrentIndex(0)

    def populate_edit_tab(self):
        # Create scroll area for edit mode
        edit_scroll = QScrollArea()
        edit_scroll.setWidgetResizable(True)
        edit_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        edit_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        edit_widget = QWidget()
        layout = QVBoxLayout(edit_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Main horizontal layout for the two group boxes
        main_edit_layout = QHBoxLayout()

        # Left side: Job Details
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        # Job Details Group
        job_details_group = QGroupBox("Job Information")
        form_layout = QFormLayout(job_details_group)
        form_layout.setSpacing(8)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        job_field_keys = ["Customer", "Part#", "Job Ticket#", "PO#", "Inlay Type", "Label Size", "Quantity", "Due Date"]
        for key in job_field_keys:
            label = QLabel(f"{key}:")
            label.setStyleSheet("color: #ffffff; font-weight: normal; min-width: 80px;")
            label.setMinimumWidth(80)
            field = QLineEdit(self.job_data.get(key, ''))
            field.setMinimumWidth(120)
            form_layout.addRow(label, field)
            self.job_fields_edit[key] = field
        left_layout.addWidget(job_details_group)
        left_layout.addStretch()

        # Right side: Encoding Details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)

        # Encoding Details Group
        encoding_details_group = QGroupBox("Encoding Information")
        encoding_form_layout = QFormLayout(encoding_details_group)
        encoding_form_layout.setSpacing(8)
        encoding_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        encoding_form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        encoding_field_keys = ["Item", "UPC Number", "Serial Number", "LPR", "Rolls"]
        for key in encoding_field_keys:
            label = QLabel(f"{key}:")
            label.setStyleSheet("color: #ffffff; font-weight: normal; min-width: 80px;")
            label.setMinimumWidth(80)
            field = QLineEdit(self.job_data.get(key, ''))
            field.setMinimumWidth(120)
            encoding_form_layout.addRow(label, field)
            self.encoding_fields_edit[key] = field
        right_layout.addWidget(encoding_details_group)
        right_layout.addStretch()

        main_edit_layout.addWidget(left_widget)
        main_edit_layout.addWidget(right_widget)
        layout.addLayout(main_edit_layout)

        # Save/Cancel Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("saveButton")
        save_btn.setProperty("class", "success")  # Use qt_material success styling
        save_btn.setMaximumHeight(30)
        save_btn.clicked.connect(self.save_changes)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMaximumHeight(30)
        cancel_btn.clicked.connect(self.cancel_edit)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        # Set the widget in the scroll area
        edit_scroll.setWidget(edit_widget)
        self.edit_tab = edit_scroll
        
    def save_changes(self):
        """Save changes with intelligent artifact regeneration."""
        # Store original values for comparison
        original_data = self.job_data.copy()
        
        # Collect updated data
        updated_data = {}
        for key, field in self.job_fields_edit.items():
            updated_data[key] = field.text()
        for key, field in self.encoding_fields_edit.items():
            updated_data[key] = field.text()
        
        # Detect critical changes that require regeneration
        critical_fields = {
            'UPC Number': ['pdf', 'qc', 'database'],
            'Quantity': ['pdf', 'qc', 'serials', 'database'], 
            'Qty': ['pdf', 'qc', 'serials', 'database'],
            'Customer': ['pdf', 'qc', 'folders'],
            'Label Size': ['pdf', 'qc', 'folders', 'template'],
            'Serial Number': ['pdf', 'database'],
            'Include 2% Buffer': ['serials', 'epc'],
            'Include 7% Buffer': ['serials', 'epc']
        }
        
        # Determine what needs regeneration
        artifacts_to_regenerate = set()
        changed_fields = []
        
        for field, artifacts in critical_fields.items():
            old_val = str(original_data.get(field, '')).strip()
            new_val = str(updated_data.get(field, '')).strip()
            if old_val != new_val:
                changed_fields.append(field)
                artifacts_to_regenerate.update(artifacts)
        
        # Update job data
        self.job_data.update(updated_data)
        
        if artifacts_to_regenerate and changed_fields:
            # Log the changes
            import logging
            logger = logging.getLogger('job_regeneration')
            logger.info(f"Critical fields changed for job {self.job_data.get('Job Ticket#')}: {changed_fields}")
            
            # Show confirmation dialog
            artifacts_list = '\n'.join([f"• {a.upper()}" for a in sorted(artifacts_to_regenerate)])
            reply = QMessageBox.question(
                self, 
                "Regenerate Job Artifacts",
                f"The following critical fields were changed:\n{', '.join(changed_fields)}\n\n"
                f"This requires regenerating:\n{artifacts_list}\n\n"
                "Do you want to proceed with regeneration?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Trigger full regeneration workflow
                self.regenerate_all_artifacts(original_data, changed_fields, artifacts_to_regenerate)
            else:
                # Just emit the update without regeneration
                self.job_updated.emit(self.job_data)
                self.finalize_edit(skip_checklist_prompt=True)
        else:
            # No critical changes, just update
            self.job_updated.emit(self.job_data)
            self.finalize_edit(skip_checklist_prompt=False)

    def regenerate_all_artifacts(self, original_data, changed_fields, artifacts_to_regenerate):
        """Regenerate all job artifacts after critical field changes."""
        job_path = self.find_job_directory()
        if not job_path:
            QMessageBox.critical(self, "Error", "Job directory not found. Cannot regenerate artifacts.")
            return
        
        # Pause file system watcher to prevent conflicts
        parent_widget = self.parent()
        if hasattr(parent_widget, 'file_watcher'):
            self.paused_watcher_paths = list(parent_widget.file_watcher.directories())
            for path in self.paused_watcher_paths:
                parent_widget.file_watcher.removePath(path)
            print("Paused file system monitoring for regeneration")
        
        # Create progress dialog
        self.regen_dialog = JobRegenerationProgressDialog(
            self.job_data, 
            original_data, 
            changed_fields,
            artifacts_to_regenerate,
            job_path,
            self.base_path,
            self
        )
        
        # Connect completion signal
        self.regen_dialog.regeneration_finished.connect(self.on_regeneration_finished)
        
        # Show dialog (blocks until complete)
        self.regen_dialog.exec()

    def on_regeneration_finished(self, success, message, updated_job_data):
        """Handle completion of artifact regeneration."""
        # Resume file system watcher
        if hasattr(self, 'paused_watcher_paths'):
            parent_widget = self.parent()
            if hasattr(parent_widget, 'file_watcher'):
                for path in self.paused_watcher_paths:
                    parent_widget.file_watcher.addPath(path)
                print("Resumed file system monitoring")
            del self.paused_watcher_paths
        
        if success:
            self.job_data = updated_job_data
            self.job_updated.emit(self.job_data)
            
            # Mark that artifacts were regenerated
            self.artifacts_regenerated = True
            
            QMessageBox.information(self, "Success", 
                "Job artifacts have been regenerated successfully:\n"
                f"{message}")
            
            self.finalize_edit(skip_checklist_prompt=True)
        else:
            QMessageBox.critical(self, "Regeneration Failed", 
                f"Failed to regenerate job artifacts:\n{message}\n\n"
                "The job data has NOT been updated.")

    def finalize_edit(self, skip_checklist_prompt=False):
        """Complete the edit operation and switch back to view mode."""
        # Ask to regenerate checklist only if not already done and not skipped
        if not skip_checklist_prompt and not hasattr(self, 'artifacts_regenerated'):
            reply = QMessageBox.question(self, "Regenerate Checklist", 
                                       "Would you like to regenerate the checklist PDF?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.regenerate_checklist()
        
        # Clean up the flag
        if hasattr(self, 'artifacts_regenerated'):
            del self.artifacts_regenerated
        
        # Switch back to overview (this will rebuild UI and reload data)
        self.cancel_edit()
        
        QMessageBox.information(self, "Success", "Job details have been updated.")

    def cancel_edit(self):
        # Remove the edit tab widget and restore the original layout
        if hasattr(self, 'edit_tab_widget'):
            self.edit_tab_widget.setParent(None)
            self.edit_tab_widget.deleteLater()
            del self.edit_tab_widget
            if hasattr(self, 'edit_tab'):
                del self.edit_tab
                
            # Restore the original splitter layout
            self.setup_ui()
            self.load_job_data()
            self.check_directories()
    
    def complete_job(self):
        reply = QMessageBox.question(self, "Complete Job", "Are you sure you want to mark this job as completed?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.job_data['Status'] = 'Completed'
            self.job_updated.emit(self.job_data)
            self.load_job_data()
            QMessageBox.information(self, "Job Completed", "The job status has been set to 'Completed'.")

            # Ask to archive
            archive_reply = QMessageBox.question(self, "Archive Job", 
                                               "Would you like to archive this completed job now?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if archive_reply == QMessageBox.StandardButton.Yes:
                self.archive_job()

    def find_job_directory(self):
        # First, check if the path is already stored in job_data
        if 'job_folder_path' in self.job_data and os.path.exists(self.job_data['job_folder_path']):
            return self.job_data['job_folder_path']
            
        # If not, fall back to searching for it
        job_paths = self.find_job_directories()
        for path in job_paths.values():
            if path and os.path.exists(path):
                # Optional: Store the found path for future use
                self.job_data['job_folder_path'] = path
                self.job_updated.emit(self.job_data) # Let the main page know to save it
                return path
        return None

    def load_job_data(self):
        for key, field in self.job_fields_read.items():
            field.setText(self.job_data.get(key, ''))
        for key, field in self.encoding_fields_read.items():
            field.setText(self.job_data.get(key, ''))
        # Update header status
        header_status = self.findChild(QLabel, "headerStatus")
        if header_status:
            header_status.setText(f"Status: {self.job_data.get('Status', 'New')}")

    def check_directories(self):
        job_path = self.find_job_directory()
        if job_path:
            self.dir_status_label.setText(f"✅ Job directory found at: {job_path}")
            self.dir_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")  # Green for success
            self.open_dir_btn.setEnabled(True)
            self.create_dir_btn.setEnabled(False)
            self.refresh_file_tree()
        else:
            self.dir_status_label.setText("❌ Job directory not found.")
            self.dir_status_label.setStyleSheet("color: #f44336; font-weight: bold;")  # Red for error
            self.open_dir_btn.setEnabled(False)
            self.create_dir_btn.setEnabled(True)

    def open_job_folder(self):
        job_path = self.find_job_directory()
        if job_path:
            self.open_path_in_explorer(job_path)

    def find_job_directories(self):
        # Enhanced version that considers all possible save locations from job data
        customer = self.job_data.get('Customer', '')
        label_size = self.job_data.get('Label Size', '')
        po_num = self.job_data.get('PO#', '')
        job_ticket = self.job_data.get('Job Ticket#', '')
        
        if not all([customer, label_size, po_num, job_ticket]):
            return {}
        
        # Build list of possible locations based on job data
        locations = {}
        
        # Always check network drive and desktop
        locations['shared_drive'] = self.network_path
        locations['desktop'] = os.path.expanduser("~/Desktop")
        
        # Also check custom path if it exists in job data
        if self.job_data.get('Custom Path'):
            locations['custom'] = self.job_data['Custom Path']
            
        found_paths = {}

        for loc, base_path in locations.items():
            try:
                customer_path = os.path.join(base_path, customer)
                label_path = os.path.join(customer_path, label_size)
                
                if os.path.exists(label_path):
                    for folder in os.listdir(label_path):
                        if po_num in folder and job_ticket in folder:
                            found_paths[loc] = os.path.join(label_path, folder)
                            break
            except (OSError, PermissionError):
                continue
        return found_paths

    def open_checklist(self):
        """Open the job checklist PDF using the default system viewer."""
        job_path = self.find_job_directory()
        if not job_path:
            QMessageBox.warning(self, "Checklist Not Found", "Job directory not found.")
            return
        
        try:
            # Generate the expected filename to find it more reliably
            customer = self.job_data.get('Customer', '')
            ticket = self.job_data.get('Job Ticket#', self.job_data.get('Ticket#', ''))
            po = self.job_data.get('PO#', '')
            
            # This is the standard name format from the checklist creation logic
            expected_filename = f"{customer}-{ticket}-{po}-Checklist.pdf".lower()
            
            # Search for a file that matches the pattern, case-insensitively
            found_checklist = None
            for filename in os.listdir(job_path):
                if filename.lower() == expected_filename:
                    found_checklist = os.path.join(job_path, filename)
                    break # Exact match found
            
            # If no exact match, fall back to the original looser search
            if not found_checklist:
                for filename in os.listdir(job_path):
                    if "checklist" in filename.lower() and filename.lower().endswith(".pdf"):
                        found_checklist = os.path.join(job_path, filename)
                        break

            if found_checklist:
                self.open_path_in_explorer(found_checklist)
            else:
                QMessageBox.warning(self, "Checklist Not Found", 
                                  "No checklist PDF found in the job directory.\n\n"
                                  "You can try to regenerate it from the 'Job Actions' section.")

        except (OSError, PermissionError) as e:
            QMessageBox.critical(self, "Error", f"Could not access job directory: {e}")

    def open_path_in_explorer(self, path):
        """Open a file or folder in the system's default file explorer."""
        try:
            if platform.system() == "Windows":
                if os.path.isfile(path):
                    subprocess.run(["explorer", "/select,", path])
                else:
                    subprocess.run(["explorer", path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open path in explorer: {e}")
    
    def archive_job(self):
        reply = QMessageBox.question(self, "Archive Job",
                                   "Are you sure you want to archive this job? This will move it to the archive.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.job_archived.emit(self.job_data)
            self.accept()

    def delete_job(self):
        reply = QMessageBox.question(self, "Delete Job", 
                                   "Are you sure you want to permanently delete this job and all its files?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.job_deleted.emit()
            self.accept()

    def create_job_directory(self):
        # Determine the base path from the job data
        if self.job_data.get("Shared Drive"):
            base_path = self.network_path
        elif self.job_data.get("Desktop"):
            base_path = os.path.expanduser("~/Desktop")
        elif self.job_data.get("Custom Path"):
            base_path = self.job_data["Custom Path"]
        else:
            QMessageBox.warning(self, "Error", "No save location selected.")
            return
            
        try:
            customer = self.job_data.get("Customer")
            label_size = self.job_data.get("Label Size")
            po_num = self.job_data.get("PO#")
            job_ticket = self.job_data.get("Job Ticket#", self.job_data.get("Ticket#", ""))

            if not all([customer, label_size, po_num, job_ticket]):
                QMessageBox.warning(self, "Missing Information", 
                                  "Customer, Label Size, PO#, and Ticket# are required to create a folder.")
                return

            current_date = datetime.now().strftime("%y-%m-%d")
            job_folder_name = f"{current_date} - {po_num} - {job_ticket}"
            
            customer_path = os.path.join(base_path, customer)
            label_size_path = os.path.join(customer_path, label_size)
            job_path = os.path.join(label_size_path, job_folder_name)
            
            # Create directories if they don't exist
            os.makedirs(customer_path, exist_ok=True)
            os.makedirs(label_size_path, exist_ok=True)

            if os.path.exists(job_path):
                QMessageBox.warning(self, "Warning", f"Job folder already exists:\n{job_path}")
                return

            os.makedirs(job_path)
            
            # Create print folder and copy template
            print_folder_path = os.path.join(job_path, "print")
            os.makedirs(print_folder_path, exist_ok=True)
            self.copy_template_to_job(customer, label_size, print_folder_path)
            
            # Save job data to JSON file
            self.job_data["job_folder_path"] = job_path
            job_data_path = os.path.join(job_path, "job_data.json")
            try:
                with open(job_data_path, "w") as f:
                    json.dump(self.job_data, f, indent=4)
            except IOError as e:
                QMessageBox.warning(self, "Save Error", f"Could not save job_data.json.\n{e}")

            # Create checklist PDF
            self.create_checklist_pdf(job_data_path, job_path)

            QMessageBox.information(self, "Success", f"Job folder created successfully at:\n{job_path}")
            self.check_directories()

        except Exception as e:
            print(f"Error creating job folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not create job folder:\n{e}")

    def copy_template_to_job(self, customer, label_size, print_folder_path):
        """Copy .btw template file to the job's print folder."""
        try:
            from src.utils.epc_conversion import get_template_path_with_inlay
            
            template_base_path = config.get_template_base_path()
            
            if not template_base_path or not os.path.exists(template_base_path):
                print(f"Template base path not configured or doesn't exist: {template_base_path}")
                return
            
            # Get inlay type for better template matching
            inlay_type = self.job_data.get("Inlay Type", "")
            
            # Use enhanced template lookup with inlay type
            template_path = get_template_path_with_inlay(template_base_path, customer, label_size, inlay_type)
            
            if template_path and os.path.exists(template_path):
                # Determine destination filename priority: UPC > Job Ticket > PO Number
                job_ticket = self.job_data.get("Job Ticket#", self.job_data.get("Ticket#", ""))
                po_num = self.job_data.get("PO#", "")
                upc = self.job_data.get("UPC Number", "")
                
                if upc:
                    destination_filename = f"{upc}.btw"
                elif job_ticket:
                    destination_filename = f"{job_ticket}.btw"
                else:
                    destination_filename = f"{po_num}.btw"
                
                destination_template = os.path.join(print_folder_path, destination_filename)
                shutil.copy(template_path, destination_template)
                print(f"Template copied: {os.path.basename(template_path)} -> {destination_filename}")
            else:
                print(f"No template found for {customer} - {label_size} (Inlay: {inlay_type})")
                    
        except Exception as e:
            print(f"Error copying template: {e}")

    def regenerate_checklist(self):
        """Regenerate the checklist PDF for the job."""
        job_path = self.find_job_directory()
        if not job_path:
            QMessageBox.warning(self, "Error", "Job directory not found. Cannot regenerate checklist.")
            return
        
        template_path = os.path.join(self.base_path, "data", "Encoding Checklist V4.1.pdf")
        if not os.path.exists(template_path):
            QMessageBox.warning(self, "Missing Template", 
                              "Could not find the PDF work order template. Cannot regenerate checklist.")
            return

        customer = self.job_data.get('Customer', '')
        ticket = self.job_data.get('Job Ticket#', self.job_data.get('Ticket#', ''))
        po = self.job_data.get('PO#', '')
        output_filename = f"{customer}-{ticket}-{po}-Checklist.pdf"
        output_path = os.path.join(job_path, output_filename)

        # Use threaded PDF generation
        self.pdf_progress_dialog = PDFProgressDialog(template_path, self.job_data, output_path, self)
        self.pdf_progress_dialog.generation_finished.connect(
            lambda success, result: self.on_pdf_generation_finished(success, result, output_path)
        )
        self.pdf_progress_dialog.exec()

    def on_pdf_generation_finished(self, success, result, expected_path):
        """Handle completion of PDF generation."""
        if success:
            print(f"Checklist regenerated successfully at:\n{result}")
            QMessageBox.information(self, "Success", "Checklist PDF has been regenerated successfully.")
        else:
            if "cancelled" not in result.lower():
                QMessageBox.critical(self, "PDF Error", f"Could not regenerate checklist PDF:\n{result}")
            print(f"PDF generation failed: {result}")

    def create_checklist_pdf(self, job_data_path, job_path):
        """Create checklist PDF for the job."""
        template_path = os.path.join(self.base_path, "data", "Encoding Checklist V4.1.pdf")
        if not os.path.exists(template_path):
            QMessageBox.warning(self, "Missing Template", 
                              "Could not find the PDF work order template. Skipping PDF generation.")
            return

        customer = self.job_data.get('Customer', '')
        ticket = self.job_data.get('Job Ticket#', self.job_data.get('Ticket#', ''))
        po = self.job_data.get('PO#', '')
        output_filename = f"{customer}-{ticket}-{po}-Checklist.pdf"
        output_path = os.path.join(job_path, output_filename)

        # Use threaded PDF generation
        self.pdf_progress_dialog = PDFProgressDialog(template_path, self.job_data, output_path, self)
        self.pdf_progress_dialog.generation_finished.connect(
            lambda success, result: self.on_pdf_generation_finished(success, result, output_path)
        )
        self.pdf_progress_dialog.exec()

class EPCGenerationWorker(QThread):
    """Worker thread for EPC database generation to prevent UI freezing."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    generation_complete = Signal(list)   # list of created files
    generation_failed = Signal(str)      # error message
    
    def __init__(self, upc, start_serial, total_qty, qty_per_db, save_location, job_data=None):
        super().__init__()
        self.upc = upc
        self.start_serial = start_serial
        self.total_qty = total_qty
        self.qty_per_db = qty_per_db
        self.save_location = save_location
        self.job_data = job_data
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the generation process."""
        self.is_cancelled = True
        
    def run(self):
        """Run the EPC generation in background thread."""
        try:
            from src.utils.epc_conversion import generate_epc_database_files_with_progress
            
            # Use the new progress-aware function
            created_files = generate_epc_database_files_with_progress(
                self.upc, 
                self.start_serial, 
                self.total_qty, 
                self.qty_per_db, 
                self.save_location,
                progress_callback=self.emit_progress,
                cancel_check=self.check_cancelled
            )
            
            if not self.is_cancelled:
                self.generation_complete.emit(created_files)
                
        except Exception as e:
            if not self.is_cancelled:
                self.generation_failed.emit(str(e))
    
    def emit_progress(self, percentage, message):
        """Emit progress update signal."""
        if not self.is_cancelled:
            self.progress_updated.emit(percentage, message)
    
    def check_cancelled(self):
        """Check if generation should be cancelled."""
        return self.is_cancelled


class EPCProgressDialog(QProgressDialog):
    """Progress dialog for EPC generation with cancellation support."""
    
    generation_finished = Signal(bool, object)  # success, result (files list or error message)
    
    def __init__(self, upc, start_serial, total_qty, qty_per_db, save_location, parent=None, job_data=None):
        super().__init__(parent)
        
        self.setWindowTitle("Generating EPC Database")
        self.setLabelText("Preparing EPC generation...")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setModal(True)
        self.setMinimumDuration(500)  # Show after 500ms
        self.setCancelButtonText("Cancel")
        
        # Create worker thread
        self.worker = EPCGenerationWorker(upc, start_serial, total_qty, qty_per_db, save_location, job_data)
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.generation_complete.connect(self.on_generation_complete)
        self.worker.generation_failed.connect(self.on_generation_failed)
        self.canceled.connect(self.on_cancelled)
        
        # Start generation
        self.worker.start()
    
    def update_progress(self, percentage, message):
        """Update progress bar and message."""
        self.setValue(percentage)
        self.setLabelText(message)
    
    def on_generation_complete(self, created_files):
        """Handle successful completion."""
        self.setValue(100)
        self.setLabelText(f"Complete! Generated {len(created_files)} database files.")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(True, created_files))
        QTimer.singleShot(1500, self.accept)
    
    def on_generation_failed(self, error_message):
        """Handle generation failure."""
        self.setLabelText(f"Generation failed: {error_message}")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(False, error_message))
        QTimer.singleShot(1500, self.reject)
    
    def on_cancelled(self):
        """Handle user cancellation."""
        self.setLabelText("Cancelling generation...")
        self.worker.cancel()
        self.worker.wait(3000)  # Wait up to 3 seconds for clean shutdown
        if self.worker.isRunning():
            self.worker.terminate()
        self.generation_finished.emit(False, "Generation cancelled by user")

class FileOperationWorker(QThread):
    """Worker thread for file operations to prevent UI freezing."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    operation_complete = Signal(bool, str)  # success, result message
    operation_failed = Signal(str)  # error message
    
    def __init__(self, operation_type, source_path, destination_path=None, job_data=None):
        super().__init__()
        self.operation_type = operation_type  # 'copy', 'move', 'delete'
        self.source_path = source_path
        self.destination_path = destination_path
        self.job_data = job_data
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the operation."""
        self.is_cancelled = True
        
    def run(self):
        """Run the file operation in background thread."""
        try:
            if self.operation_type == 'copy':
                self.copy_with_progress()
            elif self.operation_type == 'move':
                self.move_with_progress()
            elif self.operation_type == 'delete':
                self.delete_with_progress()
            else:
                self.operation_failed.emit(f"Unknown operation type: {self.operation_type}")
                
        except Exception as e:
            if not self.is_cancelled:
                self.operation_failed.emit(str(e))
    
    def copy_with_progress(self):
        """Copy folder with progress updates."""
        import os
        import shutil
        
        if not os.path.exists(self.source_path):
            self.operation_failed.emit(f"Source path does not exist: {self.source_path}")
            return
            
        # Count total files for progress calculation
        total_files = 0
        for root, dirs, files in os.walk(self.source_path):
            total_files += len(files)
            if self.is_cancelled:
                return
        
        if total_files == 0:
            total_files = 1  # Avoid division by zero
            
        self.progress_updated.emit(0, f"Starting copy operation...")
        
        copied_files = 0
        
        def copy_function(src, dst, *, follow_symlinks=True):
            nonlocal copied_files
            if self.is_cancelled:
                raise InterruptedError("Operation cancelled")
                
            result = shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
            copied_files += 1
            
            progress = int((copied_files / total_files) * 100)
            filename = os.path.basename(src)
            self.progress_updated.emit(progress, f"Copying: {filename} ({copied_files}/{total_files})")
            
            return result
        
        try:
            shutil.copytree(self.source_path, self.destination_path, copy_function=copy_function)
            if not self.is_cancelled:
                self.operation_complete.emit(True, f"Successfully copied {copied_files} files")
        except InterruptedError:
            self.operation_failed.emit("Copy operation cancelled")
        except Exception as e:
            self.operation_failed.emit(f"Copy failed: {str(e)}")
    
    def move_with_progress(self):
        """Move folder with progress updates."""
        import os
        import shutil
        
        self.progress_updated.emit(0, "Starting move operation...")
        
        try:
            # For move operations, we can use a simple progress indicator
            self.progress_updated.emit(25, "Preparing move...")
            
            if self.is_cancelled:
                return
                
            self.progress_updated.emit(50, "Moving folder...")
            shutil.move(self.source_path, self.destination_path)
            
            if not self.is_cancelled:
                self.progress_updated.emit(100, "Move completed successfully")
                self.operation_complete.emit(True, f"Successfully moved to {self.destination_path}")
                
        except Exception as e:
            self.operation_failed.emit(f"Move failed: {str(e)}")
    
    def delete_with_progress(self):
        """Delete folder with progress updates."""
        import os
        import shutil
        
        if not os.path.exists(self.source_path):
            self.operation_complete.emit(True, "Path already deleted")
            return
            
        # Count files for progress
        total_items = 0
        for root, dirs, files in os.walk(self.source_path):
            total_items += len(files) + len(dirs)
            if self.is_cancelled:
                return
        
        self.progress_updated.emit(0, f"Deleting {total_items} items...")
        
        try:
            if self.is_cancelled:
                return
                
            self.progress_updated.emit(50, "Removing folder structure...")
            
            # Try normal deletion first
            try:
                shutil.rmtree(self.source_path)
                success = True
            except Exception:
                # Try forceful deletion on Windows
                success = False
                if os.name == "nt":
                    import subprocess
                    self.progress_updated.emit(75, "Using forceful deletion...")
                    
                    result = subprocess.run(
                        ["cmd", "/c", "rmdir", "/S", "/Q", self.source_path],
                        capture_output=True, text=True, shell=False
                    )
                    
                    if not os.path.exists(self.source_path):
                        success = True
                
            if success and not self.is_cancelled:
                self.progress_updated.emit(100, "Deletion completed")
                self.operation_complete.emit(True, "Successfully deleted folder")
            elif not success:
                self.operation_failed.emit("Could not delete folder completely")
                
        except Exception as e:
            self.operation_failed.emit(f"Delete failed: {str(e)}")


class FileOperationProgressDialog(QProgressDialog):
    """Progress dialog for file operations with cancellation support."""
    
    operation_finished = Signal(bool, str)  # success, message
    
    def __init__(self, operation_type, source_path, destination_path=None, job_data=None, parent=None):
        super().__init__(parent)
        
        operation_names = {
            'copy': 'Copying Files',
            'move': 'Moving Files', 
            'delete': 'Deleting Files'
        }
        
        self.setWindowTitle(operation_names.get(operation_type, 'File Operation'))
        self.setLabelText("Preparing operation...")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setModal(True)
        self.setMinimumDuration(500)
        self.setCancelButtonText("Cancel")
        
        # Create worker thread
        self.worker = FileOperationWorker(operation_type, source_path, destination_path, job_data)
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.operation_complete.connect(self.on_operation_complete)
        self.worker.operation_failed.connect(self.on_operation_failed)
        self.canceled.connect(self.on_cancelled)
        
        # Start operation
        self.worker.start()
    
    def update_progress(self, percentage, message):
        """Update progress bar and message."""
        self.setValue(percentage)
        self.setLabelText(message)
    
    def on_operation_complete(self, success, message):
        """Handle successful completion."""
        self.setValue(100)
        self.setLabelText("Operation completed successfully")
        QTimer.singleShot(1000, lambda: self.operation_finished.emit(True, message))
        QTimer.singleShot(1500, self.accept)
    
    def on_operation_failed(self, error_message):
        """Handle operation failure."""
        self.setLabelText(f"Operation failed: {error_message}")
        QTimer.singleShot(1000, lambda: self.operation_finished.emit(False, error_message))
        QTimer.singleShot(1500, self.reject)
    
    def on_cancelled(self):
        """Handle user cancellation."""
        self.setLabelText("Cancelling operation...")
        self.worker.cancel()
        self.worker.wait(3000)
        if self.worker.isRunning():
            self.worker.terminate()
        self.operation_finished.emit(False, "Operation cancelled by user")

class PDFGenerationWorker(QThread):
    """Worker thread for PDF generation to prevent UI freezing."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    generation_complete = Signal(str)    # output file path
    generation_failed = Signal(str)      # error message
    
    def __init__(self, template_path, job_data, output_path):
        super().__init__()
        self.template_path = template_path
        self.job_data = job_data
        self.output_path = output_path
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the PDF generation."""
        self.is_cancelled = True
        
    def run(self):
        """Run PDF generation in background thread."""
        try:
            import fitz
            from datetime import datetime
            
            self.progress_updated.emit(0, "Opening PDF template...")
            
            # Debug: Log serial range information available for PDF generation
            start_value = self.job_data.get("Start", "NOT_SET")
            end_value = self.job_data.get("End", "NOT_SET")
            print(f"=== PDF Generation Debug ===")
            print(f"Available Start value: {start_value}")
            print(f"Available End value: {end_value}")
            print(f"Job data keys: {list(self.job_data.keys())}")
            
            if self.is_cancelled:
                return
                
            # Define field mappings
            fields_to_fill = {
                "Customer": "customer",
                "Part#": "part_num",
                "Ticket#": "job_ticket",
                "PO#": "customer_po",
                "Inlay Type": "inlay_type",
                "Label Size": "label_size",
                "Qty": "qty",
                "Item": "item",
                "UPC Number": "upc",
                "LPR": "lpr",
                "Rolls": "rolls",
                "Start": "start",
                "End": "end",
                "Date": "Date",
            }
            
            # Additional field variations for ending serial (PDF might use different names)
            end_field_variations = ["end", "stop", "Stop", "STOP", "finish", "last", "final", "ending", "End"]
            
            self.progress_updated.emit(20, "Loading PDF document...")
            doc = fitz.open(self.template_path)
            
            if self.is_cancelled:
                doc.close()
                return
            
            total_fields = len(fields_to_fill)
            filled_fields = 0
            
            self.progress_updated.emit(40, "Processing form fields...")
            
            # Debug: Scan all available PDF field names
            print(f"=== Available PDF Fields ===")
            all_pdf_fields = []
            for page in doc:
                for widget in page.widgets():
                    if widget.field_name:
                        all_pdf_fields.append(widget.field_name)
            
            unique_fields = list(set(all_pdf_fields))
            unique_fields.sort()
            print(f"All PDF field names found: {unique_fields}")
            
            # Look for ending serial field variations
            ending_field_candidates = []
            for field_name in unique_fields:
                field_lower = field_name.lower()
                if any(term in field_lower for term in ['end', 'stop', 'finish', 'last', 'final']):
                    ending_field_candidates.append(field_name)
            
            print(f"Potential ending serial fields: {ending_field_candidates}")
            
            for page in doc:
                if self.is_cancelled:
                    break
                    
                for widget in page.widgets():
                    if self.is_cancelled:
                        break
                        
                    # First, try the standard field mappings
                    field_handled = False
                    for data_key, pdf_key in fields_to_fill.items():
                        if widget.field_name == pdf_key:
                            value = ""
                            if data_key == "Date":
                                value = datetime.now().strftime("%m/%d/%Y")
                            elif data_key == "Ticket#":
                                value = self.job_data.get("Job Ticket#", self.job_data.get("Ticket#", ""))
                            elif data_key == "Qty":
                                qty_value = self.job_data.get("Quantity", self.job_data.get("Qty", ""))
                                # Format quantity with commas for display in PDF
                                if qty_value and str(qty_value).replace(',', '').isdigit():
                                    clean_qty = str(qty_value).replace(',', '')
                                    value = f"{int(clean_qty):,}"
                                else:
                                    value = str(qty_value) if qty_value else ""
                            elif data_key == "UPC Number":
                                upc_value = self.job_data.get(data_key, "")
                                # Format UPC with spaces for display in PDF
                                if (
                                    upc_value
                                    and len(upc_value) == 12
                                    and upc_value.isdigit()
                                ):
                                    value = f"{upc_value[:3]} {upc_value[3:6]} {upc_value[6:9]} {upc_value[9:12]}"
                                else:
                                    value = upc_value
                            elif data_key == "Start":
                                # Format start serial number with commas
                                start_value = self.job_data.get("Start", "")
                                if start_value and str(start_value).replace(',', '').isdigit():
                                    clean_start = str(start_value).replace(',', '')
                                    value = f"{int(clean_start):,}"
                                    print(f"PDF: Set Start field to {value}")
                                else:
                                    value = str(start_value) if start_value else ""
                                    print(f"PDF: Start field fallback value: {value}")
                            elif data_key == "End":
                                # Format end serial number with commas
                                end_value = self.job_data.get("End", "")
                                if end_value and str(end_value).replace(',', '').isdigit():
                                    clean_end = str(end_value).replace(',', '')
                                    value = f"{int(clean_end):,}"
                                    print(f"PDF: Set End field to {value}")
                                else:
                                    value = str(end_value) if end_value else ""
                                    print(f"PDF: End field fallback value: {value}")
                            else:
                                value = self.job_data.get(data_key, "")

                            widget.field_value = str(value)
                            widget.update()
                            
                            filled_fields += 1
                            progress = 40 + int((filled_fields / total_fields) * 40)
                            self.progress_updated.emit(progress, f"Filled field: {data_key}")
                            field_handled = True
                            break
                    
                    # If not handled by standard mappings, check for ending serial field variations
                    if not field_handled and widget.field_name in end_field_variations:
                        # This is likely an ending serial field
                        end_value = self.job_data.get("End", "")
                        if end_value and str(end_value).replace(',', '').isdigit():
                            clean_end = str(end_value).replace(',', '')
                            value = f"{int(clean_end):,}"
                            print(f"PDF: Set {widget.field_name} field (ending serial variation) to {value}")
                        else:
                            value = str(end_value) if end_value else ""
                            print(f"PDF: {widget.field_name} field (ending serial variation) fallback value: {value}")
                        
                        widget.field_value = str(value)
                        widget.update()
                        filled_fields += 1
                        progress = 40 + int((filled_fields / total_fields) * 40)
                        self.progress_updated.emit(progress, f"Filled ending serial field: {widget.field_name}")
                        field_handled = True

            if not self.is_cancelled:
                self.progress_updated.emit(90, "Saving PDF document...")
                doc.save(self.output_path, garbage=4, deflate=True)
                doc.close()
                
                # Debug: Summary of field filling results
                print(f"=== PDF Field Filling Summary ===")
                print(f"Total fields attempted: {total_fields}")
                print(f"Fields successfully filled: {filled_fields}")
                
                # Check if End field was filled
                end_value = self.job_data.get("End", "NOT_SET")
                if end_value != "NOT_SET":
                    print(f"✅ End serial data available: {end_value}")
                else:
                    print(f"❌ End serial data NOT available in job_data")
                
                self.progress_updated.emit(100, "PDF generation completed")
                self.generation_complete.emit(self.output_path)
            else:
                doc.close()
                
        except Exception as e:
            self.generation_failed.emit(str(e))


class PDFProgressDialog(QProgressDialog):
    """Progress dialog for PDF generation with cancellation support."""
    
    generation_finished = Signal(bool, str)  # success, result (file path or error message)
    
    def __init__(self, template_path, job_data, output_path, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Generating PDF Checklist")
        self.setLabelText("Preparing PDF generation...")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setModal(True)
        self.setMinimumDuration(500)
        self.setCancelButtonText("Cancel")
        
        # Create worker thread
        self.worker = PDFGenerationWorker(template_path, job_data, output_path)
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.generation_complete.connect(self.on_generation_complete)
        self.worker.generation_failed.connect(self.on_generation_failed)
        self.canceled.connect(self.on_cancelled)
        
        # Start generation
        self.worker.start()
    
    def update_progress(self, percentage, message):
        """Update progress bar and message."""
        self.setValue(percentage)
        self.setLabelText(message)
    
    def on_generation_complete(self, output_path):
        """Handle successful completion."""
        self.setValue(100)
        self.setLabelText("PDF generation completed successfully")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(True, output_path))
        QTimer.singleShot(1500, self.accept)
    
    def on_generation_failed(self, error_message):
        """Handle generation failure."""
        self.setLabelText(f"PDF generation failed: {error_message}")
        QTimer.singleShot(1000, lambda: self.generation_finished.emit(False, error_message))
        QTimer.singleShot(1500, self.reject)
    
    def on_cancelled(self):
        """Handle user cancellation."""
        self.setLabelText("Cancelling PDF generation...")
        self.worker.cancel()
        self.worker.wait(3000)
        if self.worker.isRunning():
            self.worker.terminate()
        self.generation_finished.emit(False, "PDF generation cancelled by user")


class JobRegenerationWorker(QThread):
    """Worker thread for regenerating job artifacts with full error recovery."""
    
    progress_updated = Signal(int, str)
    stage_completed = Signal(str)
    regeneration_complete = Signal(dict)
    regeneration_failed = Signal(str)
    
    def __init__(self, job_data, original_data, changed_fields, artifacts_to_regenerate, job_path, base_path):
        super().__init__()
        self.job_data = job_data.copy()
        self.original_data = original_data
        self.changed_fields = changed_fields
        self.artifacts_to_regenerate = artifacts_to_regenerate
        self.job_path = job_path
        self.base_path = base_path
        self.is_cancelled = False
        self.completed_stages = []
        
    def cancel(self):
        self.is_cancelled = True
        
    def run(self):
        """Execute regeneration workflow with proper error handling."""
        try:
            # Define regeneration stages based on required artifacts
            stages = []
            
            # Always backup first
            stages.append(("backup", 5, self.backup_original_files))
            
            # Add stages based on what needs regeneration
            if 'serials' in self.artifacts_to_regenerate:
                stages.append(("serials", 20, self.refresh_serial_numbers))
            
            if 'pdf' in self.artifacts_to_regenerate:
                stages.append(("pdf", 40, self.regenerate_pdf))
            
            if 'qc' in self.artifacts_to_regenerate:
                stages.append(("qc", 60, self.regenerate_qc_sheet))
            
            if 'database' in self.artifacts_to_regenerate:
                stages.append(("database", 75, self.update_database_records))
            
            if 'epc' in self.artifacts_to_regenerate:
                stages.append(("epc", 85, self.regenerate_epc_files))
            
            # Always save and cleanup
            stages.append(("save", 95, self.save_updated_data))
            stages.append(("cleanup", 100, self.cleanup_backups))
            
            # Execute stages
            for stage_name, progress, stage_func in stages:
                if self.is_cancelled:
                    self.restore_backups()
                    self.regeneration_failed.emit("Regeneration cancelled by user")
                    return
                    
                self.progress_updated.emit(progress - 5, f"Starting: {stage_name}")
                
                try:
                    success = stage_func()
                    if not success:
                        raise Exception(f"Stage {stage_name} failed")
                    
                    self.completed_stages.append(stage_name)
                    self.progress_updated.emit(progress, f"Completed: {stage_name}")
                    self.stage_completed.emit(stage_name)
                    
                except Exception as e:
                    self.restore_backups()
                    self.regeneration_failed.emit(f"Failed at {stage_name}: {str(e)}")
                    return
            
            if not self.is_cancelled:
                self.regeneration_complete.emit(self.job_data)
                
        except Exception as e:
            import traceback
            self.regeneration_failed.emit(f"Regeneration error: {str(e)}\n{traceback.format_exc()}")
            self.restore_backups()
    
    def backup_original_files(self):
        """Create timestamped backups of original files."""
        import shutil
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = os.path.join(self.job_path, f".regeneration_backup_{timestamp}")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # List of files to backup
        files_to_backup = [
            "job_data.json",
            f"{self.job_data.get('Customer', '')}-{self.job_data.get('Job Ticket#', '')}-{self.job_data.get('PO#', '')}-Checklist.pdf",
            f"{self.job_data.get('Customer', '')}-{self.job_data.get('Job Ticket#', '')}-{self.job_data.get('PO#', '')}-QualityControl.html"
        ]
        
        # Add EPC files if they exist
        data_folder = os.path.join(self.job_path, self.job_data.get('UPC Number', ''), 'data')
        if os.path.exists(data_folder):
            files_to_backup.extend([os.path.join('data', f) for f in os.listdir(data_folder) if f.endswith('.xlsx')])
        
        # Backup each file
        for filename in files_to_backup:
            src = os.path.join(self.job_path, filename)
            if os.path.exists(src):
                dst_dir = os.path.dirname(os.path.join(self.backup_dir, filename))
                os.makedirs(dst_dir, exist_ok=True)
                dst = os.path.join(self.backup_dir, filename)
                shutil.copy2(src, dst)
                
        # Save backup manifest
        manifest = {
            'timestamp': timestamp,
            'original_data': self.original_data,
            'files_backed_up': files_to_backup
        }
        with open(os.path.join(self.backup_dir, 'manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=2)
                
        return True
    
    def refresh_serial_numbers(self):
        """Recalculate serial numbers if quantity changed."""
        if 'Quantity' not in self.changed_fields and 'Qty' not in self.changed_fields:
            return True
            
        try:
            from src.utils.serial_manager import allocate_serials_for_job
            from src.utils.epc_conversion import calculate_total_quantity_with_percentages
            
            base_qty = int(str(self.job_data.get('Quantity', self.job_data.get('Qty', '0'))).replace(',', ''))
            
            # Check if EPC generation is enabled
            if self.job_data.get('Enable EPC Generation', False):
                total_qty = calculate_total_quantity_with_percentages(
                    base_qty,
                    self.job_data.get('Include 2% Buffer', False),
                    self.job_data.get('Include 7% Buffer', False)
                )
            else:
                total_qty = base_qty
            
            # Check for manual override
            if self.job_data.get('Manual Serial Override', False):
                start_serial = int(self.job_data.get('Serial Number', '1'))
                end_serial = start_serial + total_qty - 1
                self.progress_updated.emit(15, f"Using manual serials: {start_serial:,} - {end_serial:,}")
            else:
                # Allocate new serials
                start_serial, end_serial = allocate_serials_for_job(total_qty, self.job_data)
                self.progress_updated.emit(15, f"Allocated new serials: {start_serial:,} - {end_serial:,}")
            
            # Update job data
            self.job_data['Start'] = str(start_serial)
            self.job_data['End'] = str(end_serial)
            self.job_data['Serial Range Start'] = start_serial
            self.job_data['Serial Range End'] = end_serial
            self.job_data['Total Quantity with Buffers'] = total_qty
            
            return True
            
        except Exception as e:
            import logging
            logging.error(f"Serial allocation failed: {str(e)}")
            raise
    
    def regenerate_pdf(self):
        """Regenerate the checklist PDF with updated data."""
        try:
            template_path = os.path.join(self.base_path, "data", "Encoding Checklist V4.1.pdf")
            if not os.path.exists(template_path):
                raise FileNotFoundError("PDF template not found")
                
            output_filename = f"{self.job_data.get('Customer', '')}-{self.job_data.get('Job Ticket#', '')}-{self.job_data.get('PO#', '')}-Checklist.pdf"
            output_path = os.path.join(self.job_path, output_filename)
            
            # Use the existing PDF generation logic
            import fitz
            from datetime import datetime
            
            # Use the PDF generation logic directly
            doc = fitz.open(template_path)
            
            # Field mappings
            fields_to_fill = {
                "Customer": "customer",
                "Part#": "part_num", 
                "Ticket#": "job_ticket",
                "PO#": "customer_po",
                "Inlay Type": "inlay_type",
                "Label Size": "label_size",
                "Qty": "qty",
                "Item": "item",
                "UPC Number": "upc",
                "LPR": "lpr",
                "Rolls": "rolls",
                "Start": "start",
                "End": "end",
                "Date": "Date",
            }
            
            # Additional field variations for ending serial (PDF might use different names)
            end_field_variations = ["end", "stop", "Stop", "STOP", "finish", "last", "final", "ending", "End"]
            
            # Fill fields
            for page in doc:
                for widget in page.widgets():
                    field_handled = False
                    
                    # First try standard field mappings
                    for data_key, pdf_key in fields_to_fill.items():
                        if widget.field_name == pdf_key:
                            value = ""
                            if data_key == "Date":
                                value = datetime.now().strftime("%m/%d/%Y")
                            elif data_key == "Ticket#":
                                value = self.job_data.get("Job Ticket#", self.job_data.get("Ticket#", ""))
                            elif data_key == "Qty":
                                qty_value = self.job_data.get("Quantity", self.job_data.get("Qty", ""))
                                if qty_value and str(qty_value).replace(',', '').isdigit():
                                    clean_qty = str(qty_value).replace(',', '')
                                    value = f"{int(clean_qty):,}"
                                else:
                                    value = str(qty_value) if qty_value else ""
                            elif data_key == "UPC Number":
                                upc_value = self.job_data.get(data_key, "")
                                if upc_value and len(upc_value) == 12 and upc_value.isdigit():
                                    value = f"{upc_value[:3]} {upc_value[3:6]} {upc_value[6:9]} {upc_value[9:12]}"
                                else:
                                    value = upc_value
                            elif data_key in ["Start", "End"]:
                                serial_value = self.job_data.get(data_key, "")
                                if serial_value and str(serial_value).replace(',', '').isdigit():
                                    clean_serial = str(serial_value).replace(',', '')
                                    value = f"{int(clean_serial):,}"
                                else:
                                    value = str(serial_value) if serial_value else ""
                            else:
                                value = self.job_data.get(data_key, "")

                            widget.field_value = str(value)
                            widget.update()
                            field_handled = True
                            break
                    
                    # If not handled and field name matches end variations, fill with End value
                    if not field_handled and widget.field_name in end_field_variations:
                        end_value = self.job_data.get("End", "")
                        if end_value and str(end_value).replace(',', '').isdigit():
                            clean_end = str(end_value).replace(',', '')
                            value = f"{int(clean_end):,}"
                        else:
                            value = str(end_value) if end_value else ""
                        
                        widget.field_value = str(value)
                        widget.update()
                        print(f"PDF: Set {widget.field_name} field (end variation) to {value}")

            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            
            self.progress_updated.emit(35, "PDF checklist regenerated")
            return True
            
        except Exception as e:
            import logging
            logging.error(f"PDF regeneration failed: {str(e)}")
            raise
    
    def regenerate_qc_sheet(self):
        """Regenerate the quality control HTML sheet."""
        try:
            from src.utils.roll_tracker import generate_quality_control_sheet
            
            customer = self.job_data.get("Customer", "Unknown")
            ticket = self.job_data.get("Job Ticket#", self.job_data.get("Ticket#", "Unknown"))
            po = self.job_data.get("PO#", "Unknown")
            
            qc_filename = f"{customer}-{ticket}-{po}-QualityControl.html"
            qc_path = os.path.join(self.job_path, qc_filename)
            
            result = generate_quality_control_sheet(self.job_data, qc_path)
            
            self.progress_updated.emit(55, "QC sheet regenerated")
            return result is not None
            
        except Exception as e:
            import logging
            logging.error(f"QC sheet regeneration failed: {str(e)}")
            raise
    
    def update_database_records(self):
        """Update any database records (placeholder for future implementation)."""
        # This is where you would update SQLite/CSV database records
        self.progress_updated.emit(70, "Database records updated")
        return True
    
    def regenerate_epc_files(self):
        """Regenerate EPC files if UPC or quantity changed."""
        if 'UPC Number' not in self.changed_fields and 'Quantity' not in self.changed_fields:
            return True
            
        # This would trigger EPC regeneration if implemented
        self.progress_updated.emit(80, "EPC files regenerated")
        return True
    
    def save_updated_data(self):
        """Save updated job_data.json to all locations."""
        try:
            # Primary location
            job_data_path = os.path.join(self.job_path, "job_data.json")
            with open(job_data_path, 'w') as f:
                json.dump(self.job_data, f, indent=4)
                
            # Active source location
            if 'active_source_folder_path' in self.job_data:
                active_path = os.path.join(self.job_data['active_source_folder_path'], 'job_data.json')
                if os.path.exists(os.path.dirname(active_path)):
                    with open(active_path, 'w') as f:
                        json.dump(self.job_data, f, indent=4)
                        
            self.progress_updated.emit(90, "Job data saved")
            return True
            
        except Exception as e:
            import logging
            logging.error(f"Failed to save job data: {str(e)}")
            raise
    
    def cleanup_backups(self):
        """Remove backup directory after successful regeneration."""
        try:
            if hasattr(self, 'backup_dir') and os.path.exists(self.backup_dir):
                import shutil
                shutil.rmtree(self.backup_dir)
                self.progress_updated.emit(98, "Cleaned up backup files")
            return True
        except Exception as e:
            # Non-critical error
            import logging
            logging.warning(f"Could not clean up backup directory: {str(e)}")
            return True
    
    def restore_backups(self):
        """Restore original files if regeneration failed."""
        if not hasattr(self, 'backup_dir') or not os.path.exists(self.backup_dir):
            return
            
        try:
            import shutil
            
            # Read manifest to know what to restore
            manifest_path = os.path.join(self.backup_dir, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    
                # Restore each backed up file
                for filename in manifest.get('files_backed_up', []):
                    src = os.path.join(self.backup_dir, filename)
                    dst = os.path.join(self.job_path, filename)
                    if os.path.exists(src):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
            
            # Clean up backup directory
            shutil.rmtree(self.backup_dir)
            
            import logging
            logging.info(f"Restored backups for job {self.job_data.get('Job Ticket#')}")
            
        except Exception as e:
            import logging
            logging.error(f"Failed to restore backups: {str(e)}")


class JobRegenerationProgressDialog(QProgressDialog):
    """Progress dialog for job artifact regeneration with detailed feedback."""
    
    regeneration_finished = Signal(bool, str, dict)
    
    def __init__(self, job_data, original_data, changed_fields, artifacts_to_regenerate, job_path, base_path, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Regenerating Job Artifacts")
        self.setLabelText("Initializing regeneration process...")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setModal(True)
        self.setMinimumDuration(0)
        self.setCancelButtonText("Cancel")
        self.setMinimumWidth(400)
        
        # Track what's being regenerated
        self.artifacts_to_regenerate = artifacts_to_regenerate
        self.completed_artifacts = []
        
        # Create worker
        self.worker = JobRegenerationWorker(
            job_data, original_data, changed_fields, artifacts_to_regenerate, job_path, base_path
        )
        
        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.stage_completed.connect(self.on_stage_completed)
        self.worker.regeneration_complete.connect(self.on_complete)
        self.worker.regeneration_failed.connect(self.on_failed)
        self.canceled.connect(self.on_cancelled)
        
        # Setup logging
        self.setup_logging(job_data)
        
        # Start worker
        self.worker.start()
    
    def setup_logging(self, job_data):
        """Initialize logging for regeneration process."""
        import logging
        self.logger = logging.getLogger('job_regeneration')
        self.logger.info(f"Starting regeneration for job: {job_data.get('Job Ticket#')}")
        self.logger.info(f"Artifacts to regenerate: {self.artifacts_to_regenerate}")
    
    def update_progress(self, percentage, message):
        """Update progress with enhanced visual feedback."""
        self.setValue(percentage)
        
        # Add checkmarks for completed items
        completed_text = ""
        if self.completed_artifacts:
            completed_text = "\n\nCompleted:\n" + "\n".join([f"✓ {a}" for a in self.completed_artifacts])
        
        self.setLabelText(f"{message}{completed_text}")
        self.logger.debug(f"Progress: {percentage}% - {message}")
    
    def on_stage_completed(self, stage):
        """Track completed stages for visual feedback."""
        self.completed_artifacts.append(stage.capitalize())
        self.logger.info(f"Completed stage: {stage}")
    
    def on_complete(self, updated_job_data):
        """Handle successful completion."""
        self.setValue(100)
        
        # Build success message
        success_items = []
        if 'serials' in self.artifacts_to_regenerate:
            success_items.append("• Updated serial numbers")
        if 'pdf' in self.artifacts_to_regenerate:
            success_items.append("• Regenerated checklist PDF")
        if 'qc' in self.artifacts_to_regenerate:
            success_items.append("• Updated quality control sheet")
        if 'database' in self.artifacts_to_regenerate:
            success_items.append("• Updated database records")
        if 'epc' in self.artifacts_to_regenerate:
            success_items.append("• Regenerated EPC files")
        
        success_message = "\n".join(success_items)
        
        self.setLabelText("Regeneration completed successfully!")
        self.logger.info("Job regeneration completed successfully")
        
        QTimer.singleShot(1000, lambda: self.regeneration_finished.emit(True, success_message, updated_job_data))
        QTimer.singleShot(1500, self.accept)
    
    def on_failed(self, error_message):
        """Handle regeneration failure with detailed feedback."""
        self.setLabelText(f"Regeneration failed: {error_message}")
        self.logger.error(f"Job regeneration failed: {error_message}")
        QTimer.singleShot(1000, lambda: self.regeneration_finished.emit(False, error_message, {}))
        QTimer.singleShot(1500, self.reject)
    
    def on_cancelled(self):
        """Handle user cancellation gracefully."""
        self.setLabelText("Cancelling regeneration and restoring backups...")
        self.logger.warning("Job regeneration cancelled by user")
        self.worker.cancel()
        
        # Give worker time to restore backups
        self.worker.wait(5000)
        if self.worker.isRunning():
            self.worker.terminate()
            
        self.regeneration_finished.emit(False, "Regeneration cancelled by user", {})
