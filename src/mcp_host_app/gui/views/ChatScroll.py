from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PySide6.QtCore import Slot
from .ChatBubble import ChatBubble


class ChatScroll(QScrollArea):
    '''对话滚动区'''
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: 2px solid #D3D3D3; }")

        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.addStretch()
        self.setWidget(container)

        self.verticalScrollBar().rangeChanged.connect(self.scroll_to_bottom)


    @Slot(int, int)
    def scroll_to_bottom(self, min_value, max_value):
        '''滚动到底部'''
        self.verticalScrollBar().setValue(max_value)


    @Slot(str, bool)
    def add_chat_bubble(self, text, is_user):
        '''添加对话气泡'''
        chat_bubble = ChatBubble(text, is_user)
        self.container_layout.insertWidget(self.container_layout.count() - 1, chat_bubble)
        return chat_bubble