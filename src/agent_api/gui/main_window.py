from PySide6.QtCore import Qt, QThread, QTimer, Slot
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from ..core import Backend
from .views import ActivityBar, ChatBubble, MainContent, Panel, Sidebar
from .widgets import Splitter


class MainWindow(QWidget):
    '''主窗口'''

    def __init__(self, config):
        super().__init__()
        self.config = config

        self.current_ai_message_bubble: ChatBubble | None = None
        self.current_sidebar_index = 0
        self.last_sidebar_size = None
        self.last_panel_size = None
        self._shutting_down = False

        self._init_backend()
        self._init_ui()
        self._signal_connect_slot()

        self.thread.start()

    def _init_backend(self):
        '''初始化后端'''
        self.thread = QThread()
        self.mcp_host = Backend(self.config)
        self.mcp_host.moveToThread(self.thread)

    def _init_ui(self):
        '''初始化界面'''
        # --- 主窗口 ---
        self.setWindowTitle('Agent')
        self.resize(1400, 700)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        workspace_layout = QHBoxLayout()  # 工作区
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        layout.addLayout(workspace_layout)

        # --- 工作区 ---
        self.activity_bar = ActivityBar()  # 活动栏
        self.splitter = Splitter(Qt.Horizontal, self)  # 分割器
        self.splitter.setStyleSheet(
            '''
            QSplitter::handle {
                background-color: #625d5c;
            }
            QSplitter::handle:hover {
                background-color: #0078d7;
            }
            '''
        )
        workspace_layout.addWidget(self.activity_bar)
        workspace_layout.addWidget(self.splitter, 1)

        # --- 分割器 ---
        self.sidebar = Sidebar(self)  # 侧边栏
        self.main_content = MainContent()  # 主内容
        self.panel = Panel()  # 面板
        self.splitter.addWidget(self.sidebar, threshold=234)
        self.splitter.addWidget(self.main_content, threshold=-1)
        self.splitter.addWidget(self.panel, threshold=234)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, True)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

    def _signal_connect_slot(self):
        '''信号连接槽'''
        self.mcp_host.occur_error.connect(self.mcp_host_occur_error)
        self.mcp_host.input_ready.connect(self.backend_ready)
        self.mcp_host.graph_ready.connect(self.mcp_host.update_chat_history_list)
        self.mcp_host.input_unready.connect(self.backend_unready)
        self.mcp_host.ai_message_chunk.connect(self.add_ai_message_bubble)
        self.mcp_host.ai_message_chunk_finish.connect(self.ai_message_chunk_finish)
        self.mcp_host.graph_state_update.connect(self.panel.add_graph_state)

        self.mcp_host.load_chat_signal.connect(self.load_chat_history)
        self.mcp_host.update_chat_history_list_signal.connect(self.sidebar.update_chat_history_list)

        self.thread.started.connect(self.mcp_host.start)
        self.thread.started.connect(self.new_chat)

        # self.mcp_host.agent_finish.connect(self.mcp_host_finished)

        self.activity_bar.transmit_changed_button_index.connect(self.update_button_state_and_switch_sidebar)

        self.splitter.widget_visibility_changed.connect(self.widget_visibility_changed)

        self.sidebar.new_chat_clicked.connect(self.new_chat)
        self.sidebar.history_selected.connect(self.load_selected_chat_history)

        self.sidebar.gpt_sovits_toggled.connect(self.mcp_host.activate_gpt_sovits)
        self.sidebar.mcp_server_toggled.connect(self.mcp_host.activate_mcp_client)
        self.sidebar.llm_changed.connect(self.mcp_host.activate_llm)

        self.main_content.transmit_input.connect(self.add_user_message_bubble)
        self.main_content.panel_slide_switch_toggled.connect(self.switch_panel)

    # --- 槽函数 ---
    @Slot()
    def mcp_host_occur_error(self, e):
        '''MCP 主机报错'''
        QMessageBox.critical(self, '后端错误', '\n' + e)

    @Slot()
    def backend_ready(self):
        '''后端准备'''
        self.main_content.set_input_text_edit_enabled_and_focus(True)

    @Slot()
    def backend_unready(self):
        '''后端未准备'''
        self.main_content.set_input_text_edit_enabled_and_focus(False)

    @Slot(str)
    def add_ai_message_bubble(self, chunk):
        '''添加 AI Messgae 气泡'''
        if not self.current_ai_message_bubble:
            self.current_ai_message_bubble = self.main_content.add_chat_bubble('', is_user=False)
        if self.current_ai_message_bubble:
            self.current_ai_message_bubble.add_text(chunk)

    @Slot()
    def ai_message_chunk_finish(self):
        '''AI Message Chunk 结束'''
        self.current_ai_message_bubble = None
        self.main_content.set_input_text_edit_enabled_and_focus(True)

    @Slot()
    def mcp_host_finished(self):
        '''MCP 主机结束'''
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.close()

    @Slot(int)
    def update_button_state_and_switch_sidebar(self, index):
        '''根据按钮索引更新按钮选中状态，折叠，展开，切换侧边栏'''
        self.activity_bar.update_button_state(index)
        current_splitter_sizes = self.splitter.sizes()
        if index == self.current_sidebar_index and current_splitter_sizes[0] > 0:
            self.splitter.setSizes(
                [0, current_splitter_sizes[0] + current_splitter_sizes[1], current_splitter_sizes[2]]
            )
            self.last_sidebar_size = current_splitter_sizes[0]
        else:
            self.sidebar.set_page(index)
            self.current_sidebar_index = index
            if not current_splitter_sizes[0] > 0:
                self.splitter.setSizes(
                    [
                        self.last_sidebar_size,
                        current_splitter_sizes[1] - self.last_sidebar_size,
                        current_splitter_sizes[2],
                    ]
                )

    @Slot(QWidget, bool)
    def widget_visibility_changed(self, widget, widget_visibility):
        '''如果控件被拖拽出，则按钮保持选中，否则反之'''
        if widget is self.sidebar:
            if widget_visibility:
                self.activity_bar.update_button_state(self.current_sidebar_index)
            else:
                self.activity_bar.update_button_state(-1)
        elif widget is self.panel:
            self.main_content.set_panel_slide_switch_state(widget_visibility)

    @Slot(str)
    def add_user_message_bubble(self, text):
        '''添加 User Message 气泡'''
        self.main_content.add_chat_bubble(text, True)
        self.main_content.set_input_text_edit_enabled_and_focus(False)
        self.mcp_host.user_message_input(text)

    @Slot(bool)
    def switch_panel(self, check):
        '''展开折叠面板区'''
        current_splitter_sizes = self.splitter.sizes()
        if check and current_splitter_sizes[2] == 0:
            self.splitter.setSizes(
                [current_splitter_sizes[0], current_splitter_sizes[1] - self.last_panel_size, self.last_panel_size]
            )
        elif not check and current_splitter_sizes[2] > 0:
            self.splitter.setSizes(
                [current_splitter_sizes[0], current_splitter_sizes[1] + current_splitter_sizes[2], 0]
            )
            self.last_panel_size = current_splitter_sizes[2]

    # --- 函数 ---
    def display_window_on_screen_center(self):
        '''显示窗口到屏幕中间'''
        screen_geometry = self.screen().geometry()
        # screen() 获取与窗口或控件相关的屏幕信息
        # geometry() 获取或设置窗口，控件，矩形的几何属性
        window_geometry = self.frameGeometry()
        # frameGeometry() 获取窗口或控件的框架的几何属性
        center_point = screen_geometry.center()
        # center() 获取屏幕或窗口的中心点位置
        window_geometry.moveCenter(center_point)
        # moveCenter() 将窗口或控件的中心点移动到指定位置
        self.move(window_geometry.topLeft())
        # move() 将窗口或控件的左上角移动到指定位置

    def set_splitter_initial_sizes(self):
        '''设置分割器初始大小'''
        current_splitter_width = self.splitter.width()
        mian_content_width = current_splitter_width - 234 * 2
        self.splitter.setSizes([234, mian_content_width, 234])

    # --- 重写 ---
    def showEvent(self, event):
        super().showEvent(event)

        def initial_sync():
            self.set_splitter_initial_sizes()
            self.widget_visibility_changed(self.panel, self.panel.isVisible())
            self.activity_bar.update_button_state(self.current_sidebar_index)
            self.display_window_on_screen_center()
            self.last_sidebar_size, _, self.last_panel_size = self.splitter.sizes()

        QTimer.singleShot(0, initial_sync)  # singleShot() 单次延时执行

    def closeEvent(self, event):
        if self._shutting_down:
            # if self.thread:
            #     self.thread.wait()
            # if hasattr(self, 'mcp_host'):
            #     self.mcp_host = None
            # if hasattr(self, 'thread'):
            #     self.thread = None
            event.ignore()
            return

        if not self.thread and not self.thread.isRunning():
            event.accept()
            return

        self.setEnabled(False)
        self._shutting_down = True
        self.mcp_host.close()

        finished = self.thread.wait(5000)
        if finished:
            print('---------- 后台线程终止 ----------')
        else:
            print('---------- ！！！！！ 等待后台超时 ！！！！！ 可能强制终止 ！！！！！ ----------')

        # event.accept()

    @Slot(list)
    def load_chat_history(self, history):
        self.main_content.clear_chat_bubbles()
        for i in history:
            self.main_content.add_chat_bubble(i['text'], i['is_user'])

    @Slot()
    def new_chat(self):
        self.main_content.clear_chat_bubbles()
        self.panel.clear_state_log()
        self.mcp_host.new_chat()

    @Slot(str)
    def load_selected_chat_history(self, thread_id):
        self.main_content.set_input_text_edit_enabled_and_focus(False)
        self.panel.clear_state_log()
        self.mcp_host.load_chat(thread_id)
