from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget, QListWidgetItem
from PySide6.QtCore import Signal, Slot
from .ChatHistoryListView import ChatHistoryListView
from .SetView import SetView


class Sidebar(QWidget):
    '''侧边栏'''
    new_chat_clicked = Signal() # 新会话点击
    history_selected = Signal(str) # 历史选择
    gpt_sovits_toggled = Signal(bool) # GPT_SoVITS 切换
    mcp_server_toggled = Signal(bool) # MCP 服务器切换
    llm_changed = Signal(str, str) # LLM 更改


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(234)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.chat_history_list_view = ChatHistoryListView() # 会话历史列表页面
        set_view = SetView(self) # 设置页面
        self.stack.addWidget(self.chat_history_list_view)
        self.stack.addWidget(set_view)





        self.chat_history_list_view.new_chat_clicked.connect(self.new_chat_clicked.emit)
        self.chat_history_list_view.history_selected.connect(self.history_selected.emit)






        set_view.gpt_sovits_toggled.connect(lambda activation: self.gpt_sovits_toggled.emit(activation))
        set_view.mcp_server_toggled.connect(lambda activation: self.mcp_server_toggled.emit(activation))
        set_view.llm_changed.connect(lambda llm_platform, llm: self.llm_changed.emit(llm_platform, llm))





    @Slot(QListWidgetItem)
    def chat_history_select(self, item):
        self.chat_history_list_view.chat_history_select(item)


    @Slot(list)
    def update_chat_history_list(self, history_list):
        self.chat_history_list_view.update_chat_history_list(history_list)





    @Slot(int)
    def set_page(self, index):
        '''设置界面'''
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)