import os
import json
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QProgressBar, QListWidget,
    QListWidgetItem, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QRect, QObject, QThread
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QBrush, QPen
import src.config as config


class DashboardDataWorker(QObject):
    """Worker to load all dashboard data in the background."""
    data_loaded = Signal(dict, list)  # updated_jobs, all_job_paths
    error = Signal(str)

    def __init__(self, active_dir, archive_dir, cache):
        super().__init__()
        self.active_jobs_source_dir = active_dir
        self.archive_dir = archive_dir
        self.cache = cache
        self.is_cancelled = False

    def run(self):
        """Load data from the filesystem, using cache to avoid re-reading files."""
        try:
            active_jobs, active_paths = self._load_jobs(self.active_jobs_source_dir, is_archived=False)
            if self.is_cancelled: return
            
            archived_jobs, archived_paths = self._load_jobs(self.archive_dir, is_archived=True)
            if self.is_cancelled: return

            updated_jobs = {**active_jobs, **archived_jobs}
            all_job_paths = active_paths.union(archived_paths)

            self.data_loaded.emit(updated_jobs, list(all_job_paths))
        except Exception as e:
            self.error.emit(f"Failed to load dashboard data: {e}")

    def _load_jobs(self, directory, is_archived):
        """Generic job loader that uses modification times to update a cache."""
        updated_jobs = {}
        found_paths = set()
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            return updated_jobs, found_paths
        
        for root, _, files in os.walk(directory):
            if self.is_cancelled:
                break
            if "job_data.json" in files:
                job_data_path = os.path.join(root, "job_data.json")
                found_paths.add(job_data_path)
                try:
                    last_modified = os.path.getmtime(job_data_path)
                    
                    # Check cache
                    if job_data_path in self.cache and self.cache[job_data_path]['mtime'] == last_modified:
                        # File is unchanged, skip reading
                        continue

                    with open(job_data_path, "r", encoding='utf-8') as f:
                        job_data = json.load(f)
                    
                    if is_archived:
                        job_data['job_folder_path'] = root
                    else:
                        job_data['active_source_folder_path'] = root

                    updated_jobs[job_data_path] = {'mtime': last_modified, 'data': job_data}
                except Exception as e:
                    print(f"Error loading job from {job_data_path}: {e}")
        return updated_jobs, found_paths

    def cancel(self):
        self.is_cancelled = True


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
        self.is_loading = False # Prevent concurrent refreshes
        self.job_data_cache = {} # Cache for job data and modification times
        
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
        self.refresh_btn = QPushButton("⟳ Refresh")
        self.refresh_btn.setStyleSheet("""
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
        self.refresh_btn.clicked.connect(self.refresh_dashboard)
        header_layout.addWidget(self.refresh_btn)
        
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
        if self.is_loading:
            print("Dashboard refresh already in progress. Skipping.")
            return

        print(f"Dashboard refresh triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.is_loading = True
        self.refresh_btn.setText("Refreshing...")
        self.refresh_btn.setEnabled(False)

        # Setup worker thread
        self.load_thread = QThread()
        self.worker = DashboardDataWorker(self.active_jobs_source_dir, self.archive_dir, self.job_data_cache)
        self.worker.moveToThread(self.load_thread)

        # Connect signals
        self.load_thread.started.connect(self.worker.run)
        self.worker.data_loaded.connect(self.on_data_loaded)
        self.worker.error.connect(self.on_data_load_error)

        # Clean up thread
        self.worker.data_loaded.connect(self.load_thread.quit)
        self.worker.error.connect(self.load_thread.quit)
        self.load_thread.finished.connect(self.load_thread.deleteLater)
        self.worker.data_loaded.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)

        self.load_thread.start()

    def on_data_loaded(self, updated_jobs, all_job_paths):
        """Handle the data loaded by the worker thread."""
        print(f"Dashboard data updated with {len(updated_jobs)} changed jobs. Total paths found: {len(all_job_paths)}.")
        
        # Update cache with new/modified jobs
        self.job_data_cache.update(updated_jobs)
        
        # Purge deleted jobs from cache
        current_paths_in_cache = set(self.job_data_cache.keys())
        paths_on_disk = set(all_job_paths)
        deleted_paths = current_paths_in_cache - paths_on_disk
        
        if deleted_paths:
            print(f"Purging {len(deleted_paths)} deleted jobs from cache.")
            for path in deleted_paths:
                if path in self.job_data_cache:
                    del self.job_data_cache[path]

        # --- REFINED FILTERING LOGIC ---
        # Use file paths to definitively separate active from archived jobs.
        
        active_jobs = []
        archived_jobs = []
        
        active_dir_path = os.path.normpath(self.active_jobs_source_dir)
        archive_dir_path = os.path.normpath(self.archive_dir)

        for path, item in self.job_data_cache.items():
            job_data = item['data']
            normalized_path = os.path.normpath(path)

            if normalized_path.startswith(archive_dir_path):
                # If it's in the archive directory, it's archived.
                archived_jobs.append(job_data)
            elif normalized_path.startswith(active_dir_path):
                # If it's in the active directory, it's active.
                active_jobs.append(job_data)
        
        # This will now give the correct counts, matching the Jobs tab.
        print(f"Recalculating stats with {len(active_jobs)} active and {len(archived_jobs)} archived jobs.")
        
        # Update UI with the freshly filtered lists
        self.update_statistics(active_jobs, archived_jobs)
        self.update_calendar(active_jobs)
        
        self.on_load_finished()

    def on_data_load_error(self, error_message):
        """Handle errors from the worker thread."""
        print(f"Error loading dashboard data: {error_message}")
        # Optionally show a message to the user
        self.on_load_finished()

    def on_load_finished(self):
        """Common cleanup after loading finishes or fails."""
        self.is_loading = False
        self.refresh_btn.setText("⟳ Refresh")
        self.refresh_btn.setEnabled(True)
        print("Dashboard loading process finished.")

    def update_statistics(self, active_jobs, archived_jobs):
        """Update statistics cards."""
        # Jobs in Backlog (active jobs)
        self.jobs_backlog_card.update_value(len(active_jobs))
        
        # Calculate total backlog quantity
        total_backlog_quantity = 0
        today = datetime.now().date()
        
        for job_data in active_jobs:
            qty_str = job_data.get("Quantity", job_data.get("Qty", "0"))
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
        
        print(f"\n--- Calculating 'Completed This Week' (Week starts on {week_start.strftime('%Y-%m-%d')}) ---")

        for job_data in archived_jobs:
            # Check for multiple possible date keys in order of preference
            archived_date_str = job_data.get("dateArchived",         # Original key with timestamp
                                     job_data.get("archivedDate",       # Key with date only
                                     job_data.get("Archived Date")))    # Key matching the table column header
            
            job_id = job_data.get('Job Ticket#', 'Unknown')

            if not archived_date_str:
                print(f"  - Job {job_id}: SKIPPED (No archive date found using keys 'dateArchived', 'archivedDate', or 'Archived Date')")
                continue

            try:
                # Handle both timestamp and date-only formats
                date_part = archived_date_str.split()[0]
                
                # Attempt to parse multiple date formats
                archived_date = None
                for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        archived_date = datetime.strptime(date_part, fmt).date()
                        break # Success
                    except ValueError:
                        continue # Try next format
                
                if archived_date is None:
                    raise ValueError(f"Date '{date_part}' could not be parsed with available formats.")

                if archived_date >= week_start:
                    print(f"  + Job {job_id}: COUNTED (Date: {archived_date.strftime('%Y-%m-%d')})")
                    completed_week_count += 1
                    # Add up the quantities
                    qty_str = job_data.get("Quantity", job_data.get("Qty", "0"))
                    if isinstance(qty_str, str):
                        qty_str = qty_str.replace(',', '')
                    try:
                        completed_week_qty += int(qty_str)
                    except (ValueError, TypeError):
                        pass # Ignore if quantity is not a valid number
                else:
                    print(f"  - Job {job_id}: SKIPPED (Archived on {archived_date.strftime('%Y-%m-%d')}, before current week)")

            except Exception as e:
                print(f"  - Job {job_id}: SKIPPED (Error parsing date: {e})")
        
        print(f"--- Calculation complete. Total jobs counted: {completed_week_count} ---\n")

        self.completed_week_card.update_value(completed_week_count)
        
        # Format completed quantity this week
        if completed_week_qty >= 1000000:
            qty_week_display = f"{completed_week_qty/1000000:.1f}M"
        elif completed_week_qty >= 1000:
            qty_week_display = f"{completed_week_qty/1000:.0f}K"
        else:
            qty_week_display = f"{completed_week_qty:,}"
        self.completed_qty_week_card.update_value(qty_week_display)
    

    
    def update_calendar(self, jobs_data):
        """Update the interactive calendar with job data."""
        # Filter out jobs that are not in the updated_jobs cache
        # This ensures we only show jobs that were successfully loaded and are relevant
        self.calendar_widget.set_jobs_data([
            job_data for job_data in jobs_data
            if 'active_source_folder_path' in job_data or 'job_folder_path' in job_data
        ])
    
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