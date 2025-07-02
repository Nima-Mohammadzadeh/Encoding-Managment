import json
import os
import shutil
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

from src.widgets.job_details_dialog import JobDetailsDialog, FileOperationProgressDialog
import src.config as config

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt, QDate

class ArchivePageWidget(QWidget):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        # The primary source of truth is now the directory, not a single file.
        self.archive_dir = config.ARCHIVE_DIR
        
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
        header.setSectionResizeMode(self.headers.index("Customer"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Part#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Job Ticket#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("PO#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Inlay Type"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Label Size"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Quantity"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Status"), QHeaderView.ResizeMode.ResizeToContents)
        content_layout.addWidget(self.jobs_table)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        # Connect double-click signal
        self.jobs_table.doubleClicked.connect(self.open_job_details)

    def add_archived_job(self, job_data):
        job_folder_path = job_data.get('job_folder_path')
        if not job_folder_path or not os.path.exists(job_folder_path):
            QMessageBox.warning(self, "Archive Error", "Original job folder not found. Cannot archive.")
            return

        # The new destination for the job folder is inside the main archive directory
        destination_folder_name = os.path.basename(job_folder_path)
        destination_path = os.path.join(self.archive_dir, destination_folder_name)

        # Check if destination already exists
        if os.path.exists(destination_path):
            QMessageBox.warning(
                self, 
                "Archive Error", 
                f"A job with the same name already exists in the archive: {destination_folder_name}"
            )
            return

        # Store job data for later use in callback
        self.temp_archive_job_data = job_data.copy()
        self.temp_archive_destination = destination_path

        # Use threaded file operation for potentially large moves
        progress_dialog = FileOperationProgressDialog(
            'move', job_folder_path, destination_path, job_data, self
        )
        
        # Connect completion signal
        progress_dialog.operation_finished.connect(self.on_archive_operation_finished)
        
        # Show the dialog
        progress_dialog.exec()

    def on_archive_operation_finished(self, success, message):
        """Handle completion of archive operation."""
        if not hasattr(self, 'temp_archive_job_data'):
            return
            
        job_data = self.temp_archive_job_data
        destination_path = self.temp_archive_destination
        
        # Clean up temporary data
        delattr(self, 'temp_archive_job_data')
        delattr(self, 'temp_archive_destination')
        
        if success:
            try:
                # Update the job's folder path to its new location
                job_data['job_folder_path'] = destination_path
                
                # Save the job metadata inside the newly moved folder
                job_data['dateArchived'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                metadata_path = os.path.join(destination_path, 'job_data.json')
                with open(metadata_path, 'w') as f:
                    json.dump(job_data, f, indent=4)
                
                # Add to the view
                self.all_jobs.append(job_data)
                self.update_archive_display()
                QMessageBox.information(self, "Success", f"Job moved to archive:\n{destination_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Archive Error", f"Job moved but could not update metadata:\n{e}")
        else:
            QMessageBox.critical(self, "Archive Error", f"Could not move job to archive:\n{message}")

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
        
        reply = QMessageBox.question(
            self, "Confirmation", "Are you sure you want to delete this job?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            selected_row_index = selection_model.selectedRows()[0]
            job_to_remove = self._get_job_data_for_row(selected_row_index.row())
            
            job_folder_path = job_to_remove.get('job_folder_path')
            if job_folder_path and os.path.exists(job_folder_path):
                reply = QMessageBox.question(
                    self, "Delete Folder", 
                    f"This will permanently delete the folder and all its contents:\n{job_folder_path}\n\nAre you sure?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # Store data for callback
                    self.temp_delete_job_data = job_to_remove
                    self.temp_delete_row_index = selected_row_index.row()
                    
                    # Use threaded deletion for potentially large folders
                    progress_dialog = FileOperationProgressDialog(
                        'delete', job_folder_path, None, job_to_remove, self
                    )
                    
                    # Connect completion signal
                    progress_dialog.operation_finished.connect(self.on_delete_operation_finished)
                    
                    # Show the dialog
                    progress_dialog.exec()
            else:
                QMessageBox.warning(self, "Delete Error", "Could not find job folder to delete.")

    def on_delete_operation_finished(self, success, message):
        """Handle completion of delete operation."""
        if not hasattr(self, 'temp_delete_job_data'):
            return
            
        job_to_remove = self.temp_delete_job_data
        row_index = self.temp_delete_row_index
        
        # Clean up temporary data
        delattr(self, 'temp_delete_job_data')
        delattr(self, 'temp_delete_row_index')
        
        if success:
            # Remove from the list and table
            job_folder_path = job_to_remove.get('job_folder_path')
            self.all_jobs = [j for j in self.all_jobs if j.get('job_folder_path') != job_folder_path]
            self.model.removeRow(row_index)
            QMessageBox.information(self, "Deleted", "Job folder has been deleted.")
        else:
            QMessageBox.critical(self, "Delete Error", f"Could not delete folder:\n{message}")

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
        self.all_jobs = []
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)
            return
        
        for folder_name in os.listdir(self.archive_dir):
            job_folder_path = os.path.join(self.archive_dir, folder_name)
            if os.path.isdir(job_folder_path):
                metadata_path = os.path.join(job_folder_path, 'job_data.json')
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            job_data = json.load(f)
                            # Ensure the path is correct for later use (like deleting)
                            job_data['job_folder_path'] = job_folder_path
                            self.all_jobs.append(job_data)
                    except Exception as e:
                        print(f"Error loading job data from {metadata_path}: {e}")

        self.update_archive_display()
        self.populate_customer_filter()
        self.apply_filters()

    def save_data(self):
        # This function is no longer needed as we save data in individual json files.
        pass
    
    def _get_job_data_for_row(self, row):
        """
        Safely retrieves the full job data dictionary from the master list
        (self.all_jobs) that corresponds to the given visible row in the table,
        accounting for sorting and filtering.
        """
        if row < 0 or row >= self.model.rowCount():
            return None

        # Get unique identifiers from the visible row in the model
        try:
            job_ticket_col = self.headers.index("Job Ticket#")
            po_num_col = self.headers.index("PO#")
        except ValueError:
            # This should not happen if headers are consistent
            return None

        job_ticket_item = self.model.item(row, job_ticket_col)
        po_num_item = self.model.item(row, po_num_col)

        if not job_ticket_item or not po_num_item:
            return None

        job_ticket = job_ticket_item.text()
        po_num = po_num_item.text()

        # Find the corresponding job in the full list of jobs
        for job in self.all_jobs:
            if job.get("Job Ticket#") == job_ticket and job.get("PO#") == po_num:
                return job  # Return the full dictionary
        
        return None # Return None if no match is found

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

    def open_job_details(self, index):
        if not index.isValid():
            return

        row = index.row()
        job_data = self._get_job_data_for_row(row)
        
        if not job_data:
            QMessageBox.warning(self, "Error", "Could not retrieve job data.")
            return

        dialog = JobDetailsDialog(job_data, self.base_path, self)
        dialog.setWindowTitle(f"Archived Job Details: {job_data.get('Job Ticket#', 'N/A')}")
        
        # Make the dialog read-only
        dialog.edit_btn.setEnabled(False)
        
        # Disable specific buttons by object name if they are set
        complete_btn = dialog.findChild(QPushButton, "complete_btn")
        if complete_btn:
            complete_btn.setEnabled(False)
        
        archive_btn = dialog.findChild(QPushButton, "archive_btn")
        if archive_btn:
            archive_btn.setEnabled(False)
        
        delete_btn = dialog.findChild(QPushButton, "deleteButton")
        if delete_btn:
            delete_btn.setEnabled(False)

        dialog.exec()
