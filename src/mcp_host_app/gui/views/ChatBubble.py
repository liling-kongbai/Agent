from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class ChatBubble(QWidget):
    '''对话气泡'''
    def __init__(self, text, is_user):
        super().__init__()
        layout = QHBoxLayout(self)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            layout.addStretch(1)
            layout.addWidget(self.label)
            self.setStyleSheet('background-color: #0078FF; color: white; border-radius: 10px; padding: 8px;')
        else:
            self.setStyleSheet('background-color: #E5E5EA; color: black; border-radius: 10px; padding: 8px;')
            layout.addWidget(self.label)
            layout.addStretch(1)


    def add_text(self, new_text):
        '''增加文本'''
        current_text = self.label.text()
        self.label.setText(current_text + new_text)