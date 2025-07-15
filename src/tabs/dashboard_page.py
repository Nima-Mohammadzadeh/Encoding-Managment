import os
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QProgressBar, QListWidget,
    QListWidgetItem, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QBrush, QPen
import src.config as config


class StatCard(QFrame):
    """A modern statistics card widget with icon and value."""
    clicked = Signal()
    
    def __init__(self, title, value, icon_path=None, color="#0078d4", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Apply styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 6px;
                padding: 8px;
            }}
            QFrame:hover {{
                background-color: #3d3d40;
                border: 1px solid {color};
            }}
        """)
        
        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: #cccccc; font-size: 12px; font-weight: 500;")
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title_label)
        
        # Value container to ensure proper centering
        value_container = QWidget()
        value_layout = QVBoxLayout(value_container)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(0)
        
        # Value
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; line-height: 1.2;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setWordWrap(True)
        value_layout.addWidget(self.value_label)
        
        layout.addWidget(value_container, 1)
        layout.addStretch()
    
    def update_value(self, value):
        """Update the displayed value with animation."""
        self.value_label.setText(str(value))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DeadlineItem(QFrame):
    """A deadline item showing job with due date."""
    clicked = Signal(dict)
    
    def __init__(self, job_data, parent=None):
        super().__init__(parent)
        self.job_data = job_data
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setMinimumHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 6px;
            }
            QFrame:hover {
                background-color: #3d3d40;
                border: 1px solid #0078d4;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # Customer and PO
        header_layout = QHBoxLayout()
        customer_label = QLabel(job_data.get("Customer", "Unknown"))
        customer_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 11px;")
        customer_label.setWordWrap(True)
        header_layout.addWidget(customer_label, 1) # Add stretch factor
        
        # Right-aligned details (Ticket and PO)
        right_details_layout = QVBoxLayout()
        right_details_layout.setSpacing(4)
        
        ticket_number = job_data.get('Job Ticket#', job_data.get('Ticket#', 'N/A'))
        ticket_label = QLabel(f"#{ticket_number}")
        ticket_label.setStyleSheet("color: #cccccc; font-size: 11px; font-weight: bold;")
        ticket_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_details_layout.addWidget(ticket_label)

        po_label = QLabel(f"PO: {job_data.get('PO#', 'N/A')}")
        po_label.setStyleSheet("color: #888888; font-size: 10px;")
        po_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_details_layout.addWidget(po_label)
        
        header_layout.addLayout(right_details_layout)

        layout.addLayout(header_layout)
        
        # Due date and days remaining
        due_date_str = job_data.get("Due Date", "")
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                days_remaining = (due_date - datetime.now()).days
                
                date_layout = QHBoxLayout()
                date_label = QLabel(due_date.strftime("%m/%d/%Y"))
                date_label.setStyleSheet("color: #cccccc; font-size: 10px;")
                date_layout.addWidget(date_label)
                
                # Color code based on urgency
                if days_remaining < 0:
                    color = "#e74c3c"  # Red for overdue
                    status = f"Overdue {abs(days_remaining)}d"
                elif days_remaining == 0:
                    color = "#e74c3c"  # Red for due today
                    status = "Due Today"
                elif days_remaining <= 3:
                    color = "#f39c12"  # Orange for urgent
                    status = f"{days_remaining}d left"
                else:
                    color = "#27ae60"  # Green for normal
                    status = f"{days_remaining}d left"
                
                status_label = QLabel(status)
                status_label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
                date_layout.addStretch()
                date_layout.addWidget(status_label)
                
                layout.addLayout(date_layout)
            except:
                pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.job_data)
        super().mousePressEvent(event)


class DashboardPageWidget(QWidget):
    """Main dashboard widget with statistics and quick actions."""
    
    # Signals
    navigate_to_jobs = Signal()
    navigate_to_archive = Signal()
    navigate_to_tools = Signal()
    navigate_to_reports = Signal()
    create_new_job = Signal()
    open_job_details = Signal(dict)
    
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.active_jobs_source_dir = config.ACTIVE_JOBS_SOURCE_DIR
        self.archive_dir = config.ARCHIVE_DIR
        
        # Setup UI
        self.setup_ui()
        
        # Load initial data
        self.refresh_dashboard()
        
        # Setup auto-refresh timer (every 30 seconds)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(30000)  # 30 seconds
    
    def update_source_directories(self):
        """
        Public method to update the source directories from the config and
        trigger a dashboard refresh.
        """
        print("Dashboard: Updating source directories...")
        self.active_jobs_source_dir = config.ACTIVE_JOBS_SOURCE_DIR
        self.archive_dir = config.ARCHIVE_DIR
        self.refresh_dashboard()

    def setup_ui(self):
        """Setup the dashboard UI layout."""
        # Main layout for the widget
        widget_layout = QVBoxLayout(self)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d30;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #464647;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # Create scrollable content widget
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        
        # Layout for scrollable content
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Dashboard")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0e0e0;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_dashboard)
        header_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(header_layout)

        # Main content area with two columns
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # Left column - Stats Grid and Quick Actions
        left_column = QVBoxLayout()
        left_column.setSpacing(15)

        # Stats Grid (2x2)
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)

        # Create stat cards in 2x2 grid
        self.jobs_backlog_card = StatCard("Jobs in Backlog", "0", color="#0078d4")
        self.jobs_backlog_card.clicked.connect(self.navigate_to_jobs.emit)
        stats_grid.addWidget(self.jobs_backlog_card, 0, 0)

        self.total_backlog_qty_card = StatCard("Total Backlog Qty", "0", color="#f39c12")
        stats_grid.addWidget(self.total_backlog_qty_card, 0, 1)

        self.completed_week_card = StatCard("Completed This Week", "0", color="#27ae60")
        stats_grid.addWidget(self.completed_week_card, 1, 0)

        self.completed_qty_week_card = StatCard("Completed Qty This Week", "0", color="#27ae60")
        stats_grid.addWidget(self.completed_qty_week_card, 1, 1)

        # Add stats grid to left column
        left_column.addLayout(stats_grid)

        # Quick Actions
        actions_frame = QFrame()
        actions_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setSpacing(8)
        
        actions_title = QLabel("Quick Actions")
        actions_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0; margin-bottom: 8px;")
        actions_layout.addWidget(actions_title)
        
        # Create grid layout for action buttons (2 columns)
        actions_grid = QGridLayout()
        actions_grid.setSpacing(6)
        actions_grid.setContentsMargins(0, 0, 0, 0)
        
        # Primary action button (spans both columns)
        new_job_btn = QPushButton("➕ Create New Job")
        new_job_btn.setMinimumHeight(36)
        new_job_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        new_job_btn.clicked.connect(self.create_new_job.emit)
        actions_grid.addWidget(new_job_btn, 0, 0, 1, 2)  # Span 2 columns

        # Secondary action buttons in grid (2x3 grid)
        buttons = [
            ("📋 View Jobs", self.navigate_to_jobs.emit, "#27ae60"),
            ("📁 Archive", self.navigate_to_archive.emit, "#6c757d"),
            ("🔧 Tools", self.navigate_to_tools, "#f39c12"),
            ("📊 Reports", self.navigate_to_reports, "#9b59b6"),
            ("🗃️ Database Gen", self.open_database_generator, "#17a2b8"),
            ("📑 Roll Tracker", self.open_roll_tracker, "#e74c3c")
        ]
        
        for i, (text, callback, color) in enumerate(buttons):
            btn = QPushButton(text)
            btn.setMinimumHeight(28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    padding: 6px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 10px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }}
            """)
            
            # Connect to callback
            if hasattr(callback, 'emit'):
                btn.clicked.connect(callback.emit)
            else:
                btn.clicked.connect(callback)
            
            # Add to grid (3 rows, 2 columns starting from row 1)
            row = 1 + (i // 2)
            col = i % 2
            actions_grid.addWidget(btn, row, col)
        
        actions_layout.addLayout(actions_grid)
        left_column.addWidget(actions_frame)

        # Add stretch to prevent vertical stretching
        left_column.addStretch()

        # Add left column to content layout
        content_layout.addLayout(left_column, 1)

        # Right column - Job Distribution Chart and Upcoming Deadlines
        right_column = QVBoxLayout()
        right_column.setSpacing(15)

        # Interactive Calendar - now takes full available space
        from src.widgets.interactive_calendar import InteractiveCalendarWidget
        
        self.calendar_widget = InteractiveCalendarWidget()
        self.calendar_widget.setMinimumHeight(500)  # Increased height to use the deadlines space
        self.calendar_widget.job_clicked.connect(self.open_job_details.emit)
        right_column.addWidget(self.calendar_widget, 1)  # Allow calendar to expand

        # Add right column to content layout
        content_layout.addLayout(right_column, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # Add scroll area to the main widget layout
        widget_layout.addWidget(scroll_area)
    
    def refresh_dashboard(self):
        """Refresh all dashboard data."""
        print(f"Dashboard refresh triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load job data
        active_jobs = self.load_active_jobs()
        archived_jobs = self.load_archived_jobs()
        
        print(f"Found {len(active_jobs)} active jobs and {len(archived_jobs)} archived jobs")
        
        # Update statistics
        self.update_statistics(active_jobs, archived_jobs)
        
        # Update calendar (now shows all deadline information)
        self.update_calendar(active_jobs)
    
    def load_active_jobs(self):
        """Load active jobs from directory structure (like job_page does)."""
        jobs = []
        
        if not os.path.exists(self.active_jobs_source_dir):
            os.makedirs(self.active_jobs_source_dir, exist_ok=True)
            return jobs
        
        # Scan for job_data.json files in the directory structure
        for root, _, files in os.walk(self.active_jobs_source_dir):
            if "job_data.json" in files:
                job_data_path = os.path.join(root, "job_data.json")
                try:
                    with open(job_data_path, "r", encoding='utf-8') as f:
                        job_data = json.load(f)
                    job_data['active_source_folder_path'] = root
                    jobs.append(job_data)
                except Exception as e:
                    print(f"Error loading job from {job_data_path}: {e}")
        
        return jobs
    
    def load_archived_jobs(self):
        """Load archived jobs from archive directory structure."""
        jobs = []
        
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir, exist_ok=True)
            return jobs
        
        # Scan archive directory for job folders
        for folder_name in os.listdir(self.archive_dir):
            job_folder_path = os.path.join(self.archive_dir, folder_name)
            if os.path.isdir(job_folder_path):
                metadata_path = os.path.join(job_folder_path, 'job_data.json')
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            job_data = json.load(f)
                        job_data['job_folder_path'] = job_folder_path
                        
                        # Debug: Print date fields for first few jobs
                        if len(jobs) < 3:
                            print(f"Archived job {job_data.get('Job Ticket#', 'Unknown')}: "
                                  f"dateArchived={job_data.get('dateArchived', 'N/A')}, "
                                  f"archivedDate={job_data.get('archivedDate', 'N/A')}")
                        
                        jobs.append(job_data)
                    except Exception as e:
                        print(f"Error loading archived job from {metadata_path}: {e}")
        
        return jobs
    
    def update_statistics(self, active_jobs, archived_jobs):
        """Update statistics cards."""
        # Jobs in Backlog (active jobs)
        self.jobs_backlog_card.update_value(len(active_jobs))
        
        # Calculate total backlog quantity
        total_backlog_quantity = 0
        today = datetime.now().date()
        
        for job in active_jobs:
            # Count quantities for backlog
            qty_str = job.get("Quantity", job.get("Qty", "0"))
            if isinstance(qty_str, str):
                qty_str = qty_str.replace(',', '')
            try:
                total_backlog_quantity += int(qty_str)
            except:
                pass
        
        # Format total backlog quantity with commas
        if total_backlog_quantity >= 1000000:
            qty_display = f"{total_backlog_quantity/1000000:.1f}M"
        elif total_backlog_quantity >= 1000:
            qty_display = f"{total_backlog_quantity/1000:.0f}K"
        else:
            qty_display = f"{total_backlog_quantity:,}"
        self.total_backlog_qty_card.update_value(qty_display)
        
        # Completed this week (jobs count) and completed quantity this week
        week_start = today - timedelta(days=today.weekday())  # Monday of current week
        completed_week_count = 0
        completed_week_qty = 0
        
        for job in archived_jobs:
            # Try both dateArchived (timestamp) and archivedDate (date only) fields
            archived_date_str = job.get("dateArchived", job.get("archivedDate", ""))
            if archived_date_str:
                try:
                    # Handle both formats: "YYYY-MM-DD HH:MM:SS" and "YYYY-MM-DD"
                    if ' ' in archived_date_str:
                        # It's a timestamp, extract just the date part
                        archived_date = datetime.strptime(archived_date_str.split()[0], "%Y-%m-%d").date()
                    else:
                        # It's just a date
                        archived_date = datetime.strptime(archived_date_str, "%Y-%m-%d").date()
                    
                    if archived_date >= week_start:
                        completed_week_count += 1
                        # Add up the quantities
                        qty_str = job.get("Quantity", job.get("Qty", "0"))
                        if isinstance(qty_str, str):
                            qty_str = qty_str.replace(',', '')
                        try:
                            completed_week_qty += int(qty_str)
                        except:
                            pass
                except Exception as e:
                    print(f"Error parsing date for job {job.get('Job Ticket#', 'Unknown')}: {e}")
                    pass
        
        self.completed_week_card.update_value(completed_week_count)
        
        # Format completed quantity this week
        if completed_week_qty >= 1000000:
            qty_week_display = f"{completed_week_qty/1000000:.1f}M"
        elif completed_week_qty >= 1000:
            qty_week_display = f"{completed_week_qty/1000:.0f}K"
        else:
            qty_week_display = f"{completed_week_qty:,}"
        self.completed_qty_week_card.update_value(qty_week_display)
    

    
    def update_calendar(self, active_jobs):
        """Update the interactive calendar with job data."""
        self.calendar_widget.set_jobs_data(active_jobs)
    
    def open_database_generator(self):
        """Open the Database Generator tool from dashboard."""
        try:
            from src.widgets.database_generator_dialog import DatabaseGeneratorDialog
            dialog = DatabaseGeneratorDialog(self)
            dialog.exec()
        except Exception as e:
            print(f"Error opening Database Generator: {e}")
    
    def open_roll_tracker(self):
        """Open the Roll Tracker tool from dashboard."""
        try:
            from src.widgets.roll_tracker_dialog import RollTrackerDialog
            dialog = RollTrackerDialog(self)
            dialog.exec()
        except Exception as e:
            print(f"Error opening Roll Tracker: {e}") 