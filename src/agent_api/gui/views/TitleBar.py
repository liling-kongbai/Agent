from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import (
    Slot,
    Qt
)


class TitleBar(QWidget):
    '''标题栏'''
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.mouse_press_position = None
        self.parent_window_position = None


        self.setObjectName('title_bar')
        self.setFixedHeight(33)


        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)


        ico_label = QLabel()
        

        title_label = QLabel('MCPHost')
        title_label.setObjectName('title_label')


        minimize_button = QPushButton('—')
        minimize_button.setObjectName('minimize_button')
        minimize_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        minimize_button.clicked.connect(self.minimize)
        self.maximize_button = QPushButton('☐')
        self.maximize_button.setObjectName('maximize_button')
        self.maximize_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.maximize_button.clicked.connect(self.maximize)
        close_button = QPushButton('✕')
        close_button.setObjectName('close_button')
        close_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        close_button.clicked.connect(self.close)


        layout.addWidget(ico_label)
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(close_button)


    @Slot()
    def minimize(self):
        self.parent_window.showMinimized()
    @Slot()
    def maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.maximize_button.setText('☐')
        else:
            self.parent_window.showMaximized()
            self.maximize_button.setText('❐')
    @Slot()
    def close(self):
        self.parent_window.close()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_press_position = event.globalPosition().toPoint()
            self.parent_window_position = self.parent_window.pos()
            event.accept()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.mouse_press_position is not None:
            delta = event.globalPosition().toPoint() - self.mouse_press_position
            self.parent_window.move(self.parent_window_position + delta)
            event.accept()
    def mouseReleaseEvent(self, event):
        self.mouse_press_position = None
        self.parent_window_position = None
        event.accept()