from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal, Qt, Slot


class ChatHistoryListView(QWidget):
    '''会话历史列表页面'''
    new_chat_clicked = Signal() # 新会话点击
    history_selected = Signal(str) # 历史选择


    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        new_chat_button = QPushButton('新会话')
        self.chat_history_list = QListWidget()
        layout.addWidget(new_chat_button)
        layout.addWidget(self.chat_history_list)

        new_chat_button.clicked.connect(self.new_chat_clicked.emit)
        self.chat_history_list.itemClicked.connect(self.chat_history_select)

    
    @Slot(QListWidgetItem)
    def chat_history_select(self, item):
        thread_id = item.data(Qt.UserRole)
        self.history_selected.emit(thread_id)


    @Slot(list)
    def update_chat_history_list(self, history_list):
        self.chat_history_list.clear()
        for i in history_list:
            item = QListWidgetItem(i['title'])
            item.setData(Qt.UserRole, i['thread_id'])
            self.chat_history_list.addItem(item)