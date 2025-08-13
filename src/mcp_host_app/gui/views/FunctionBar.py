from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Signal, Slot
from ..widgets.SlideSwitch import SlideSwitch


class FunctionBar(QWidget):
    '''功能栏'''
    panel_slide_switch_toggled = Signal(bool) # 面板滑动开关切换


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)

        self.panel_slide_switch = SlideSwitch(self)
        self.panel_slide_switch.setFixedSize(38, 19)
        layout.addStretch()
        layout.addWidget(self.panel_slide_switch)

        self.panel_slide_switch.toggled.connect(self.panel_slide_switch_toggled)


    @Slot(bool)
    def set_panel_slide_switch_state(self, state):
        '''设置面板滑动开关状态'''
        self.panel_slide_switch.blockSignals(True)
        self.panel_slide_switch.setChecked(state)
        self.panel_slide_switch.knob_position = 1.0 if state else 0.0
        self.panel_slide_switch.blockSignals(False)