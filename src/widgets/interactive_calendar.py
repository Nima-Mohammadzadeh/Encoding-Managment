import os
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QSizePolicy, QToolTip, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QDate
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QBrush, QPen, QCursor


class JobCalendarDayWidget(QFrame):
    """Individual day widget that can display jobs."""
    job_clicked = Signal(dict)
    
    def __init__(self, day_date: date, parent=None):
        super().__init__(parent)
        self.day_date = day_date
        self.jobs = []  # List of jobs for this day
        self.is_current_month = True
        self.is_today = day_date == date.today()
        
        self.setMinimumSize(100, 85)
        self.setMaximumSize(110, 95)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setup_ui()
        self.update_styling()
    
    def setup_ui(self):
        """Setup the day widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        
        # Day number
        self.day_label = QLabel(str(self.day_date.day))
        self.day_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.day_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(self.day_label)
        
        # Jobs container
        self.jobs_container = QFrame()
        self.jobs_layout = QVBoxLayout(self.jobs_container)
        self.jobs_layout.setContentsMargins(0, 0, 0, 0)
        self.jobs_layout.setSpacing(1)
        layout.addWidget(self.jobs_container, 1)
        
        # Job count badge (hidden initially)
        self.job_count_label = QLabel()
        self.job_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.job_count_label.setStyleSheet("""
            QLabel {
                background-color: #0078d4;
                color: white;
                border-radius: 6px;
                font-size: 8px;
                font-weight: bold;
                padding: 1px 4px;
                max-width: 20px;
            }
        """)
        self.job_count_label.hide()
        layout.addWidget(self.job_count_label)
    
    def set_current_month(self, is_current: bool):
        """Set whether this day belongs to the current month."""
        self.is_current_month = is_current
        self.update_styling()
    
    def add_job(self, job_data: Dict[str, Any]):
        """Add a job to this day."""
        self.jobs.append(job_data)
        self.update_jobs_display()
    
    def clear_jobs(self):
        """Clear all jobs from this day."""
        self.jobs.clear()
        self.update_jobs_display()
    
    def update_jobs_display(self):
        """Update the visual display of jobs for this day."""
        # Clear existing job widgets
        while self.jobs_layout.count():
            item = self.jobs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.jobs:
            self.job_count_label.hide()
            self.setToolTip("")
            self.update_styling()
            return
        
        # Create detailed tooltip for all jobs on this day
        tooltip_lines = []
        for job in self.jobs:
            customer = job.get("Customer", "Unknown")
            ticket = job.get("Job Ticket#", job.get("Ticket#", "N/A"))
            po = job.get("PO#", "N/A")
            qty = job.get("Quantity", job.get("Qty", "N/A"))
            
            # Format quantity with commas
            if qty and str(qty).replace(',', '').isdigit():
                clean_qty = str(qty).replace(',', '')
                qty = f"{int(clean_qty):,}"
            
            tooltip_lines.append(f"• {customer} (#{ticket})")
            tooltip_lines.append(f"  PO: {po} | Qty: {qty}")
        
        tooltip_text = f"Jobs due on {self.day_date.strftime('%B %d, %Y')}:\n" + "\n".join(tooltip_lines)
        self.setToolTip(tooltip_text)
        
        # Show job count if more than 3 jobs
        if len(self.jobs) > 3:
            self.job_count_label.setText(f"{len(self.jobs)}")
            self.job_count_label.show()
            
            # Show only first 2 jobs with "..." indicator
            for i, job in enumerate(self.jobs[:2]):
                job_widget = self.create_job_widget(job)
                self.jobs_layout.addWidget(job_widget)
            
            # Add "more" indicator
            more_label = QLabel("...")
            more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            more_label.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold;")
            self.jobs_layout.addWidget(more_label)
        else:
            self.job_count_label.hide()
            # Show all jobs
            for job in self.jobs:
                job_widget = self.create_job_widget(job)
                self.jobs_layout.addWidget(job_widget)
        
        self.update_styling()
    
    def create_job_widget(self, job_data: Dict[str, Any]) -> QLabel:
        """Create a small widget for displaying a job."""
        customer = job_data.get("Customer", "Unknown")
        ticket = job_data.get("Job Ticket#", job_data.get("Ticket#", ""))
        
        # Determine urgency color
        color = self.get_urgency_color(job_data)
        
        job_widget = QLabel(f"{customer[:8]}...")
        job_widget.setToolTip(f"Customer: {customer}\nTicket#: {ticket}\nPO#: {job_data.get('PO#', 'N/A')}")
        job_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        job_widget.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 3px;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 3px;
                min-height: 12px;
                max-height: 14px;
            }}
        """)
        job_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        job_widget.mousePressEvent = lambda event, job=job_data: self.on_job_clicked(job)
        
        return job_widget
    
    def get_urgency_color(self, job_data: Dict[str, Any]) -> str:
        """Get color based on job urgency."""
        due_date_str = job_data.get("Due Date", "")
        if not due_date_str:
            return "#6c757d"  # Gray for no due date
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            days_until_due = (due_date - date.today()).days
            
            if days_until_due < 0:
                return "#e74c3c"  # Red for overdue
            elif days_until_due == 0:
                return "#e74c3c"  # Red for due today
            elif days_until_due <= 3:
                return "#f39c12"  # Orange for urgent
            elif days_until_due <= 7:
                return "#f1c40f"  # Yellow for soon
            else:
                return "#27ae60"  # Green for normal
        except:
            return "#6c757d"  # Gray for invalid date
    
    def update_styling(self):
        """Update the styling based on current state."""
        base_style = """
            QFrame {
                border: 1px solid #464647;
                border-radius: 4px;
                background-color: %s;
            }
            QFrame:hover {
                border: 1px solid #0078d4;
                background-color: %s;
            }
        """
        
        if not self.is_current_month:
            # Muted colors for non-current month
            bg_color = "#1a1a1a"
            hover_color = "#2a2a2a"
            text_color = "#666666"
        elif self.is_today:
            # Highlight today
            bg_color = "#0078d4"
            hover_color = "#106ebe"
            text_color = "#ffffff"
        elif self.jobs:
            # Highlight days with jobs
            bg_color = "#2d2d30"
            hover_color = "#3d3d40"
            text_color = "#e0e0e0"
        else:
            # Normal days
            bg_color = "#2d2d30"
            hover_color = "#3d3d40"
            text_color = "#cccccc"
        
        self.setStyleSheet(base_style % (bg_color, hover_color))
        self.day_label.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {text_color};")
    
    def on_job_clicked(self, job_data):
        """Handle job click."""
        self.job_clicked.emit(job_data)
    
    def mousePressEvent(self, event):
        """Handle day click - show jobs for this day."""
        if event.button() == Qt.MouseButton.LeftButton and self.jobs:
            if len(self.jobs) == 1:
                # Single job - directly emit it
                self.job_clicked.emit(self.jobs[0])
            else:
                # Multiple jobs - show selection dialog
                self.show_job_selection_dialog()
        super().mousePressEvent(event)
    
    def show_job_selection_dialog(self):
        """Show dialog for selecting a job when multiple jobs are due."""
        from src.widgets.job_selection_dialog import JobSelectionDialog
        
        date_str = self.day_date.strftime("%B %d, %Y")
        dialog = JobSelectionDialog(self.jobs, date_str, self)
        dialog.job_selected.connect(self.job_clicked.emit)
        dialog.exec()


