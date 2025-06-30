from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QSpacerItem,
    QSizePolicy,
    QListWidget,
    QDialog,
    QDialogButtonBox,
    QInputDialog
)
from PySide6.QtCore import Qt
# We import our config module to get access to the settings object and keys
import src.config as config

class SettingsPageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # --- Title ---
        title_label = QLabel("Application Settings")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 25px;")
        main_layout.addWidget(title_label)

        # --- Directory Settings Section ---
        dir_section = self.create_section_header("Directory Settings")
        main_layout.addWidget(dir_section)

        self.archive_dir_edit = self.create_directory_setting_row(
            main_layout, "Archive Directory:", "Folder where completed jobs are moved.", config.ARCHIVE_DIR
        )
        self.templates_dir_edit = self.create_directory_setting_row(
            main_layout, "Templates Directory:", "Folder containing document templates.", config.TEMPLATES_DIR
        )

        main_layout.addSpacing(30)

        # --- Job Wizard Data Section ---
        data_section = self.create_section_header("Job Wizard Dropdown Data")
        main_layout.addWidget(data_section)

        description = QLabel("Manage the options that appear in job wizard dropdown menus. Click a button to open the editor.")
        description.setStyleSheet("color: grey; margin-bottom: 15px;")
        description.setWordWrap(True)
        main_layout.addWidget(description)

        # Create buttons for each data type
        self.create_data_manager_button(main_layout, "Manage Customer Names", 
                                       "Edit the list of customer names", self.open_customer_manager)
        self.create_data_manager_button(main_layout, "Manage Label Sizes", 
                                       "Edit the list of label sizes", self.open_label_sizes_manager)
        self.create_data_manager_button(main_layout, "Manage Inlay Types", 
                                       "Edit the list of inlay types", self.open_inlay_types_manager)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # --- Save Button ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        save_button = QPushButton("Save Directory Settings")
        save_button.setFixedWidth(180)
        save_button.setStyleSheet("font-weight: bold; padding: 8px;")
        save_button.clicked.connect(self.save_directory_settings)
        button_layout.addWidget(save_button)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def create_section_header(self, title):
        """Create a styled section header."""
        label = QLabel(title)
        label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4; margin-bottom: 10px;")
        return label

    def create_directory_setting_row(self, parent_layout, label_text, description_text, current_path):
        """Create a clean directory setting row."""
        container_layout = QVBoxLayout()
        
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        container_layout.addWidget(label)
        
        description_label = QLabel(description_text)
        description_label.setStyleSheet("font-size: 10pt; color: grey; margin-bottom: 8px;")
        container_layout.addWidget(description_label)
        
        input_layout = QHBoxLayout()
        line_edit = QLineEdit(current_path)
        line_edit.setMinimumHeight(32)
        browse_button = QPushButton("Browse...")
        browse_button.setFixedWidth(100)
        browse_button.clicked.connect(lambda: self.browse_for_directory(line_edit, label_text))
        
        input_layout.addWidget(line_edit)
        input_layout.addWidget(browse_button)
        container_layout.addLayout(input_layout)
        
        parent_layout.addLayout(container_layout)
        parent_layout.addSpacing(20)
        
        return line_edit

    def create_data_manager_button(self, parent_layout, title, description, callback):
        """Create a button that opens a data manager popup."""
        container_layout = QVBoxLayout()
        
        button_layout = QHBoxLayout()
        button = QPushButton(title)
        button.setMinimumHeight(40)
        button.setStyleSheet("text-align: left; padding: 10px; font-weight: bold;")
        button.clicked.connect(callback)
        
        info_label = QLabel(description)
        info_label.setStyleSheet("color: grey; font-size: 10pt; margin-left: 15px;")
        
        button_layout.addWidget(button, 1)  # Take up most space
        button_layout.addWidget(info_label, 2)  # Take up remaining space
        
        container_layout.addLayout(button_layout)
        parent_layout.addLayout(container_layout)
        parent_layout.addSpacing(10)

    def browse_for_directory(self, line_edit, title):
        """Open a directory browser dialog."""
        directory = QFileDialog.getExistingDirectory(self, f"Select {title}", line_edit.text())
        if directory:
            line_edit.setText(directory)

    def save_directory_settings(self):
        """Save only the directory settings."""
        try:
            config.settings.setValue(config.ARCHIVE_DIR_KEY, self.archive_dir_edit.text())
            config.ARCHIVE_DIR = self.archive_dir_edit.text()
            
            config.settings.setValue(config.TEMPLATES_DIR_KEY, self.templates_dir_edit.text())
            config.TEMPLATES_DIR = self.templates_dir_edit.text()
            
            config.ensure_dirs_exist()
            QMessageBox.information(self, "Settings Saved", "Directory settings have been saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An error occurred while saving settings:\n{e}")

    # --- Popup Dialog Launchers ---
    def open_customer_manager(self):
        dialog = TxtFileManagerDialog(self, "Customer Names", config.CUSTOMER_NAMES_FILE, 
                                     "Manage the customer names that appear in the job wizard dropdown.")
        dialog.exec()

    def open_label_sizes_manager(self):
        dialog = TxtFileManagerDialog(self, "Label Sizes", config.LABEL_SIZES_FILE,
                                     "Manage the label sizes that appear in the job wizard dropdown.\nExample: 2.9 x 0.47")
        dialog.exec()

    def open_inlay_types_manager(self):
        dialog = TxtFileManagerDialog(self, "Inlay Types", config.INLAY_TYPES_FILE,
                                     "Manage the inlay types that appear in the job wizard dropdown.")
        dialog.exec()


