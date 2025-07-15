import os
import json
import math
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QLineEdit, QCheckBox, QComboBox, QTextEdit, QGroupBox,
    QMessageBox, QGridLayout, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QIcon
from src.utils.epc_conversion import generate_epc
from src.utils.file_utils import resource_path
from filelock import FileLock, Timeout

class InteractiveRollTrackerDialog(QDialog):
    """Interactive Roll Tracker - A standalone window for tracking roll completion progress."""
    
    def __init__(self, job_data, parent=None):
        super().__init__(parent)
        self.job_data = job_data
        self.roll_widgets = []
        
        # Make this dialog non-modal
        self.setModal(False)
        
        # Find job folder and set up data file path
        self.job_folder_path = self.find_job_directory()
        if self.job_folder_path:
            self.roll_tracker_file = os.path.join(self.job_folder_path, "interactive_roll_tracker_data.json")
        else:
            self.roll_tracker_file = None

        # Set up auto-save timer and file monitoring
        from PySide6.QtCore import QTimer, QFileSystemWatcher
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_data)
        self.auto_save_timer.start(5000)  # Auto-save every 5 seconds for better responsiveness
        
        # Set up file system watcher for live updates from other users
        self.file_watcher = QFileSystemWatcher()
        if self.roll_tracker_file and os.path.exists(os.path.dirname(self.roll_tracker_file)):
            self.file_watcher.addPath(os.path.dirname(self.roll_tracker_file))
            self.file_watcher.fileChanged.connect(self.on_tracker_file_changed)
            
        # Refresh timer to debounce rapid file changes
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_from_file)

        self.setup_ui()
        self.load_printers()
        self.validate_and_calculate_roll_data()
        self.load_roll_tracker_data()

    def find_job_directory(self):
        """Find the correct job directory."""
        if 'job_folder_path' in self.job_data and os.path.exists(self.job_data['job_folder_path']):
            return self.job_data['job_folder_path']
        return self.job_data.get("active_source_folder_path")

    def setup_ui(self):
        """Set up the user interface."""
        job_ticket = self.job_data.get('Job Ticket#', self.job_data.get('Ticket#', 'Unknown'))
        customer = self.job_data.get('Customer', 'Unknown')
        self.setWindowTitle(f"Roll Tracker - {customer} - #{job_ticket}")
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # Compact header
        header_frame = self.create_header()
        main_layout.addWidget(header_frame)

        # Compact scroll area for rolls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_content = QWidget()
        self.rolls_layout = QVBoxLayout(scroll_content)
        self.rolls_layout.setSpacing(2)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Compact footer
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        self.save_button = QPushButton("Save")
        self.save_button.setMaximumWidth(80)
        self.save_button.clicked.connect(self.save_roll_tracker_data)
        footer_layout.addWidget(self.save_button)
        
        main_layout.addLayout(footer_layout)

    def create_header(self):
        """Create compact header with job info and progress."""
        header_frame = QFrame()
        header_frame.setMaximumHeight(40)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-bottom: 1px solid #333333;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
        layout = QHBoxLayout(header_frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Job info on left
        job_ticket = self.job_data.get('Job Ticket#', self.job_data.get('Ticket#', 'Unknown'))
        customer = self.job_data.get('Customer', 'Unknown')
        upc = self.job_data.get('UPC Number', 'N/A')
        
        info_label = QLabel(f"{customer} | UPC: {upc}")
        font = QFont()
        font.setBold(True)
        info_label.setFont(font)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # Progress on right
        self.progress_label = QLabel("Progress: 0/0")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.progress_label)
        
        return header_frame

    def load_printers(self):
        """Load printer names."""
        self.printers = ["Select Printer"]
        try:
            printer_file = resource_path(os.path.join("data", "Printers.txt"))
            if os.path.exists(printer_file):
                with open(printer_file, 'r') as f:
                    self.printers.extend([line.strip() for line in f if line.strip()])
        except Exception as e:
            print(f"Error loading printers: {e}")

    def validate_and_calculate_roll_data(self):
        """Validate job data and calculate roll data with EPC ranges."""
        self.roll_data = []
        
        try:
            # Validate required job data
            upc = self.job_data.get('UPC Number', '')
            start_serial = int(self.job_data.get('Serial Number', 1))
            quantity = int(self.job_data.get('Quantity', self.job_data.get('Qty', 0)))
            lpr = int(self.job_data.get('LPR', 100))
            
            if not upc:
                QMessageBox.warning(self, "Missing Data", "Job is missing UPC Number. Roll tracker may not display EPC ranges correctly.")
            
            if quantity <= 0:
                QMessageBox.critical(self, "Invalid Data", "Job quantity must be greater than 0.")
                return
                
            if lpr <= 0:
                QMessageBox.critical(self, "Invalid Data", "Labels per roll (LPR) must be greater than 0.")
                return
            
            # Calculate rolls with job metadata
            num_rolls = math.ceil(quantity / lpr)
            current_serial = start_serial
            
            # Store job validation info in tracker metadata
            self.tracker_metadata = {
                'job_ticket': self.job_data.get('Job Ticket#', self.job_data.get('Ticket#', 'Unknown')),
                'customer': self.job_data.get('Customer', 'Unknown'),
                'upc': upc,
                'total_quantity': quantity,
                'lpr': lpr,
                'start_serial': start_serial,
                'num_rolls': num_rolls,
                'created_timestamp': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            
            for roll_num in range(1, num_rolls + 1):
                remaining_qty = quantity - (roll_num - 1) * lpr
                roll_qty = min(lpr, remaining_qty)
                
                start_epc = generate_epc(upc, current_serial) if upc else "N/A"
                end_epc = generate_epc(upc, current_serial + roll_qty - 1) if upc else "N/A"
                
                roll_info = {
                    'roll_number': roll_num,
                    'quantity': roll_qty,
                    'start_serial': current_serial,
                    'end_serial': current_serial + roll_qty - 1,
                    'start_epc': start_epc,
                    'end_epc': end_epc,
                    'status': 'Not Started',
                    'completed': False,
                    'initials': '',
                    'printer': '',
                    'notes': '',
                    'notes_history': [],
                    'timestamps': {},
                    'created_timestamp': datetime.now().isoformat()
                }
                
                self.roll_data.append(roll_info)
                current_serial += roll_qty
                
        except (ValueError, TypeError) as e:
            QMessageBox.critical(self, "Data Error", f"Error processing job data: {e}")
            print(f"Error calculating roll data: {e}")

    def load_roll_tracker_data(self):
        """Load existing data with validation or create new."""
        if not self.roll_tracker_file:
            self.populate_rolls()
            self.update_progress()
            return

        existing_data = {}
        saved_metadata = {}
        
        if os.path.exists(self.roll_tracker_file):
            try:
                with open(self.roll_tracker_file, 'r') as f:
                    saved_file = json.load(f)
                
                # Handle both old format (direct list) and new format (with metadata)
                if isinstance(saved_file, list):
                    # Old format - convert to new format
                    print("Converting old roll tracker format to new format...")
                    existing_data = {item['roll_number']: item for item in saved_file}
                elif isinstance(saved_file, dict) and 'rolls' in saved_file:
                    # New format with metadata
                    saved_metadata = saved_file.get('metadata', {})
                    existing_data = {item['roll_number']: item for item in saved_file['rolls']}
                    
                    # Validate saved data matches current job
                    if not self.validate_saved_data(saved_metadata):
                        reply = QMessageBox.question(
                            self, "Data Mismatch", 
                            "The saved roll tracker data doesn't match the current job specifications. "
                            "Would you like to regenerate the roll tracker?\n\n"
                            "Choose 'Yes' to regenerate (recommended) or 'No' to keep existing data.",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            existing_data = {}
                            saved_metadata = {}
                        
            except (json.JSONDecodeError, IOError) as e:
                QMessageBox.warning(self, "Load Error", f"Error loading saved roll tracker data: {e}")
                print(f"Error loading data: {e}")

        # Merge saved data with calculated data
        for roll_info in self.roll_data:
            roll_num = roll_info['roll_number']
            if roll_num in existing_data:
                saved_roll = existing_data[roll_num]
                # Preserve tracking data but update calculated fields
                roll_info.update({
                    'status': saved_roll.get('status', 'Not Started'),
                    'completed': saved_roll.get('completed', False),
                    'initials': saved_roll.get('initials', ''),
                    'printer': saved_roll.get('printer', ''),
                    'notes': saved_roll.get('notes', ''),
                    'notes_history': saved_roll.get('notes_history', []),
                    'timestamps': saved_roll.get('timestamps', {})
                })

        self.populate_rolls()
        self.update_progress()
        
        # Auto-save to update format if needed
        self.auto_save_data()
    
    def validate_saved_data(self, saved_metadata):
        """Validate that saved data matches current job specifications."""
        if not saved_metadata:
            return True  # No metadata to validate against
        
        current_metadata = getattr(self, 'tracker_metadata', {})
        
        # Check critical job parameters
        validation_fields = ['upc', 'total_quantity', 'lpr', 'start_serial', 'num_rolls']
        
        for field in validation_fields:
            saved_value = saved_metadata.get(field)
            current_value = current_metadata.get(field)
            
            if saved_value != current_value:
                print(f"Validation failed for {field}: saved={saved_value}, current={current_value}")
                return False
        
        return True

    def populate_rolls(self):
        """Create roll widgets."""
        for widget in self.roll_widgets:
            widget.deleteLater()
        self.roll_widgets = []

        for roll_info in self.roll_data:
            roll_widget = self.create_roll_widget(roll_info)
            self.rolls_layout.addWidget(roll_widget)
            self.roll_widgets.append(roll_widget)

    def create_roll_widget(self, roll_info):
        """Create refined widget for a single roll."""
        roll_frame = QFrame()
        roll_frame.setFrameShape(QFrame.Shape.Box)
        roll_frame.setMaximumHeight(65)
        roll_frame.setMinimumHeight(65)
        
        # Simplified status-based styling
        status = roll_info.get('status', 'Not Started')
        if status == 'Completed':
            bg_color = "#1a3d2e"  # Subtle dark green
            border_color = "#2e5d48"
        elif status == 'Running':
            bg_color = "#1a2e3d"  # Subtle dark blue
            border_color = "#2e485d"
        else:  # Not Started or Paused
            bg_color = "#2d2d30"  # Standard dark
            border_color = "#404040"

        roll_frame.setStyleSheet(f"""
            QFrame {{ 
                border: 1px solid {border_color}; 
                background-color: {bg_color};
                margin: 1px;
                border-radius: 4px;
            }}
            QLabel {{ 
                color: #ffffff;
                background-color: transparent;
            }}
            QPushButton {{
                background-color: transparent;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #404040;
            }}
            QPushButton:checked {{
                background-color: #0078d4;
                border-color: #0078d4;
            }}
        """)
        
        layout = QHBoxLayout(roll_frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(15)
        
        # Left side: Roll number and data sections
        left_layout = QHBoxLayout()
        left_layout.setSpacing(15)
        
        # Roll number section
        roll_section = QVBoxLayout()
        roll_section.setSpacing(2)
        
        roll_header = QLabel("ROLL")
        roll_header.setStyleSheet("color: #606060; font-size: 8px; font-weight: bold;")
        roll_section.addWidget(roll_header)
        
        roll_label = QLabel(f"{roll_info['roll_number']}")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        roll_label.setFont(font)
        roll_label.setStyleSheet("color: #ffffff;")
        roll_section.addWidget(roll_label)
        
        left_layout.addLayout(roll_section)
        
        # EPC section
        epc_section = QVBoxLayout()
        epc_section.setSpacing(2)
        
        epc_header = QLabel("EPC RANGE")
        epc_header.setStyleSheet("color: #606060; font-size: 8px; font-weight: bold;")
        epc_section.addWidget(epc_header)
        
        start_epc_short = roll_info['start_epc'][-8:] if len(roll_info['start_epc']) > 8 else roll_info['start_epc']
        end_epc_short = roll_info['end_epc'][-8:] if len(roll_info['end_epc']) > 8 else roll_info['end_epc']
        epc_label = QLabel(f"{start_epc_short} → {end_epc_short}")
        epc_font = QFont("Consolas", 10)
        epc_label.setFont(epc_font)
        epc_label.setStyleSheet("color: #a0a0a0;")
        epc_section.addWidget(epc_label)
        
        left_layout.addLayout(epc_section)
        
        # Serial number section
        serial_section = QVBoxLayout()
        serial_section.setSpacing(2)
        
        serial_header = QLabel("SERIAL RANGE")
        serial_header.setStyleSheet("color: #606060; font-size: 8px; font-weight: bold;")
        serial_section.addWidget(serial_header)
        
        start_serial = roll_info.get('start_serial', 0)
        end_serial = roll_info.get('end_serial', 0)
        if 'start_serial' not in roll_info:
            # Calculate serials if not stored
            quantity = roll_info['quantity']
            start_serial = int(self.job_data.get('Serial Number', 1))
            # Calculate the starting serial for this specific roll
            for i, r in enumerate(self.roll_data):
                if r['roll_number'] == roll_info['roll_number']:
                    # Sum quantities of previous rolls
                    prev_qty = sum(prev_roll['quantity'] for prev_roll in self.roll_data[:i])
                    start_serial += prev_qty
                    end_serial = start_serial + quantity - 1
                    roll_info['start_serial'] = start_serial
                    roll_info['end_serial'] = end_serial
                    break
        
        serial_label = QLabel(f"{start_serial:,} → {end_serial:,}")
        serial_font = QFont("Consolas", 10)
        serial_label.setFont(serial_font)
        serial_label.setStyleSheet("color: #a0a0a0;")
        serial_section.addWidget(serial_label)
        
        left_layout.addLayout(serial_section)
        
        # Quantity section
        qty_section = QVBoxLayout()
        qty_section.setSpacing(2)
        
        qty_header = QLabel("QTY")
        qty_header.setStyleSheet("color: #606060; font-size: 8px; font-weight: bold;")
        qty_section.addWidget(qty_header)
        
        qty_label = QLabel(f"{roll_info['quantity']:,}")
        qty_label.setStyleSheet("color: #808080; font-size: 11px; font-weight: bold;")
        qty_section.addWidget(qty_label)
        
        left_layout.addLayout(qty_section)
        
        layout.addLayout(left_layout)
        layout.addStretch()
        
        # Center: Simplified status indicator
        status_widget = self.create_status_indicator(roll_info, roll_frame)
        layout.addWidget(status_widget)
        
        layout.addStretch()
        
        # Right side: Action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # Start/Pause/Resume button with icons
        if status == 'Not Started':
            action_btn = QPushButton("START")
            # Could add a start/play icon here if you have one, otherwise keep text
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    border: none;
                    padding: 4px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
            """)
            action_btn.clicked.connect(lambda: self.start_roll(roll_info, roll_frame))
        elif status == 'Running':
            action_btn = QPushButton()
            pause_icon_path = resource_path(os.path.join("src", "icons", "pause.png"))
            if os.path.exists(pause_icon_path):
                action_btn.setIcon(QIcon(pause_icon_path))
                action_btn.setToolTip("Pause Roll")
            else:
                action_btn.setText("PAUSE")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d4a007;
                    border: none;
                    padding: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e6b100;
                }
            """)
            action_btn.setMaximumWidth(40)
            action_btn.clicked.connect(lambda: self.pause_roll(roll_info, roll_frame))
        elif status == 'Paused':
            action_btn = QPushButton()
            resume_icon_path = resource_path(os.path.join("src", "icons", "resume.png"))
            if os.path.exists(resume_icon_path):
                action_btn.setIcon(QIcon(resume_icon_path))
                action_btn.setToolTip("Resume Roll")
            else:
                action_btn.setText("RESUME")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    border: none;
                    padding: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1084d8;
                }
            """)
            action_btn.setMaximumWidth(40)
            action_btn.clicked.connect(lambda: self.resume_roll(roll_info, roll_frame))
        else:  # Completed - show check icon
            action_btn = QPushButton()
            check_icon_path = resource_path(os.path.join("src", "icons", "check.png"))
            if os.path.exists(check_icon_path):
                action_btn.setIcon(QIcon(check_icon_path))
            else:
                action_btn.setText("✓")  # Fallback checkmark
            action_btn.setEnabled(False)
            action_btn.setMaximumWidth(35)
            action_btn.setToolTip(f"Completed by: {roll_info.get('initials', 'Unknown')}")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2e5d48;
                    border: none;
                    padding: 4px;
                    color: #a0a0a0;
                }
            """)
        
        # Always add the action button (it's either an action or completion indicator)
        actions_layout.addWidget(action_btn)
        
        # Complete button (only if running or paused) - using stop icon
        if status in ['Running', 'Paused']:
            complete_btn = QPushButton()
            stop_icon_path = resource_path(os.path.join("src", "icons", "stop.png"))
            if os.path.exists(stop_icon_path):
                complete_btn.setIcon(QIcon(stop_icon_path))
                complete_btn.setToolTip("Finish Roll")
            else:
                complete_btn.setText("FINISH")
            complete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2e5d48;
                    border: none;
                    padding: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3c8c61;
                }
            """)
            complete_btn.setMaximumWidth(40)
            complete_btn.clicked.connect(lambda: self.complete_roll(roll_info, roll_frame))
            actions_layout.addWidget(complete_btn)
        
        # Notes button (always visible) - using PNG icon
        notes_btn = QPushButton()
        notes_icon_path = resource_path(os.path.join("src", "icons", "note.png"))
        if os.path.exists(notes_icon_path):
            notes_btn.setIcon(QIcon(notes_icon_path))
        else:
            notes_btn.setText("📝")  # Fallback emoji
        notes_btn.setMaximumWidth(30)
        notes_btn.setMaximumHeight(30)
        notes_btn.setToolTip("View/Add Notes")
        actions_layout.addWidget(notes_btn)
        notes_btn.clicked.connect(lambda: self.open_notes_dialog(roll_info))
        
        layout.addLayout(actions_layout)
        
        # Store references
        roll_frame.setProperty("roll_data", {
            "roll_info": roll_info
        })
        
        return roll_frame
    
    def create_status_indicator(self, roll_info, roll_frame):
        """Create a simple status indicator."""
        status = roll_info.get('status', 'Not Started')
        
        if status == 'Not Started':
            indicator = QLabel("⚪ Ready")
            indicator.setStyleSheet("color: #808080; font-size: 11px;")
        elif status == 'Running':
            indicator = QLabel("🔵 Running")
            indicator.setStyleSheet("color: #0078d4; font-size: 11px; font-weight: bold;")
        elif status == 'Paused':
            indicator = QLabel("🟡 Paused")
            indicator.setStyleSheet("color: #d4a007; font-size: 11px; font-weight: bold;")
        else:  # Completed
            indicator = QLabel("🟢 Done")
            indicator.setStyleSheet("color: #2e5d48; font-size: 11px; font-weight: bold;")
        
        return indicator
    
    def start_roll(self, roll_info, roll_frame):
        """Start a roll."""
        timestamp = datetime.now().strftime("%H:%M")
        note_text = f"[{timestamp}] STARTED"
        
        if 'notes_history' not in roll_info:
            roll_info['notes_history'] = []
        roll_info['notes_history'].append(note_text)
        
        roll_info['status'] = 'Running'
        roll_info['timestamps']['started'] = datetime.now().isoformat()
        
        # Immediate save for real-time updates
        self.auto_save_data()
        
        self.rebuild_roll_widget(roll_info, roll_frame)
        self.update_progress()
    
    def pause_roll(self, roll_info, roll_frame):
        """Pause a roll."""
        timestamp = datetime.now().strftime("%H:%M")
        note_text = f"[{timestamp}] PAUSED"
        
        if 'notes_history' not in roll_info:
            roll_info['notes_history'] = []
        roll_info['notes_history'].append(note_text)
        
        roll_info['status'] = 'Paused'
        roll_info['timestamps']['paused'] = datetime.now().isoformat()
        
        # Immediate save for real-time updates
        self.auto_save_data()
        
        self.rebuild_roll_widget(roll_info, roll_frame)
        self.update_progress()
    
    def resume_roll(self, roll_info, roll_frame):
        """Resume a paused roll."""
        timestamp = datetime.now().strftime("%H:%M")
        note_text = f"[{timestamp}] RESUMED"
        
        if 'notes_history' not in roll_info:
            roll_info['notes_history'] = []
        roll_info['notes_history'].append(note_text)
        
        roll_info['status'] = 'Running'
        roll_info['timestamps']['resumed'] = datetime.now().isoformat()
        
        # Immediate save for real-time updates
        self.auto_save_data()
        
        self.rebuild_roll_widget(roll_info, roll_frame)
        self.update_progress()
    
    def complete_roll(self, roll_info, roll_frame):
        """Handle roll completion with printer assignment."""
        from PySide6.QtWidgets import QInputDialog
        
        # Get initials
        initials, ok1 = QInputDialog.getText(self, "Complete Roll", "Enter your initials:")
        if not ok1 or not initials.strip():
            return
        
        # Get printer
        printer, ok2 = QInputDialog.getItem(self, "Complete Roll", "Select printer used:", 
                                          [p for p in self.printers if p != "Select Printer"], 0, False)
        if not ok2 or not printer:
            return
        
        # Add completion note
        timestamp = datetime.now().strftime("%H:%M")
        completion_note = f"[{timestamp}] COMPLETED by {initials.strip()} on {printer}"
        
        if 'notes_history' not in roll_info:
            roll_info['notes_history'] = []
        roll_info['notes_history'].append(completion_note)
        
        # Update roll info
        roll_info['status'] = 'Completed'
        roll_info['completed'] = True
        roll_info['initials'] = initials.strip()
        roll_info['printer'] = printer
        roll_info['completion_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        roll_info['timestamps']['completed'] = datetime.now().isoformat()
        
        # Immediate save for real-time updates - completion is critical
        self.auto_save_data()
        
        # Rebuild this roll widget to show completed state
        self.rebuild_roll_widget(roll_info, roll_frame)
        self.update_progress()
    
    def rebuild_roll_widget(self, roll_info, old_frame):
        """Rebuild a single roll widget."""
        # Find the position of the old frame
        index = -1
        for i in range(self.rolls_layout.count()):
            if self.rolls_layout.itemAt(i).widget() == old_frame:
                index = i
                break
        
        if index >= 0:
            # Remove old widget
            self.rolls_layout.removeWidget(old_frame)
            old_frame.deleteLater()
            
            # Create new widget
            new_widget = self.create_roll_widget(roll_info)
            self.rolls_layout.insertWidget(index, new_widget)
            
            # Update the roll_widgets list
            for i, widget in enumerate(self.roll_widgets):
                if widget == old_frame:
                    self.roll_widgets[i] = new_widget
                    break
    
    def open_notes_dialog(self, roll_info):
        """Open notes dialog for viewing/adding notes."""
        dialog = NotesDialog(roll_info, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Notes were updated in the dialog
            pass

    def update_progress(self):
        """Update progress display."""
        total_rolls = len(self.roll_data)
        completed_rolls = sum(1 for roll in self.roll_data if roll.get('completed', False))
        percentage = (completed_rolls / total_rolls) * 100 if total_rolls > 0 else 0
        
        self.progress_label.setText(f"Progress: {completed_rolls}/{total_rolls} completed ({percentage:.1f}%)")

    def save_roll_tracker_data(self):
        """Save current data with metadata."""
        if not self.roll_tracker_file:
            QMessageBox.warning(self, "Error", "Cannot save: No file path set.")
            return

        # Update metadata timestamp
        if hasattr(self, 'tracker_metadata'):
            self.tracker_metadata['last_updated'] = datetime.now().isoformat()
            
            # Calculate completion statistics
            completed_rolls = sum(1 for roll in self.roll_data if roll.get('completed', False))
            total_rolls = len(self.roll_data)
            self.tracker_metadata['completion_stats'] = {
                'completed_rolls': completed_rolls,
                'total_rolls': total_rolls,
                'completion_percentage': (completed_rolls / total_rolls * 100) if total_rolls > 0 else 0
            }

        # Prepare data structure with metadata
        save_data = {
            'metadata': getattr(self, 'tracker_metadata', {}),
            'rolls': self.roll_data,
            'version': '1.0'
        }

        try:
            with open(self.roll_tracker_file, 'w') as f:
                json.dump(save_data, f, indent=4)
            QMessageBox.information(self, "Success", "Roll tracker data saved!")
        except IOError as e:
            QMessageBox.critical(self, "Error", f"Error saving: {e}")
    
    def auto_save_data(self):
        """Auto-save data without showing success message."""
        if not self.roll_tracker_file:
            return

        try:
            # Update metadata timestamp and add user context
            if hasattr(self, 'tracker_metadata'):
                self.tracker_metadata['last_updated'] = datetime.now().isoformat()
                self.tracker_metadata['last_updated_by'] = os.getenv('USERNAME', 'Unknown User')
                self.tracker_metadata['last_updated_machine'] = os.getenv('COMPUTERNAME', 'Unknown Machine')
                
                # Calculate completion statistics
                completed_rolls = sum(1 for roll in self.roll_data if roll.get('completed', False))
                total_rolls = len(self.roll_data)
                running_rolls = sum(1 for roll in self.roll_data if roll.get('status') == 'Running')
                paused_rolls = sum(1 for roll in self.roll_data if roll.get('status') == 'Paused')
                
                self.tracker_metadata['completion_stats'] = {
                    'completed_rolls': completed_rolls,
                    'running_rolls': running_rolls,
                    'paused_rolls': paused_rolls,
                    'not_started_rolls': total_rolls - completed_rolls - running_rolls - paused_rolls,
                    'total_rolls': total_rolls,
                    'completion_percentage': (completed_rolls / total_rolls * 100) if total_rolls > 0 else 0
                }

            # Prepare data structure with metadata
            save_data = {
                'metadata': getattr(self, 'tracker_metadata', {}),
                'rolls': self.roll_data,
                'version': '1.0'
            }

            with open(self.roll_tracker_file, 'w') as f:
                json.dump(save_data, f, indent=4)
            print(f"Auto-saved roll tracker data at {datetime.now().strftime('%H:%M:%S')}")
        except IOError as e:
            print(f"Auto-save failed: {e}")

    def on_tracker_file_changed(self, path):
        """Handle changes to the tracker file from other users."""
        print(f"Roll tracker file changed detected: {path}")
        # Use timer to debounce rapid changes (wait 2 seconds after last change)
        self.refresh_timer.start(2000)
    
    def refresh_from_file(self):
        """Refresh roll tracker data from file changes by other users."""
        if not self.roll_tracker_file or not os.path.exists(self.roll_tracker_file):
            return
        
        try:
            print("Refreshing roll tracker from file changes...")
            
            # Store current UI state to preserve user's current focus
            current_notes_text = ""
            
            # Load updated data from file
            with open(self.roll_tracker_file, 'r') as f:
                saved_file = json.load(f)
            
            if isinstance(saved_file, dict) and 'rolls' in saved_file:
                updated_rolls = {item['roll_number']: item for item in saved_file['rolls']}
                
                # Update our data while preserving UI state
                for roll_info in self.roll_data:
                    roll_num = roll_info['roll_number']
                    if roll_num in updated_rolls:
                        updated_roll = updated_rolls[roll_num]
                        # Update tracking data from other users
                        roll_info.update({
                            'status': updated_roll.get('status', roll_info['status']),
                            'completed': updated_roll.get('completed', roll_info['completed']),
                            'initials': updated_roll.get('initials', roll_info['initials']),
                            'printer': updated_roll.get('printer', roll_info['printer']),
                            'notes': updated_roll.get('notes', roll_info['notes']),
                            'notes_history': updated_roll.get('notes_history', roll_info['notes_history']),
                            'timestamps': updated_roll.get('timestamps', roll_info['timestamps'])
                        })
                
                # Refresh the UI to show updates
                self.populate_rolls()
                self.update_progress()
                
                print("Roll tracker refreshed from external changes")
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error refreshing from file: {e}")
    
    def closeEvent(self, event):
        """Handle close event."""
        # Stop timers
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        if hasattr(self, 'file_watcher'):
            self.file_watcher.deleteLater()
        
        # Final save
        self.auto_save_data()
        event.accept()


class NotesDialog(QDialog):
    """Dialog for viewing and adding notes to a roll."""
    
    def __init__(self, roll_info, parent=None):
        super().__init__(parent)
        self.roll_info = roll_info
        self.parent_tracker = parent  # Reference to main tracker for saving
        self.setWindowTitle(f"Notes - Roll {roll_info['roll_number']}")
        self.setMinimumSize(400, 300)
        self.resize(500, 400)
        
        # Set dark theme styles
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit {
                background-color: #2d2d30;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
            }
            QTextEdit:read-only {
                background-color: #252526;
            }
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cc1;
            }
        """)
        
        self.setup_ui()
        self.load_notes()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"Roll {self.roll_info['roll_number']} Notes")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title.setFont(font)
        layout.addWidget(title)
        
        # Notes history (read-only)
        history_label = QLabel("Notes History:")
        layout.addWidget(history_label)
        
        self.notes_history = QTextEdit()
        self.notes_history.setReadOnly(True)
        self.notes_history.setMaximumHeight(200)
        layout.addWidget(self.notes_history)
        
        # Add new note
        add_note_label = QLabel("Add New Note:")
        layout.addWidget(add_note_label)
        
        self.new_note_edit = QTextEdit()
        self.new_note_edit.setMaximumHeight(80)
        self.new_note_edit.setPlaceholderText("Type your note here...")
        layout.addWidget(self.new_note_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        add_btn = QPushButton("Add Note")
        add_btn.clicked.connect(self.add_note)
        button_layout.addWidget(add_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_notes(self):
        """Load and display notes history with enhanced formatting."""
        notes_history = self.roll_info.get('notes_history', [])
        if notes_history:
            # Format notes with better readability
            formatted_notes = []
            for note in notes_history:
                # Add extra spacing for EPC-specific notes
                if '@EPC:' in note:
                    formatted_notes.append(f"📍 {note}")
                else:
                    formatted_notes.append(f"   {note}")
            
            self.notes_history.setText('\n'.join(formatted_notes))
        else:
            self.notes_history.setText("No notes yet.\n\nClick 'Add Note' to record events or observations for this roll.")
    
    def add_note(self):
        """Add a new note with timestamp and EPC position."""
        note_text = self.new_note_edit.toPlainText().strip()
        if not note_text:
            return
        
        # Prompt for EPC position
        from PySide6.QtWidgets import QInputDialog
        epc_last5, ok = QInputDialog.getText(
            self, 
            "EPC Position", 
            "Enter the last 5 characters of the EPC where this note applies:\n\n"
            f"Roll {self.roll_info['roll_number']} EPC Range:\n"
            f"{self.roll_info.get('start_epc', 'N/A')} → {self.roll_info.get('end_epc', 'N/A')}\n\n"
            "Last 5 characters of EPC:",
            text=""
        )
        
        if not ok:
            return  # User cancelled
        
        timestamp = datetime.now().strftime("%H:%M")
        
        # Format note with EPC position if provided
        if epc_last5.strip():
            formatted_note = f"[{timestamp}] @EPC:{epc_last5.strip().upper()} - {note_text}"
        else:
            formatted_note = f"[{timestamp}] {note_text}"
        
        if 'notes_history' not in self.roll_info:
            self.roll_info['notes_history'] = []
        
        self.roll_info['notes_history'].append(formatted_note)
        
        # Trigger immediate save in parent tracker for real-time updates
        if hasattr(self.parent_tracker, 'auto_save_data'):
            self.parent_tracker.auto_save_data()
        
        # Refresh the display
        self.load_notes()
        self.new_note_edit.clear()
        
        QMessageBox.information(self, "Note Added", "Note added successfully!") 