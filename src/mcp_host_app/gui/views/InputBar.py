from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal, Slot
from ..widgets.InputTextEdit import InputTextEdit


class InputBar(QWidget):
    '''输入栏'''
    transmit_input = Signal(str) # 传递输入


    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        self.input_text_edit = InputTextEdit()
        self.input_text_edit.setFixedHeight(60)
        self.input_text_edit.setEnabled(False)
        self.send_button = QPushButton('发送')
        self.send_button.setEnabled(False)
        layout.addWidget(self.input_text_edit)
        layout.addWidget(self.send_button)

        self.input_text_edit.enter_press.connect(self.transmit_and_clear)
        self.send_button.clicked.connect(self.transmit_and_clear)


    @Slot()
    def transmit_and_clear(self):
        '''获取文本并传递，清空编辑框'''
        text = self.input_text_edit.toPlainText().strip()
        if text:
            self.transmit_input.emit(text)
        self.input_text_edit.clear()


    def set_enabled(self, enabled):
        '''设置激活状态'''
        self.input_text_edit.setEnabled(enabled)
        self.send_button.setEnabled(enabled)


    def set_focus_input_text_edit(self):
        '''设置编辑框焦点'''
        self.input_text_edit.setFocus()