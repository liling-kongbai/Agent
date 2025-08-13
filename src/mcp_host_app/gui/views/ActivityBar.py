from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal, Qt, Slot


class ActivityBar(QWidget):
    '''活动栏'''
    transmit_changed_button_index = Signal(int) # 传递更改的按钮索引


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(46)
        self.setStyleSheet('#activity_bar { background-color: #333333;}')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignTop)

        chat_button = QPushButton('Chat')
        chat_button.setCheckable(True)
        set_button = QPushButton('Set')
        set_button.setCheckable(True)
        layout.addWidget(chat_button)
        layout.addWidget(set_button)

        chat_button.clicked.connect(lambda: self.transmit_changed_button_index.emit(0))
        set_button.clicked.connect(lambda: self.transmit_changed_button_index.emit(1))

        self.buttons = [
            chat_button,
            set_button
        ]


    @Slot(int)
    def update_button_state(self, index):
        '''根据按钮索引更新按钮选中状态'''
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)