from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class Panel(QWidget):
    '''面板'''
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(234)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('正在开发中！！！！！'))