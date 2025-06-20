import json
import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QTableView,
    QHeaderView,
    QSizePolicy,
    QAbstractItemView,
    QMenu
)
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import Qt

class ArchivePageWidget(QWidget):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.save_file = os.path.join(self.base_path, "data", "archived_jobs.json")
        self.network_path = r"Z:\3 Encoding and Printing Files\Archived Jobs"
        layout = QVBoxLayout(self)

        self.model = QStandardItemModel()
        self.headers = ([
        "Customer", "Part#", "Job Ticket#", "PO#",
         "Inlay Type", "Label Size", "Quantity", "Status"
        ])      
        self.model.setHorizontalHeaderLabels(self.headers)
        self.jobs_table = QTableView()
        self.jobs_table.setModel(self.model)
        self.jobs_table.setSizePolicy(QSizePolicy.Policy.Expanding,
    QSizePolicy.Policy.Expanding)
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.setSortingEnabled(True)
        
        self.jobs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.jobs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        header = self.jobs_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        header.setSectionResizeMode(self.headers.index("Customer"), QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.headers.index("Part#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("PO#"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Quantity"), QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.headers.index("Status"), QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.jobs_table)
        self.setLayout(layout)
        self.load_jobs()

    def add_archived_job(self, job_data):
        print(f"Archiving job: {job_data.get('Job Ticket#')}")
        self.add_job_to_table(job_data, status="Archived")
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
    
    def delete_job(self, row_index):
        reply = QMessageBox.question(self, "Confirmation", "Are you sure you want to delete this job?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.model.removeRow(row_index)
            self.save_data()
            self.load_jobs()

    def add_job_to_table(self, job_data, status="Archived"):
        row_items = [
            QStandardItem(job_data.get("Customer", "")),
            QStandardItem(job_data.get("Part#", "")),
            QStandardItem(job_data.get("Job Ticket#", "")),
            QStandardItem(job_data.get("PO#", "")),
            QStandardItem(job_data.get("Inlay Type", "")),
            QStandardItem(job_data.get("Label Size", "")),
            QStandardItem(job_data.get("Qty", "")),
            QStandardItem(status)
        ]
        self.model.appendRow(row_items)

    def load_jobs(self):
        if not os.path.exists(self.save_file):
            print("save file does not exsist. Fresh start")
            return
        
        try:
            with open(self.save_file, "r") as f:
                data = json.load(f)
                
            self.model.removeRows(0, self.model.rowCount()) # Clear existing data
            for job in data:
                status = job.pop("Status", "")
                self.add_job_to_table(job, status=status)
        except Exception as e:
            print("Error loading jobs:", e)

    def save_data(self):
        data_to_save = []

        for row_index in range(self.model.rowCount()):
            job_data = {}
            for col, header in enumerate(self.headers):
                item = self.model.item(row_index, col)
                job_data[header] = item.text() if item else ""
            data_to_save.append(job_data)

        try:
            with open(self.save_file, "w") as f:
                json.dump(data_to_save, f, indent=4)
        except IOError as e:
            print(f"Error saving data: {e}") 
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Move to Active", self.move_to_archive)
        menu.addAction("Delete Job", self.delete_job)
        menu.exec(event.globalPos())
