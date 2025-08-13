from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal, Slot
from .ChatScroll import ChatScroll
from .FunctionBar import FunctionBar
from .InputBar import InputBar


class MainContent(QWidget):
    '''主内容区，对话滚动区，功能栏，输入栏'''
    panel_slide_switch_toggled = Signal(bool) # 面板滑动开关切换
    transmit_input = Signal(str) # 传递输入
    

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(234)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(0)

        self.chat_scroll = ChatScroll() # 对话滚动区
        self.function_bar = FunctionBar() # 功能栏
        self.input_bar = InputBar() # 输入栏
        layout.addWidget(self.chat_scroll, 1)
        layout.addWidget(self.function_bar)
        layout.addWidget(self.input_bar)

        self.function_bar.panel_slide_switch_toggled.connect(lambda toggled: self.panel_slide_switch_toggled.emit(toggled))
        self.input_bar.transmit_input.connect(lambda input: self.transmit_input.emit(input))


    @Slot(str, bool)
    def add_chat_bubble(self, text, is_user):
        '''添加对话气泡'''
        return self.chat_scroll.add_chat_bubble(text, is_user)


    @Slot(bool)
    def set_panel_slide_switch_state(self, state):
        '''设置面板滑动开关状态'''
        self.function_bar.set_panel_slide_switch_state(state)


    @Slot(bool)
    def set_input_text_edit_enabled_and_focus(self, enabled):
        '''设置 input_text_edit 激活状态和焦点'''
        self.input_bar.set_enabled(enabled)
        if enabled:
            self.input_bar.set_focus_input_text_edit()





    def clear_chat_bubbles(self):
        while self.chat_scroll.container_layout.count() > 1:
            item = self.chat_scroll.container_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()