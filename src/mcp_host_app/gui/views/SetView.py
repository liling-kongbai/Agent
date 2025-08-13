from PySide6.QtWidgets import QWidget, QGridLayout, QCheckBox, QLabel, QComboBox
from PySide6.QtCore import Signal, Slot


class SetView(QWidget):
    '''设置页面'''
    gpt_sovits_toggled = Signal(bool) # GPT_SoVITS 切换
    mcp_server_toggled = Signal(bool) # MCP 服务器切换
    llm_changed = Signal(str, str) # LLM 更改


    def __init__(self, parent=None):
        super().__init__(parent)
        self.PLACEHOLDER_TEXT = '请选择模型'
        self.llms = {
            'ollama': ['qwen2.5:3b', 'qwen2.5:7b', 'qwen3:1.7b', 'qwen3:4b', 'qwen3:latest'],
            'deepseek': ['deepseek-chat', 'deepseek-reasoner']
        }


        layout = QGridLayout(self)

        # GPT_SoVITS
        GPT_SoVITS_check = QCheckBox('GPT_SoVITS')
        GPT_SoVITS_check.setChecked(False)
        layout.addWidget(GPT_SoVITS_check, 0, 0)
        GPT_SoVITS_check.toggled.connect(lambda activation: self.gpt_sovits_toggled.emit(activation))
        # MCP 服务器
        mcp_server_check = QCheckBox('mcp_server')
        mcp_server_check.setChecked(False)
        layout.addWidget(mcp_server_check, 0, 1)
        mcp_server_check.toggled.connect(lambda activation: self.mcp_server_toggled.emit(activation))
        # LLM 平台
        layout.addWidget(QLabel('llm_platform'), 1, 0)
        self.llm_platform_combo = QComboBox(editable=False)
        self.llm_platform_combo.addItems(self.llms.keys())
        layout.addWidget(self.llm_platform_combo, 3, 0)
        self.llm_platform_combo.currentTextChanged.connect(self.update_llm_combo)
        # LLM
        layout.addWidget(QLabel('LLM'), 2, 2)
        self.llm_combo = QComboBox(editable=False)
        layout.addWidget(self.llm_combo, 3, 2)
        self.llm_combo.currentIndexChanged.connect(self.on_llm_changed)


        self.llm_platform_combo.setCurrentText(list(self.llms.keys())[0])
        self.update_llm_combo(self.llm_platform_combo.currentText())


    @Slot(str)
    def update_llm_combo(self, llm_platform):
        '''更新 llm_combo'''
        self.llm_changed.emit('', '')
        self.llm_combo.blockSignals(True)
        try:
            self.llm_combo.clear()
            self.llm_combo.addItem(self.PLACEHOLDER_TEXT)
            llms = self.llms.get(llm_platform, [])
            if llms:
                self.llm_combo.addItems(llms)
                self.llm_combo.setCurrentIndex(0)
        finally:
            self.llm_combo.blockSignals(False)


    @Slot(int)
    def on_llm_changed(self, index):
        '''LLM 更改'''
        if index <= 0:
            self.llm_changed.emit('', '')
            return
        self.llm_changed.emit(self.llm_platform_combo.currentText(), self.llm_combo.currentText())