class TxtFileManagerDialog(QDialog):
    """A dedicated dialog for managing the contents of a .txt file."""
    
    def __init__(self, parent, title, txt_file_path, description):
        super().__init__(parent)
        self.txt_file_path = txt_file_path
        self.setWindowTitle(f"Manage {title}")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # --- Header ---
        header_label = QLabel(f"Manage {title}")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: grey; margin-bottom: 20px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # --- Input Section ---
        input_layout = QHBoxLayout()
        self.new_item_edit = QLineEdit()
        self.new_item_edit.setPlaceholderText(f"Enter new {title.lower()}...")
        self.new_item_edit.setMinimumHeight(32)
        
        add_button = QPushButton("Add")
        add_button.setFixedWidth(80)
        add_button.setMinimumHeight(32)
        add_button.clicked.connect(self.add_item)
        
        input_layout.addWidget(self.new_item_edit)
        input_layout.addWidget(add_button)
        layout.addLayout(input_layout)

        # --- List Widget ---
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(250)
        layout.addWidget(self.list_widget)

        # --- Action Buttons ---
        action_layout = QHBoxLayout()
        edit_button = QPushButton("Edit Selected")
        remove_button = QPushButton("Remove Selected")
        
        edit_button.clicked.connect(self.edit_selected)
        remove_button.clicked.connect(self.remove_selected)
        
        action_layout.addWidget(edit_button)
        action_layout.addWidget(remove_button)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_and_close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # --- Load Data ---
        self.load_data()
        
        # --- Connect Enter Key ---
        self.new_item_edit.returnPressed.connect(self.add_item)

    def load_data(self):
        """Load the current contents of the .txt file."""
        items = config.read_txt_file(self.txt_file_path)
        self.list_widget.clear()
        self.list_widget.addItems(items)

    def add_item(self):
        """Add a new item to the list."""
        new_text = self.new_item_edit.text().strip()
        if not new_text:
            return

        # Check for duplicates
        existing_items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if new_text in existing_items:
            QMessageBox.warning(self, "Duplicate Entry", f"'{new_text}' already exists in the list.")
            return

        self.list_widget.addItem(new_text)
        self.new_item_edit.clear()

    def edit_selected(self):
        """Edit the selected item."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select an item to edit.")
            return

        item = selected_items[0]
        current_text = item.text()
        
        new_text, ok = QInputDialog.getText(self, "Edit Item", "Edit the selected item:", text=current_text)
        if ok and new_text.strip():
            new_text = new_text.strip()
            # Check for duplicates (excluding current item)
            existing_items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())
                            if self.list_widget.item(i) != item]
            if new_text in existing_items:
                QMessageBox.warning(self, "Duplicate Entry", f"'{new_text}' already exists in the list.")
                return
            
            item.setText(new_text)

    def remove_selected(self):
        """Remove selected items."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select an item to remove.")
            return

        # Confirm deletion
        items_text = ", ".join([item.text() for item in selected_items])
        reply = QMessageBox.question(self, "Confirm Removal", 
                                   f"Are you sure you want to remove:\n{items_text}?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                self.list_widget.takeItem(self.list_widget.row(item))

    def save_and_close(self):
        """Save the changes to the .txt file and close the dialog."""
        try:
            items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
            
            if config.write_txt_file(self.txt_file_path, items):
                QMessageBox.information(self, "Saved", "Changes have been saved successfully!")
                self.accept()
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save the changes.")
        
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An error occurred while saving:\n{e}") 