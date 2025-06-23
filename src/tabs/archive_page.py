import json
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QTableView,
    QHeaderView,
    QSizePolicy,
    QAbstractItemView,
    QMenu,
    QComboBox,
    QDateEdit,
    QPushButton,
    QLabel,
    QTreeView
)


from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt, QDate

class ArchivePageWidget(QWidget):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.save_file = os.path.join(self.base_path, "data", "archived_jobs.json")
        self.network_path = r"Z:\3 Encoding and Printing Files\Archived Jobs"
        
        self.all_jobs = [] # To store all loaded jobs
        self.setup_ui()
        self.load_jobs()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDate(QDate.currentDate())
        filter_layout.addWidget(self.date_to)

        filter_layout.addWidget(QLabel("Customer:"))
        self.customer_filter = QComboBox()
        self.customer_filter.setEditable(True)
        self.customer_filter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filter_layout.addWidget(self.customer_filter)
        
        self.apply_filter_btn = QPushButton("Filter")
        self.apply_filter_btn.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.apply_filter_btn)

        self.reset_filter_btn = QPushButton("Reset")
        self.reset_filter_btn.clicked.connect(self.reset_filters)
        filter_layout.addWidget(self.reset_filter_btn)

        main_layout.addLayout(filter_layout)

        # Content layout
        content_layout = QHBoxLayout()

        # Tree view for date hierarchy
        self.tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(['Archive'])
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setFixedWidth(200)
        self.tree_view.clicked.connect(self.on_tree_selection)
        content_layout.addWidget(self.tree_view)

        # Table view
        self.model = QStandardItemModel()
        self.headers = ([
            "Customer", "Part#", "Job Ticket#", "PO#",
            "Inlay Type", "Label Size", "Quantity", "Status", "Archived Date"
        ])
        self.model.setHorizontalHeaderLabels(self.headers)
        self.jobs_table = QTableView()
        self.jobs_table.setModel(self.model)
        self.jobs_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setSortingEnabled(True)
        self.jobs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.jobs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.jobs_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.headers.index("Customer"), QHeaderView.ResizeMode.Stretch)
        content_layout.addWidget(self.jobs_table)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    def add_archived_job(self, job_data):
        print(f"Archiving job: {job_data.get('Job Ticket#')}")
        
        # Add a timestamp to the job data
        job_data['dateArchived'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.all_jobs.append(job_data)
        self.update_archive_display()
        self.save_data()

    def get_job_data(self, row_index):
        job_data = {}
        for col, header in enumerate(self.headers):
            item = self.model.item(row_index, col)
            job_data[header] = item.text() if item else ""
        return job_data
    
    def move_to_archive(self, row_index):
        job_data = self.get_job_data(row_index)
        job_data["Status"] = "Archived"
        self.add_job_to_table(job_data, status="Archived")
        self.save_data()
        self.model.removeRow(row_index)
        self.save_data()
        self.load_jobs()
    
    def delete_selected_job(self):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return
        reply = QMessageBox.question(self, "Confirmation", "Are you sure you want to delete this job?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            selected_row_index = selection_model.selectedRows()[0]
            # Find the corresponding job in self.all_jobs and remove it
            job_to_remove = self._get_job_data_for_row(selected_row_index.row())
            self.all_jobs = [j for j in self.all_jobs if j.get('Job Ticket#') != job_to_remove.get('Job Ticket#')]
            self.model.removeRow(selected_row_index.row())
            self.save_data()

    def add_job_to_table(self, job_data, status="Archived"):
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Job Ticket#", "")),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(job_data.get("Qty", "")),
            QStandardItem(status),
            QStandardItem(job_data.get("dateArchived", ""))
        ]
        self.model.appendRow(row_items)

    def load_jobs(self):
        if not os.path.exists(self.save_file):
            print("save file does not exist. Fresh start")
            return
        
        try:
            with open(self.save_file, "r") as f:
                self.all_jobs = json.load(f)
            
            self.update_archive_display()
            self.populate_customer_filter()
            self.apply_filters() # apply default filters on load

        except Exception as e:
            print("Error loading jobs:", e)
            self.all_jobs = []

    def save_data(self):
        try:
            with open(self.save_file, "w") as f:
                json.dump(self.all_jobs, f, indent=4)
        except IOError as e:
            print(f"Error saving data: {e}")
    
    def _get_job_data_for_row(self, row):
        job_data = {}
        # This needs to get data from the currently displayed row in the table model
        if row < self.model.rowCount():
            for col, header in enumerate(self.headers):
                item = self.model.item(row, col)
                job_data[header] = item.text() if item else ""
        return job_data

    def update_archive_display(self):
        """This will update both the tree and the table."""
        self.populate_tree_view()
        self.apply_filters()

    def populate_tree_view(self):
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(['Archive'])
        root = self.tree_model.invisibleRootItem()
        
        hierarchy = {}
        for job in self.all_jobs:
            date_str = job.get('dateArchived', '')
            if not date_str:
                continue
            
            try:
                date = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
                year = str(date.year)
                month = date.strftime('%B')
                
                if year not in hierarchy:
                    hierarchy[year] = {}
                if month not in hierarchy[year]:
                    hierarchy[year][month] = 0
                hierarchy[year][month] += 1
            except ValueError:
                continue
        
        for year in sorted(hierarchy.keys(), reverse=True):
            year_item = QStandardItem(f"{year} ({sum(hierarchy[year].values())})")
            year_item.setData(year, Qt.ItemDataRole.UserRole)
            root.appendRow(year_item)
            for month in sorted(hierarchy[year].keys(), key=lambda m: datetime.strptime(m, '%B').month, reverse=True):
                count = hierarchy[year][month]
                month_item = QStandardItem(f"{month} ({count})")
                month_item.setData((year, month), Qt.ItemDataRole.UserRole)
                year_item.appendRow(month_item)

    def populate_customer_filter(self):
        customers = sorted(list(set(job['Customer'] for job in self.all_jobs if 'Customer' in job)))
        self.customer_filter.clear()
        self.customer_filter.addItem("All")
        self.customer_filter.addItems(customers)
        
    def apply_filters(self):
        self.model.removeRows(0, self.model.rowCount())
        
        date_from = self.date_from.date()
        date_to = self.date_to.date()
        customer = self.customer_filter.currentText()
        
        for job in self.all_jobs:
            archive_date_str = job.get('dateArchived', '').split(' ')[0]
            if not archive_date_str:
                continue

            try:
                archive_date = QDate.fromString(archive_date_str, 'yyyy-MM-dd')
                
                # Date filter
                if not (date_from <= archive_date <= date_to):
                    continue
                
                # Customer filter
                if customer != "All" and job.get('Customer') != customer:
                    continue

                self.add_job_to_table(job, status=job.get("Status", "Archived"))
            except Exception as e:
                print(f"Could not filter job: {e}")

    def reset_filters(self):
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        self.date_to.setDate(QDate.currentDate())
        self.customer_filter.setCurrentIndex(0) # "All"
        self.tree_view.clearSelection()
        self.apply_filters()

    def on_tree_selection(self, index):
        item = self.tree_model.itemFromIndex(index)
        data = item.data(Qt.ItemDataRole.UserRole)
        
        if not data:
            return
        
        if isinstance(data, str): # Year selected
            year = int(data)
            self.date_from.setDate(QDate(year, 1, 1))
            self.date_to.setDate(QDate(year, 12, 31))
        elif isinstance(data, tuple): # Month selected
            year, month_str = data
            year = int(year)
            month = datetime.strptime(month_str, '%B').month
            self.date_from.setDate(QDate(year, month, 1))
            self.date_to.setDate(QDate(year, month, 1).addMonths(1).addDays(-1))
            
        self.customer_filter.setCurrentIndex(0) # Reset customer filter
        self.apply_filters()

    def contextMenuEvent(self, event):
        selection_model = self.jobs_table.selectionModel()
        if not selection_model.hasSelection():
            return  
        menu = QMenu(self)
        # menu.addAction("Move to Active", self.move_to_archive) # This needs more implementation
        menu.addAction("Delete Job", self.delete_selected_job)
        menu.exec(event.globalPos())
