from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
import os


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
        subtitle_label = QLabel("Quick access to productivity tools")
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
        
        # Data Processing Tools Section
        data_section = self.create_tool_section(
            "Data Processing Tools",
            [
                ("Batch File Renamer", "Rename multiple files at once using patterns and rules"),
                ("CSV Merger", "Combine multiple CSV files into a single file"),
                ("Data Validator", "Validate data formats and check for errors"),
                ("Excel Processor", "Process and transform Excel files in bulk")
            ]
        )
        tools_layout.addWidget(data_section)
        
        # File Management Tools Section
        file_section = self.create_tool_section(
            "File Management Tools",
            [
                ("Duplicate Finder", "Find and remove duplicate files in directories"),
                ("Folder Organizer", "Organize files into folders based on rules"),
                ("Archive Extractor", "Extract multiple archive files at once"),
                ("File Compressor", "Compress files and folders with various formats")
            ]
        )
        tools_layout.addWidget(file_section)
        
        # Encoding Tools Section
        encoding_section = self.create_tool_section(
            "Encoding Tools",
            [
                ("Barcode Generator", "Generate barcodes in various formats"),
                ("QR Code Creator", "Create QR codes with custom data"),
                ("EPC Calculator", "Calculate and validate EPC codes"),
                ("Serial Number Generator", "Generate sequential serial numbers")
            ]
        )
        tools_layout.addWidget(encoding_section)
        
        # Utility Tools Section
        utility_section = self.create_tool_section(
            "Utility Tools",
            [
                ("Text Replacer", "Find and replace text across multiple files"),
                ("Image Resizer", "Resize multiple images at once"),
                ("PDF Merger", "Combine multiple PDF files"),
                ("Format Converter", "Convert between different file formats")
            ]
        )
        tools_layout.addWidget(utility_section)
        
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
        
    def handle_tool_click(self, tool_name):
        """Handle click on a tool card"""
        print(f"Tool clicked: {tool_name}")
        # This is where you would implement the logic to open specific tools
        # For now, it's a placeholder that can be expanded later
        
        # Example structure for future implementation:
        if tool_name == "Batch File Renamer":
            self.open_batch_renamer()
        elif tool_name == "CSV Merger":
            self.open_csv_merger()
        elif tool_name == "Barcode Generator":
            self.open_barcode_generator()
        # ... etc for other tools
        else:
            print(f"Tool '{tool_name}' not yet implemented")
    
    # Placeholder methods for tools - to be implemented
    def open_batch_renamer(self):
        print("Opening Batch File Renamer...")
        # Future implementation
        
    def open_csv_merger(self):
        print("Opening CSV Merger...")
        # Future implementation
        
    def open_barcode_generator(self):
        print("Opening Barcode Generator...")
        # Future implementation 