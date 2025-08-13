from PySide6.QtWidgets import QSplitterHandle


class Handle(QSplitterHandle):
    '''分割条把手'''
    def __init__(self, orientation, splitter_parent):
        super().__init__(orientation, splitter_parent)
        self.splitter_parent = splitter_parent
        self.mouse_is_press = False


    def adsorb(self):
        '''吸附'''
        splitter = self.splitter_parent # 提升可读性，方便调试和重构，微乎其微的性能优势
        handle_index = splitter.indexOf(self)

        if handle_index <= 0: return

        left_widget = splitter.widget(handle_index - 1)
        right_widget = splitter.widget(handle_index)
        left_threshold = splitter.thresholds.get(left_widget)
        right_threshold = splitter.thresholds.get(right_widget)

        sizes = splitter.sizes()
        if left_threshold is not None and left_threshold > 0 and sizes[handle_index - 1] < left_threshold:
            if left_widget.isVisible():
                sizes[handle_index] += sizes[handle_index - 1]
                sizes[handle_index - 1] = 0
                splitter.setSizes(sizes)
        if right_threshold is not None and right_threshold > 0 and sizes[handle_index] < right_threshold:
            if right_widget.isVisible():
                sizes[handle_index - 1] += sizes[handle_index]
                sizes[handle_index] = 0
                splitter.setSizes(sizes)


    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.mouse_is_press = True
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.mouse_is_press:
            self.adsorb()
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.mouse_is_press = False
        self.adsorb()