class MonthNavigationWidget(QFrame):
    """Navigation widget for changing months."""
    month_changed = Signal(int, int)  # year, month
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_date = date.today()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the navigation UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Previous month button
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setFixedSize(24, 24)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.prev_btn.clicked.connect(self.go_to_previous_month)
        layout.addWidget(self.prev_btn)
        
        # Month/Year label
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.month_label, 1)
        
        # Next month button
        self.next_btn = QPushButton("›")
        self.next_btn.setFixedSize(24, 24)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.next_btn.clicked.connect(self.go_to_next_month)
        layout.addWidget(self.next_btn)
        
        # Today button
        self.today_btn = QPushButton("Today")
        self.today_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        self.today_btn.clicked.connect(self.go_to_today)
        layout.addWidget(self.today_btn)
        
        # View toggle buttons
        view_layout = QHBoxLayout()
        view_layout.setSpacing(4)
        
        # Month view button (default active)
        self.month_view_btn = QPushButton("Month")
        self.month_view_btn.setCheckable(True)
        self.month_view_btn.setChecked(True)
        self.month_view_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                min-width: 50px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:checked {
                background-color: #106ebe;
            }
        """)
        view_layout.addWidget(self.month_view_btn)
        
        # Week view button (for future enhancement)
        self.week_view_btn = QPushButton("Week")
        self.week_view_btn.setCheckable(True)
        self.week_view_btn.setEnabled(False)  # Disabled for now
        self.week_view_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
                min-width: 50px;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #666666;
            }
        """)
        view_layout.addWidget(self.week_view_btn)
        
        layout.addLayout(view_layout)
        
        self.update_month_label()
    
    def update_month_label(self):
        """Update the month/year label."""
        month_name = self.current_date.strftime("%B %Y")
        self.month_label.setText(month_name)
    
    def go_to_previous_month(self):
        """Navigate to previous month."""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        self.update_month_label()
        self.month_changed.emit(self.current_date.year, self.current_date.month)
    
    def go_to_next_month(self):
        """Navigate to next month."""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        self.update_month_label()
        self.month_changed.emit(self.current_date.year, self.current_date.month)
    
    def go_to_today(self):
        """Navigate to current month."""
        self.current_date = date.today()
        self.update_month_label()
        self.month_changed.emit(self.current_date.year, self.current_date.month)


