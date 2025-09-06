from PySide6.QtWidgets import QSplitter, QWidget
from PySide6.QtCore import Signal
from .Handle import Handle


class Splitter(QSplitter):
    '''分割器'''
    widget_visibility_changed = Signal(QWidget, bool)


    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)
        self.orientation = orientation
        self.thresholds = {}
        self.widget_visibility_state = {}


        self.setHandleWidth(2)
        self.splitterMoved.connect(self.check_widget_visibility)


    def check_widget_visibility(self):
        '''检查，发送，更新控件可见性状态'''
        sizes = self.sizes()
        for i in range(self.count()):
            widget = self.widget(i)
            widget_is_visible = sizes[i] > 0
            widget_was_visible = self.widget_visibility_state.get(widget)
            if widget_is_visible !=  widget_was_visible:
                self.widget_visibility_changed.emit(widget, widget_is_visible)
                self.widget_visibility_state[widget] = widget_is_visible


    def setSizes(self, list):
        '''设置大小并检查'''
        super().setSizes(list)
        self.check_widget_visibility()
    def addWidget(self, widget, threshold):
        '''添加子控件，吸附阈值，可见性状态'''
        super().addWidget(widget)
        self.thresholds[widget] = threshold
        self.widget_visibility_state[widget] = True
    def createHandle(self):
        '''分割条把手'''
        return Handle(self.orientation, self)