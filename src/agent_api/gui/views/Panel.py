from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import Slot


class Panel(QWidget):
    '''面板'''
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(234)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.graph_state_plain_text_edit = QPlainTextEdit()
        self.graph_state_plain_text_edit.setReadOnly(True)
        layout.addWidget(self.graph_state_plain_text_edit)


    @Slot(str)
    def add_graph_state(self, state):
        '''添加图状态'''
        self.graph_state_plain_text_edit.appendPlainText(state)
        self.graph_state_plain_text_edit.verticalScrollBar().setValue(self.graph_state_plain_text_edit.verticalScrollBar().maximum())


    def clear_state_log(self):
        '''清空图状态日志'''
        self.graph_state_plain_text_edit.clear()