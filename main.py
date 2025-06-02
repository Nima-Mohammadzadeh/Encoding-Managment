import sys, os
from PySide6.QtWidgets import (QMainWindow, QPushButton, QWidget, QApplication, QMainWindow, QLabel, QToolBar, QInputDialog, QFileDialog, QGridLayout, QLineEdit, QTextEdit, 
                               QMessageBox, QMenu, QToolButton, QInputDialog, QToolBar, QStatusBar, QLabel, QVBoxLayout, QHBoxLayout, QListWidgetItem)
from PySide6.QtCore import QSize, Qt, QPoint, QItemSelection
from PySide6.QtGui import QAction, QIcon, QPixmap, QCursor, QFont
from pathlib import Path
from random import randint, choice
from main_ui import Ui_MainWindow




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.title_label = self.ui.title_label
        self.title_label.setText("Encoding Room Mangager")

        self.title_icon = self.ui.title_icon
        self.title_icon.setText("")
        self.title_icon.setPixmap(QPixmap("src/icons/dashboard.png"))
        self.title_icon.setScaledContents(True)
        

        self.side_menu = self.ui.listWidget
        self.side_menu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.side_menu_icon_only = self.ui.listWidget_icon_only
        self.side_menu_icon_only.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.side_menu_icon_only.hide()

        self.menu_button = self.ui.menu_btn
        self.menu_button.setObjectName("menu_button")
        self.menu_button.setText("")
        self.menu_button.setIcon(QIcon("src/icons/save.png"))
        self.menu_button.setIconSize(QSize(24, 24))
        self.menu_button.setCheckable(True)
        self.menu_button.setChecked(False)

        self.main_content = self.ui.stackedWidget



        #define menu times with names and icons
        self.menu_items = [
            {"name": "Dashboard",
             "icon": "src/icons/dashboard.png",
             "page": "dashboard"
             },
            {"name": "Settings",
             "icon": "src/icons/settings.png",
             "page": "settings"
             },
            {"name": "Help",
             "icon": "src/icons/help.png",
             "page": "help"
             },
        ]
        

        #initlaize the UI elements and slots
        self.init_list_widget()
        self.init_signal_slot()
        self.init_stackwidget()

    def init_signal_slot(self):
        self.menu_button.toggled["bool"].connect(self.side_menu.setHidden)
        self.menu_button.toggled["bool"].connect(self.title_label.setHidden)
        self.menu_button.toggled["bool"].connect(self.title_icon.setHidden)
        self.menu_button.toggled["bool"].connect(self.side_menu_icon_only.setVisible)


        # Connect signals and slot for menu switching
        self.side_menu.currentRowChanged["int"].connect(self.main_content.setCurrentIndex)
        self.side_menu_icon_only.currentRowChanged["int"].connect(self.main_content.setCurrentIndex)
        self.side_menu.currentRowChanged["int"].connect(self.side_menu_icon_only.setCurrentRow)
        self.side_menu_icon_only.currentRowChanged["int"].connect(self.side_menu.setCurrentRow)

        # Connect signals and slot for menu button
        self.menu_button.toggled.connect(self.button_icon_change)

       
    def button_icon_change(self, status):
        if status:
            self.menu_button.setIcon(QIcon("src/icons/open.png"))
        else:
            self.menu_button.setIcon(QIcon("src/icons/close.png"))
            
            
    
    def init_list_widget(self):
        self.side_menu.clear()
        self.side_menu_icon_only.clear()

        for menu in self.menu_items:
            item = QListWidgetItem()
            item.setIcon(QIcon(menu["icon"]))
            item.setSizeHint(QSize(25, 25))
            self.side_menu_icon_only.addItem(item)     
            self.side_menu_icon_only.setCurrentRow(0)


            #Set items for side menu with icons and text
            item_new = QListWidgetItem()
            item_new.setIcon(QIcon(menu["icon"]))
            item_new.setText(menu["name"])
            self.side_menu.addItem(item_new)
            self.side_menu.setCurrentRow(0)


    def init_stackwidget(self):
        # initalize the stack widget with content page
        widget_list = self.main_content.findChildren(QWidget)
        for widget in widget_list:
            self.main_content.removeWidget(widget)

        for menu in self.menu_items:
            text = menu["name"]
            layout = QGridLayout()
            label = QLabel(text=text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = QFont()
            font.setPixelSize(20)
            label.setFont(font)
            layout.addWidget(label)

            new_page = QWidget()
            new_page.setLayout(layout)
            self.main_content.addWidget(new_page)
            

            
            

    def toggle_menu(self):
        checked = self.menu_button.isChecked()
        self.menu_button.setChecked(checked)
        
        






    def the_button_was_clicked(self):
        print("You clicked me!")



 
if __name__ == "__main__":  
    app = QApplication(sys.argv)


    # Load Style file
    with open("src/style.qss", "r") as f:
        style_str = f.read()

    app.setStyleSheet(style_str)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())












