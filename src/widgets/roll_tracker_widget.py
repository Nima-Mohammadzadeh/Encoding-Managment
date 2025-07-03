from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGroupBox, QFormLayout, QLineEdit, QCheckBox, QComboBox, QFrame,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
import json
import os
from datetime import datetime

class RollTrackerWidget(QWidget):
    def __init__(self, job_data, parent=None):
        super().__init__(parent)
        self.job_data = job_data
        self.roll_tracker_file = None
        self.roll_widgets = []

        # Find the job folder and set up the roll tracker data file path
        self.job_folder_path = self.find_job_directory()
        if self.job_folder_path:
            self.roll_tracker_file = os.path.join(self.job_folder_path, "roll_tracker_data.json")

        self.setup_ui()
        self.load_printers()
        self.load_roll_data()

    def find_job_directory(self):
        """Find the correct job directory."""
        if 'job_folder_path' in self.job_data and os.path.exists(self.job_data['job_folder_path']):
            return self.job_data['job_folder_path']
        # Add more robust search logic if needed, similar to JobDetailsDialog
        return self.job_data.get("active_source_folder_path")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_layout = QHBoxLayout()
        self.progress_label = QLabel("Rolls Completed: 0 / 0")
        header_layout.addWidget(self.progress_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Scroll Area for rolls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.rolls_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Save Button
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_roll_data)
        main_layout.addWidget(self.save_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        if not self.job_folder_path:
            self.show_error_message("Job folder not found. Cannot load or save roll tracker data.")
            self.save_button.setEnabled(False)


    def load_printers(self):
        """Load printer names from the Printers.txt file."""
        self.printers = [""] # Add an empty option
        try:
            printer_file = os.path.join("data", "Printers.txt")
            if os.path.exists(printer_file):
                with open(printer_file, 'r') as f:
                    self.printers.extend([line.strip() for line in f if line.strip()])
        except Exception as e:
            print(f"Error loading printers: {e}")


    def load_roll_data(self):
        """Load roll data from the JSON file or create it if it doesn't exist."""
        if not self.roll_tracker_file:
            return

        roll_data = []
        if os.path.exists(self.roll_tracker_file):
            try:
                with open(self.roll_tracker_file, 'r') as f:
                    roll_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.show_error_message(f"Error loading roll tracker data: {e}")
                return
        else:
            # If the file doesn't exist, generate the initial data structure
            try:
                num_rolls = int(self.job_data.get("Rolls", 0))
                for i in range(1, num_rolls + 1):
                    roll_data.append({
                        "roll_number": i,
                        "completed": False,
                        "initials": "",
                        "notes": "",
                        "printer": "",
                        "timestamp": ""
                    })
            except (ValueError, TypeError):
                 self.show_error_message("Invalid 'Rolls' number in job data. Cannot create roll tracker.")
                 return

        self.populate_rolls(roll_data)
        self.update_progress()

    def populate_rolls(self, roll_data):
        # Clear existing widgets
        for widget in self.roll_widgets:
            widget.deleteLater()
        self.roll_widgets = []

        for data in roll_data:
            roll_widget = self.create_roll_entry(data)
            self.rolls_layout.addWidget(roll_widget)
            self.roll_widgets.append(roll_widget)

    def create_roll_entry(self, data):
        """Creates a widget for a single roll."""
        roll_frame = QFrame()
        roll_frame.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(roll_frame)
        
        # Checkbox
        check_box = QCheckBox(f"Roll {data['roll_number']}")
        check_box.setChecked(data.get("completed", False))
        layout.addWidget(check_box, 1)

        # Form for details
        form_layout = QFormLayout()
        initials_edit = QLineEdit(data.get("initials", ""))
        notes_edit = QLineEdit(data.get("notes", ""))
        printer_combo = QComboBox()
        printer_combo.addItems(self.printers)
        printer_combo.setCurrentText(data.get("printer", ""))
        
        form_layout.addRow("Initials:", initials_edit)
        form_layout.addRow("Printer:", printer_combo)
        form_layout.addRow("Notes:", notes_edit)
        layout.addLayout(form_layout, 4)

        # Timestamp Label
        timestamp_label = QLabel(data.get("timestamp", ""))
        timestamp_label.setStyleSheet("font-style: italic; color: #888;")
        layout.addWidget(timestamp_label, 1)
        
        # Store widgets for later access
        roll_frame.setProperty("roll_data_widgets", {
            "check_box": check_box,
            "initials": initials_edit,
            "notes": notes_edit,
            "printer": printer_combo,
            "timestamp": timestamp_label,
            "roll_number": data['roll_number']
        })
        
        check_box.stateChanged.connect(lambda state, ts_label=timestamp_label: \
            ts_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) if state else ts_label.setText(""))
            
        return roll_frame

    def save_roll_data(self):
        """Save the current state of all rolls to the JSON file."""
        if not self.roll_tracker_file:
            self.show_error_message("Cannot save: Roll tracker file path is not set.")
            return

        updated_roll_data = []
        for roll_widget in self.roll_widgets:
            widgets = roll_widget.property("roll_data_widgets")
            data = {
                "roll_number": widgets["roll_number"],
                "completed": widgets["check_box"].isChecked(),
                "initials": widgets["initials"].text(),
                "notes": widgets["notes"].text(),
                "printer": widgets["printer"].currentText(),
                "timestamp": widgets["timestamp"].text()
            }
            updated_roll_data.append(data)
            
        try:
            with open(self.roll_tracker_file, 'w') as f:
                json.dump(updated_roll_data, f, indent=4)
            QMessageBox.information(self, "Success", "Roll tracker data saved successfully.")
            self.update_progress()
        except IOError as e:
            self.show_error_message(f"Error saving roll tracker data: {e}")

    def update_progress(self):
        """Update the progress label based on completed rolls."""
        completed_rolls = 0
        total_rolls = len(self.roll_widgets)
        for roll_widget in self.roll_widgets:
            widgets = roll_widget.property("roll_data_widgets")
            if widgets["check_box"].isChecked():
                completed_rolls += 1
        self.progress_label.setText(f"Rolls Completed: {completed_rolls} / {total_rolls}")

    def show_error_message(self, message):
        """Displays an error message in the widget area."""
        for i in reversed(range(self.layout().count())): 
            widgetToRemove = self.layout().itemAt(i).widget()
            if widgetToRemove is not None:
                widgetToRemove.deleteLater()

        error_label = QLabel(message)
        error_label.setWordWrap(True)
        error_label.setStyleSheet("color: red; font-weight: bold;")
        self.layout().addWidget(error_label) 