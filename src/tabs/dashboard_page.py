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
try:
    from PySide6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    print("PySide6.QtCharts not available - charts will be disabled")
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


class ActivityItem(QFrame):
    """A single activity item in the activity feed."""
    
    def __init__(self, icon, text, timestamp, color="#0078d4", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setMinimumHeight(45)
        self.setMaximumHeight(60)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Icon/Badge
        icon_label = QLabel(icon)
        icon_label.setFixedSize(28, 28)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 14px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        layout.addWidget(icon_label)
        
        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        
        text_label = QLabel(text)
        text_label.setStyleSheet("color: #e0e0e0; font-size: 11px;")
        text_label.setWordWrap(True)
        text_layout.addWidget(text_label)
        
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("color: #888888; font-size: 10px;")
        text_layout.addWidget(time_label)
        
        layout.addLayout(text_layout, 1)


class DeadlineItem(QFrame):
    """A deadline item showing job with due date."""
    
    def __init__(self, job_data, parent=None):
        super().__init__(parent)
        self.job_data = job_data
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setMinimumHeight(70)
        self.setMaximumHeight(85)
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
        header_layout.addWidget(customer_label)
        
        po_label = QLabel(f"PO: {job_data.get('PO#', 'N/A')}")
        po_label.setStyleSheet("color: #888888; font-size: 10px;")
        header_layout.addWidget(po_label)
        header_layout.addStretch()
        
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


class DashboardPageWidget(QWidget):
    """Main dashboard widget with statistics, activity feed, and quick actions."""
    
    # Signals
    navigate_to_jobs = Signal()
    navigate_to_archive = Signal()
    create_new_job = Signal()
    
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
        
        # Statistics Cards Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        self.active_jobs_card = StatCard("Active Jobs", "0", color="#0078d4")
        self.active_jobs_card.clicked.connect(self.navigate_to_jobs.emit)
        stats_layout.addWidget(self.active_jobs_card)
        
        self.due_today_card = StatCard("Due Today", "0", color="#e74c3c")
        stats_layout.addWidget(self.due_today_card)
        
        self.overdue_card = StatCard("Overdue", "0", color="#e74c3c")
        stats_layout.addWidget(self.overdue_card)
        
        self.completed_week_card = StatCard("Completed This Week", "0", color="#27ae60")
        stats_layout.addWidget(self.completed_week_card)
        
        self.total_quantity_card = StatCard("Total Active Qty", "0", color="#3498db")
        stats_layout.addWidget(self.total_quantity_card)
        
        main_layout.addLayout(stats_layout)
        
        # Content area with two columns
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Left column - Activity Feed and Quick Actions
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        # Quick Actions
        actions_frame = QFrame()
        actions_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        actions_layout = QVBoxLayout(actions_frame)
        
        actions_title = QLabel("Quick Actions")
        actions_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0; margin-bottom: 8px;")
        actions_layout.addWidget(actions_title)
        
        # Action buttons
        new_job_btn = QPushButton("➕ Create New Job")
        new_job_btn.setMinimumHeight(32)
        new_job_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        new_job_btn.clicked.connect(self.create_new_job.emit)
        actions_layout.addWidget(new_job_btn)
        
        view_jobs_btn = QPushButton("📋 View All Jobs")
        view_jobs_btn.setMinimumHeight(32)
        view_jobs_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d40;
                color: white;
                border: 1px solid #464647;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #4d4d50;
                border: 1px solid #0078d4;
            }
        """)
        view_jobs_btn.clicked.connect(self.navigate_to_jobs.emit)
        actions_layout.addWidget(view_jobs_btn)
        
        archive_btn = QPushButton("📁 View Archive")
        archive_btn.setMinimumHeight(32)
        archive_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d40;
                color: white;
                border: 1px solid #464647;
                padding: 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #4d4d50;
                border: 1px solid #0078d4;
            }
        """)
        archive_btn.clicked.connect(self.navigate_to_archive.emit)
        actions_layout.addWidget(archive_btn)
        
        left_column.addWidget(actions_frame)
        
        # Activity Feed
        activity_frame = QFrame()
        activity_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        activity_layout = QVBoxLayout(activity_frame)
        
        activity_title = QLabel("Recent Activity")
        activity_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0; margin-bottom: 8px;")
        activity_layout.addWidget(activity_title)
        
        # Activity scroll area
        self.activity_scroll = QScrollArea()
        self.activity_scroll.setWidgetResizable(True)
        self.activity_scroll.setMaximumHeight(350)
        self.activity_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d30;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #464647;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
        """)
        
        self.activity_widget = QWidget()
        self.activity_layout = QVBoxLayout(self.activity_widget)
        self.activity_layout.setSpacing(5)
        self.activity_scroll.setWidget(self.activity_widget)
        
        activity_layout.addWidget(self.activity_scroll)
        left_column.addWidget(activity_frame, 1)
        
        content_layout.addLayout(left_column, 1)
        
        # Right column - Job Distribution Chart and Upcoming Deadlines
        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        
        # Job Status Chart (moved to top)
        if CHARTS_AVAILABLE:
            chart_frame = QFrame()
            chart_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d30;
                    border: 1px solid #464647;
                    border-radius: 6px;
                    padding: 10px;
                }
            """)
            chart_layout = QVBoxLayout(chart_frame)
            
            chart_title = QLabel("Job Distribution")
            chart_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0; margin-bottom: 8px;")
            chart_layout.addWidget(chart_title)
            
            # Create pie chart
            self.chart = QChart()
            self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            self.chart.setBackgroundBrush(QBrush(QColor("#2d2d30")))
            self.chart.setTitleBrush(QBrush(QColor("#e0e0e0")))
            self.chart.legend().setLabelColor(QColor("#e0e0e0"))
            
            self.chart_view = QChartView(self.chart)
            self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.chart_view.setMinimumHeight(200)
            self.chart_view.setMaximumHeight(250)
            
            chart_layout.addWidget(self.chart_view)
            right_column.addWidget(chart_frame)
        else:
            # Fallback when charts are not available
            fallback_frame = QFrame()
            fallback_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d30;
                    border: 1px solid #464647;
                    border-radius: 6px;
                    padding: 10px;
                }
            """)
            fallback_layout = QVBoxLayout(fallback_frame)
            
            fallback_title = QLabel("Job Distribution")
            fallback_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0; margin-bottom: 8px;")
            fallback_layout.addWidget(fallback_title)
            
            self.job_stats_label = QLabel("Charts not available")
            self.job_stats_label.setStyleSheet("color: #e0e0e0; font-size: 11px; line-height: 1.5;")
            self.job_stats_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.job_stats_label.setMinimumHeight(150)
            self.job_stats_label.setMaximumHeight(200)
            fallback_layout.addWidget(self.job_stats_label)
            
            right_column.addWidget(fallback_frame)
        
        # Upcoming Deadlines (moved below chart with more space)
        deadlines_frame = QFrame()
        deadlines_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        deadlines_layout = QVBoxLayout(deadlines_frame)
        
        deadlines_title = QLabel("Upcoming Deadlines")
        deadlines_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #e0e0e0; margin-bottom: 8px;")
        deadlines_layout.addWidget(deadlines_title)
        
        # Deadlines scroll area with more space
        self.deadlines_scroll = QScrollArea()
        self.deadlines_scroll.setWidgetResizable(True)
        self.deadlines_scroll.setMinimumHeight(300)
        self.deadlines_scroll.setMaximumHeight(400)
        self.deadlines_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d30;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #464647;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
        """)
        
        self.deadlines_widget = QWidget()
        self.deadlines_layout = QVBoxLayout(self.deadlines_widget)
        self.deadlines_layout.setSpacing(8)
        self.deadlines_scroll.setWidget(self.deadlines_widget)
        
        deadlines_layout.addWidget(self.deadlines_scroll)
        right_column.addWidget(deadlines_frame, 1)  # Give it stretch priority
        
        content_layout.addLayout(right_column, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # Add scroll area to the main widget layout
        widget_layout.addWidget(scroll_area)
    
    def refresh_dashboard(self):
        """Refresh all dashboard data."""
        # Load job data
        active_jobs = self.load_active_jobs()
        archived_jobs = self.load_archived_jobs()
        
        # Update statistics
        self.update_statistics(active_jobs, archived_jobs)
        
        # Update activity feed
        self.update_activity_feed(active_jobs, archived_jobs)
        
        # Update upcoming deadlines
        self.update_deadlines(active_jobs)
        
        # Update chart
        self.update_chart(active_jobs)
    
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
                        jobs.append(job_data)
                    except Exception as e:
                        print(f"Error loading archived job from {metadata_path}: {e}")
        
        return jobs
    
    def update_statistics(self, active_jobs, archived_jobs):
        """Update statistics cards."""
        # Active jobs count
        self.active_jobs_card.update_value(len(active_jobs))
        
        # Due today and overdue counts
        today = datetime.now().date()
        due_today = 0
        overdue = 0
        total_quantity = 0
        
        for job in active_jobs:
            # Count quantities
            qty_str = job.get("Quantity", job.get("Qty", "0"))
            if isinstance(qty_str, str):
                qty_str = qty_str.replace(',', '')
            try:
                total_quantity += int(qty_str)
            except:
                pass
                
            # Check due dates
            due_date_str = job.get("Due Date", "")
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    if due_date == today:
                        due_today += 1
                    elif due_date < today:
                        overdue += 1
                except:
                    pass
                    
        self.due_today_card.update_value(due_today)
        self.overdue_card.update_value(overdue)
        
        # Format total quantity with commas
        if total_quantity >= 1000000:
            qty_display = f"{total_quantity/1000000:.1f}M"
        elif total_quantity >= 1000:
            qty_display = f"{total_quantity/1000:.0f}K"
        else:
            qty_display = str(total_quantity)
        self.total_quantity_card.update_value(qty_display)
        
        # Completed this week
        week_start = today - timedelta(days=today.weekday())
        completed_week = 0
        for job in archived_jobs:
            archived_date_str = job.get("dateArchived", "")
            if archived_date_str:
                try:
                    archived_date = datetime.strptime(archived_date_str.split()[0], "%Y-%m-%d").date()
                    if archived_date >= week_start:
                        completed_week += 1
                except:
                    pass
        self.completed_week_card.update_value(completed_week)
    
    def update_activity_feed(self, active_jobs, archived_jobs):
        """Update the activity feed with recent events."""
        # Clear existing items
        while self.activity_layout.count():
            item = self.activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        activities = []
        
        # Add recent archives (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        for job in archived_jobs:
            archived_date_str = job.get("dateArchived", "")
            if archived_date_str:
                try:
                    archived_date = datetime.strptime(archived_date_str, "%Y-%m-%d %H:%M:%S")
                    if archived_date >= seven_days_ago:
                        time_diff = datetime.now() - archived_date
                        if time_diff.days == 0:
                            if time_diff.seconds < 3600:
                                time_str = f"{time_diff.seconds // 60}m ago"
                            else:
                                time_str = f"{time_diff.seconds // 3600}h ago"
                        else:
                            time_str = f"{time_diff.days}d ago"
                        
                        ticket = job.get('Job Ticket#', job.get('Ticket#', 'N/A'))
                        qty = job.get('Quantity', job.get('Qty', 'N/A'))
                        activities.append({
                            'icon': '✓',
                            'text': f"{job.get('Customer', 'Unknown')} - PO#{job.get('PO#', 'N/A')} (Qty: {qty})",
                            'timestamp': time_str,
                            'color': '#27ae60',
                            'date': archived_date,
                            'priority': 2
                        })
                except:
                    pass
        
        # Add overdue jobs with priority
        today = datetime.now()
        for job in active_jobs:
            due_date_str = job.get("Due Date", "")
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                    days_diff = (due_date.date() - today.date()).days
                    
                    if days_diff < 0:  # Overdue
                        qty = job.get('Quantity', job.get('Qty', 'N/A'))
                        activities.append({
                            'icon': '⚠',
                            'text': f"{job.get('Customer', 'Unknown')} - PO#{job.get('PO#', 'N/A')} (Qty: {qty})",
                            'timestamp': f"{abs(days_diff)}d overdue",
                            'color': '#e74c3c',
                            'date': due_date,
                            'priority': 0
                        })
                    elif days_diff == 0:  # Due today
                        qty = job.get('Quantity', job.get('Qty', 'N/A'))
                        activities.append({
                            'icon': '📅',
                            'text': f"{job.get('Customer', 'Unknown')} - PO#{job.get('PO#', 'N/A')} (Qty: {qty})",
                            'timestamp': "Due today",
                            'color': '#f39c12',
                            'date': due_date,
                            'priority': 1
                        })
                    elif days_diff <= 3:  # Due soon
                        qty = job.get('Quantity', job.get('Qty', 'N/A'))
                        activities.append({
                            'icon': '⏰',
                            'text': f"{job.get('Customer', 'Unknown')} - PO#{job.get('PO#', 'N/A')} (Qty: {qty})",
                            'timestamp': f"Due in {days_diff}d",
                            'color': '#3498db',
                            'date': due_date,
                            'priority': 3
                        })
                except:
                    pass
        
        # Add jobs with large quantities
        for job in active_jobs:
            qty_str = job.get("Quantity", job.get("Qty", "0"))
            if isinstance(qty_str, str):
                qty_str = qty_str.replace(',', '')
            try:
                qty = int(qty_str)
                if qty >= 50000:  # Large orders
                    activities.append({
                        'icon': '📦',
                        'text': f"Large order: {job.get('Customer', 'Unknown')} - {qty:,} units",
                        'timestamp': f"PO#{job.get('PO#', 'N/A')}",
                        'color': '#9b59b6',
                        'date': datetime.now(),
                        'priority': 4
                    })
            except:
                pass
        
        # Sort activities by priority then date
        activities.sort(key=lambda x: (x.get('priority', 99), x.get('date', datetime.min)), reverse=False)
        
        # Add activity items to layout (limit to 10 most important)
        if activities:
            for activity in activities[:10]:
                item = ActivityItem(
                    activity['icon'],
                    activity['text'],
                    activity['timestamp'],
                    activity['color']
                )
                self.activity_layout.addWidget(item)
        else:
            # Show empty state
            empty_label = QLabel("No recent activity")
            empty_label.setStyleSheet("color: #666666; font-size: 12px; padding: 1px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.activity_layout.addWidget(empty_label)
        
        # Add stretch at the end
        self.activity_layout.addStretch()
    
    def update_deadlines(self, active_jobs):
        """Update upcoming deadlines list."""
        # Clear existing items
        while self.deadlines_layout.count():
            item = self.deadlines_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Sort jobs by due date
        jobs_with_dates = []
        for job in active_jobs:
            due_date_str = job.get("Due Date", "")
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                    jobs_with_dates.append((due_date, job))
                except:
                    pass
        
        jobs_with_dates.sort(key=lambda x: x[0])
        
        # Add deadline items (limit to next 10)
        for due_date, job in jobs_with_dates[:10]:
            item = DeadlineItem(job)
            self.deadlines_layout.addWidget(item)
        
        # Add stretch at the end
        self.deadlines_layout.addStretch()
    
    def update_chart(self, active_jobs):
        """Update the job distribution pie chart."""
        if CHARTS_AVAILABLE:
            # Clear existing series
            self.chart.removeAllSeries()
            
            # Count jobs by customer
            customer_counts = {}
            for job in active_jobs:
                customer = job.get("Customer", "Unknown")
                customer_counts[customer] = customer_counts.get(customer, 0) + 1
            
            if customer_counts:
                # Create pie series
                series = QPieSeries()
                
                # Add data to series
                for customer, count in customer_counts.items():
                    slice = series.append(f"{customer} ({count})", count)
                    slice.setLabelVisible(True)
                    slice.setLabelColor(QColor("#e0e0e0"))
                
                # Add series to chart
                self.chart.addSeries(series)
                
                # Customize appearance
                for slice in series.slices():
                    slice.setLabelBrush(QBrush(QColor("#e0e0e0")))
                    slice.setLabelFont(QFont("Arial", 8))
            else:
                # Show empty state
                series = QPieSeries()
                series.append("No Active Jobs", 1)
                self.chart.addSeries(series)
        else:
            # Update text-based stats when charts are not available
            if hasattr(self, 'job_stats_label'):
                customer_counts = {}
                for job in active_jobs:
                    customer = job.get("Customer", "Unknown")
                    customer_counts[customer] = customer_counts.get(customer, 0) + 1
                
                if customer_counts:
                    stats_text = "Job Distribution:\n\n"
                    total = sum(customer_counts.values())
                    for customer, count in sorted(customer_counts.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total) * 100
                        stats_text += f"{customer}: {count} ({percentage:.1f}%)\n"
                    self.job_stats_label.setText(stats_text)
                else:
                    self.job_stats_label.setText("No active jobs") 