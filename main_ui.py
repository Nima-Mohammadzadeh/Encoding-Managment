# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitled.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QStackedWidget,
    QStatusBar, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(875, 665)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.title_frame = QFrame(self.centralwidget)
        self.title_frame.setObjectName(u"title_frame")
        self.title_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.title_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.title_frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.title_icon = QLabel(self.title_frame)
        self.title_icon.setObjectName(u"title_icon")

        self.horizontalLayout.addWidget(self.title_icon)

        self.title_label = QLabel(self.title_frame)
        self.title_label.setObjectName(u"title_label")

        self.horizontalLayout.addWidget(self.title_label)

        self.menu_btn = QPushButton(self.title_frame)
        self.menu_btn.setObjectName(u"menu_btn")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.menu_btn.sizePolicy().hasHeightForWidth())
        self.menu_btn.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.menu_btn)


        self.gridLayout.addWidget(self.title_frame, 0, 0, 1, 2)

        self.stackedWidget = QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.stackedWidget.addWidget(self.page)
        self.page_2 = QWidget()
        self.page_2.setObjectName(u"page_2")
        self.stackedWidget.addWidget(self.page_2)

        self.gridLayout.addWidget(self.stackedWidget, 0, 2, 2, 1)

        self.listWidget_icon_only = QListWidget(self.centralwidget)
        self.listWidget_icon_only.setObjectName(u"listWidget_icon_only")
        self.listWidget_icon_only.setMaximumSize(QSize(55, 16777215))
        self.listWidget_icon_only.setAutoFillBackground(False)
        self.listWidget_icon_only.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.listWidget_icon_only, 1, 0, 1, 1)

        self.listWidget = QListWidget(self.centralwidget)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setMaximumSize(QSize(200, 16777215))
        self.listWidget.setItemAlignment(Qt.AlignmentFlag.AlignLeading)

        self.gridLayout.addWidget(self.listWidget, 1, 1, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 875, 33))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.title_icon.setText(QCoreApplication.translate("MainWindow", u"TextLabel", None))
        self.title_label.setText(QCoreApplication.translate("MainWindow", u"TextLabel", None))
        self.menu_btn.setText(QCoreApplication.translate("MainWindow", u"PushButton", None))
    # retranslateUi

