from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Signal, Qt


class InputTextEdit(QTextEdit):
    '''多行文本编辑框'''
    enter_press = Signal()


    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.enter_press.emit()
        else:
            super().keyPressEvent(event)