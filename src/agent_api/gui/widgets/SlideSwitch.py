from PySide6.QtWidgets import QAbstractButton
from PySide6.QtCore import (
    QPointF, Slot, Qt, Property,
    QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import (
    QPainter, QBrush,
    QColor
)


class SlideSwitch(QAbstractButton):
    '''滑动开关'''
    def __init__(self, parent, track_color_off=QColor('#d0d0d0'), track_color_on=QColor('#0078d7'), knob_color=QColor('#f0f0f0')):
        super().__init__(parent)
        self._track_color_off = track_color_off
        self._track_color_on = track_color_on
        self._knob_color = knob_color
        self._knob_position = 0.0 

        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self._toggled_on)

        self.animation = QPropertyAnimation(self, b'knob_position', self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(300)
        

    def paintEvent(self, event):
        '''绘制滑动开关'''
        track_height = self.height()
        track_radius = track_height / 2
        track_color = self._track_color_on if self.isChecked() else self._track_color_off
        padding = 2
        knob_height = self.height() - padding * 2
        knob_radius = knob_height / 2
        knob_x = padding + self._knob_position * (self.width() - knob_height - 2 * padding)


        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing) # 抗锯齿渲染
        painter.setPen(Qt.NoPen)

        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(0, (self.height() - track_height) / 2, self.width(), track_height, track_radius, track_radius)
        painter.setBrush(QBrush(self._knob_color))
        painter.drawEllipse(QPointF(knob_x + knob_radius, self.height() / 2), knob_radius, knob_radius)


    @Slot(bool)
    def _toggled_on(self, checked):
        '''启动动画'''
        self.animation.setStartValue(self._knob_position)
        self.animation.setEndValue(1.0 if checked else 0.0)
        self.animation.start()


    @Property(float)
    def knob_position(self):
        return self._knob_position
    @knob_position.setter
    def knob_position(self, position):
        self._knob_position = position
        self.update()