class InteractiveCalendarWidget(QFrame):
    """Beautiful interactive calendar widget for displaying job due dates."""
    job_clicked = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_year = date.today().year
        self.current_month = date.today().month
        self.jobs_data = []
        self.day_widgets = {}  # date -> JobCalendarDayWidget
        
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 6px;
            }
        """)
        
        # Add drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.setup_ui()
        self.create_calendar_grid()
        
        # Enable keyboard focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def setup_ui(self):
        """Setup the calendar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        # Title
        title_label = QLabel("Job Calendar")
        title_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0; margin-bottom: 8px;")
        layout.addWidget(title_label)
        
        # Navigation
        self.navigation = MonthNavigationWidget()
        self.navigation.month_changed.connect(self.on_month_changed)
        layout.addWidget(self.navigation)
        
        # Day headers
        self.create_day_headers(layout)
        
        # Calendar grid container
        self.calendar_container = QFrame()
        self.calendar_layout = QGridLayout(self.calendar_container)
        self.calendar_layout.setContentsMargins(0, 0, 0, 0)
        self.calendar_layout.setSpacing(2)
        layout.addWidget(self.calendar_container, 1)
        
        # Legend
        self.create_legend(layout)
    
    def create_day_headers(self, parent_layout):
        """Create day of week headers."""
        headers_frame = QFrame()
        headers_layout = QGridLayout(headers_frame)
        headers_layout.setContentsMargins(0, 0, 0, 0)
        headers_layout.setSpacing(1)
        
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day_name in enumerate(day_names):
            label = QLabel(day_name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 2px;
                }
            """)
            headers_layout.addWidget(label, 0, i)
        
        parent_layout.addWidget(headers_frame)
    
    def create_legend(self, parent_layout):
        """Create color legend."""
        legend_frame = QFrame()
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(2, 2, 2, 2)
        legend_layout.setSpacing(4)
        
        legend_items = [
            ("Overdue", "#e74c3c"),
            ("Due Soon (≤3d)", "#f39c12"),
            ("Due This Week", "#f1c40f"),
            ("Normal", "#27ae60"),
            ("Today", "#0078d4")
        ]
        
        for text, color in legend_items:
            item_frame = QFrame()
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(2)
            
            color_indicator = QLabel()
            color_indicator.setFixedSize(8, 8)
            color_indicator.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """)
            item_layout.addWidget(color_indicator)
            
            text_label = QLabel(text)
            text_label.setStyleSheet("color: #cccccc; font-size: 8px;")
            item_layout.addWidget(text_label)
            
            legend_layout.addWidget(item_frame)
        
        legend_layout.addStretch()
        parent_layout.addWidget(legend_frame)
    
    def create_calendar_grid(self):
        """Create the calendar grid for the current month."""
        # Clear existing widgets
        self.day_widgets.clear()
        while self.calendar_layout.count():
            item = self.calendar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get first day of month and number of days
        first_day = date(self.current_year, self.current_month, 1)
        
        # Calculate days to show (including previous/next month days)
        # Monday = 0, Sunday = 6
        start_weekday = first_day.weekday()
        
        # Start from the Monday of the week containing the first day
        start_date = first_day - timedelta(days=start_weekday)
        
        # Create 6 weeks (42 days) to ensure full calendar
        for week in range(6):
            for day in range(7):
                current_date = start_date + timedelta(days=week * 7 + day)
                
                day_widget = JobCalendarDayWidget(current_date)
                day_widget.job_clicked.connect(self.job_clicked.emit)
                
                # Set whether this day is in current month
                is_current_month = current_date.month == self.current_month
                day_widget.set_current_month(is_current_month)
                
                self.day_widgets[current_date] = day_widget
                self.calendar_layout.addWidget(day_widget, week, day)
        
        # Update with job data
        self.update_jobs_on_calendar()
    
    def on_month_changed(self, year: int, month: int):
        """Handle month navigation."""
        self.current_year = year
        self.current_month = month
        self.create_calendar_grid()
    
    def set_jobs_data(self, jobs_data: List[Dict[str, Any]]):
        """Set the jobs data and update calendar."""
        self.jobs_data = jobs_data
        self.update_jobs_on_calendar()
    
    def update_jobs_on_calendar(self):
        """Update the calendar with job data."""
        # Clear all existing jobs from day widgets
        for day_widget in self.day_widgets.values():
            day_widget.clear_jobs()
        
        # Add jobs to appropriate days
        for job in self.jobs_data:
            due_date_str = job.get("Due Date", "")
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    if due_date in self.day_widgets:
                        self.day_widgets[due_date].add_job(job)
                except Exception as e:
                    print(f"Error parsing due date '{due_date_str}': {e}")
    
    def keyPressEvent(self, event):
        """Handle keyboard navigation."""
        if event.key() == Qt.Key.Key_Left:
            self.navigation.go_to_previous_month()
        elif event.key() == Qt.Key.Key_Right:
            self.navigation.go_to_next_month()
        elif event.key() == Qt.Key.Key_Home:
            self.navigation.go_to_today()
        else:
            super().keyPressEvent(event) 