from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFrame, QScrollArea, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
import os

from src.widgets.database_generator_dialog import DatabaseGeneratorDialog
from src.widgets.checklist_generator_dialog import ChecklistGeneratorDialog
from src.widgets.roll_tracker_dialog import RollTrackerDialog
from src.widgets.upc_validator_dialog import UPCValidatorDialog
from src.widgets.epc_validator_dialog import EPCValidatorDialog
from src.widgets.global_search_dialog import GlobalSearchDialog


class ToolCard(QFrame):
    """Individual tool card widget for displaying a tool with icon and description"""
    tool_clicked = Signal(str)  # Emits tool name when clicked
    
    def __init__(self, tool_name, description, icon_path=None, parent=None):
        super().__init__(parent)
        self.tool_name = tool_name
        self.setup_ui(description, icon_path)
        
    def setup_ui(self, description, icon_path):
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            ToolCard {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 15px;
            }
            ToolCard:hover {
                background-color: #353535;
                border: 1px solid #4a4a4a;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Tool name
        name_label = QLabel(self.tool_name)
        name_font = QFont()
        name_font.setPointSize(12)
        name_font.setBold(True)
        name_label.setFont(name_font)
        layout.addWidget(name_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888888;")
        layout.addWidget(desc_label)
        
        layout.addStretch()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.tool_clicked.emit(self.tool_name)


class ToolsPageWidget(QWidget):
    def __init__(self, base_path=None, parent=None):
        super().__init__(parent)
        self.base_path = base_path if base_path else os.path.dirname(os.path.abspath(__file__))
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the tools page UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Tools")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Subtitle
        subtitle_label = QLabel("Essential workflow tools for encoding and data management")
        subtitle_label.setStyleSheet("color: #888888;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Create scroll area for tools
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Tools container
        tools_container = QWidget()
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setSpacing(20)
        
        # Primary Tools Section
        primary_section = self.create_tool_section(
            "Primary Tools",
            [
                ("Database Generator", "Generate EPC database files with custom parameters and serial ranges"),
                ("Roll Tracker", "Track and manage label roll inventory and usage statistics"),
                ("Checklist", "Create and manage job checklists with customizable templates"),
                ("Global Search", "Search across all jobs, archives, and data files for specific information")
            ]
        )
        tools_layout.addWidget(primary_section)
        
        # Validation Tools Section
        validation_section = self.create_tool_section(
            "Validation Tools",
            [
                ("UPC Validator", "Validate UPC codes for format compliance and check digit accuracy"),
                ("EPC Validator", "Validate EPC codes and perform round-trip UPC conversion testing")
            ]
        )
        tools_layout.addWidget(validation_section)
        
        # Deprecated Tools Section
        deprecated_section = self.create_deprecated_tools_section()
        tools_layout.addWidget(deprecated_section)
        
        tools_layout.addStretch()
        
        scroll_area.setWidget(tools_container)
        main_layout.addWidget(scroll_area)
        
    def create_tool_section(self, section_title, tools):
        """Create a section of tool cards"""
        section_group = QGroupBox(section_title)
        section_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        
        # Grid layout for tool cards
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(10, 20, 10, 10)
        
        # Add tool cards to grid (2 columns)
        for i, (tool_name, description) in enumerate(tools):
            row = i // 2
            col = i % 2
            
            tool_card = ToolCard(tool_name, description)
            tool_card.tool_clicked.connect(self.handle_tool_click)
            grid_layout.addWidget(tool_card, row, col)
        
        section_group.setLayout(grid_layout)
        return section_group
    
    def create_deprecated_tools_section(self):
        """Create the deprecated tools section"""
        section_group = QGroupBox("Deprecated Tools")
        section_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #888888;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #888888;
            }
        """)
        
        # Layout for deprecated tools
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Placeholder message
        placeholder_label = QLabel("Deprecated tools will be listed here.\nThese are legacy tools that are no longer actively maintained.")
        placeholder_label.setStyleSheet("""
            color: #666666;
            font-style: italic;
            padding: 20px;
            text-align: center;
        """)
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setWordWrap(True)
        
        layout.addWidget(placeholder_label)
        section_group.setLayout(layout)
        
        return section_group
        
    def handle_tool_click(self, tool_name):
        """Handle click on a tool card"""
        print(f"Tool clicked: {tool_name}")
        
        # Route to specific tool implementations
        if tool_name == "Database Generator":
            self.open_database_generator()
        elif tool_name == "Roll Tracker":
            self.open_roll_tracker()
        elif tool_name == "Checklist":
            self.open_checklist_tool()
        elif tool_name == "UPC Validator":
            self.open_upc_validator()
        elif tool_name == "EPC Validator":
            self.open_epc_validator()
        elif tool_name == "Global Search":
            self.open_global_search()
        else:
            self.show_tool_placeholder(tool_name)
    
    def show_tool_placeholder(self, tool_name):
        """Show placeholder message for tools not yet implemented"""
        QMessageBox.information(
            self,
            "Tool Coming Soon",
            f"The '{tool_name}' tool is currently under development.\n\n"
            f"This feature will be available in a future update."
        )
    
    # Tool implementation methods - to be developed
    def open_database_generator(self):
        """Open the Database Generator tool"""
        print("Opening Database Generator...")
        dialog = DatabaseGeneratorDialog(self)
        dialog.exec()
        
    def open_roll_tracker(self):
        """Open the Roll Tracker tool"""
        print("Opening Roll Tracker...")
        dialog = RollTrackerDialog(self)
        dialog.exec()
        
    def open_checklist_tool(self):
        """Open the Checklist tool"""
        print("Opening Checklist tool...")
        dialog = ChecklistGeneratorDialog(self.base_path, self)
        dialog.exec()
        
    def open_upc_validator(self):
        """Open the UPC Validator tool"""
        print("Opening UPC Validator...")
        dialog = UPCValidatorDialog(self)
        dialog.exec()
        
    def open_epc_validator(self):
        """Open the EPC Validator tool"""
        print("Opening EPC Validator...")
        dialog = EPCValidatorDialog(self)
        dialog.exec()
        
    def open_global_search(self):
        """Open the Global Search tool"""
        print("Opening Global Search...")
        dialog = GlobalSearchDialog(self)
        dialog.exec() 