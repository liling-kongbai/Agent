import asyncio
import threading
import traceback
import uuid

from PySide6.QtCore import QObject, Signal, Slot

from ..utils import logger
from . import Agent


class Backend(QObject):
    '''后端，响应前端，启动服务'''

    occur_error = Signal(str)  # 报错

    ai_message_chunk = Signal(str)  # AI Message Chunk
    ai_message_chunk_finish = Signal()  # AI Message Chunk 结束
    graph_state_update = Signal(str)  # 图状态更新

    mcp_host_finish = Signal()  # MCP 主机结束信号
    input_ready = Signal()  # 输入准备，后端准备就绪
    input_unready = Signal()  # 输入未准备，后端未准备就绪
    graph_ready = Signal()  # 图结构准备，图结构准备就绪

    load_chat = Signal(list)  # 加载对话 # ??????????
    update_history_list = Signal(list)  # 更新历史列表

    def __init__(self, config):
        super().__init__()
        self._agent = Agent(config)

        # ---------- 事件相关 ----------
        self._thread = None
        self._event_loop = None

    # ---------- 启动 ----------
    @Slot()
    def start(self):
        '''槽函数，启动 Agent，创建线程，事件循环，任务'''
        logger.debug('<start> 启动 Agent')
        try:
            logger.debug('<start> 创建并设置线程和事件循环')
            self._thread = threading.Thread(target=self._create_event_loop, daemon=True)
            self._thread.start()
            asyncio.run_coroutine_threadsafe(self._init_agent(), self._event_loop)
            # run_coroutine_threadsafe() 从同步线程中调度协程到指定事件循环中执行
        except:
            error = traceback.format_exc()
            self.occur_error.emit('<start>\n' + error)
            logger.error('<start>\n' + error)

    def _create_event_loop(self):
        '''创建，设置，运行事件循环'''
        logger.debug('<_run_event_loop> 创建，设置，运行事件循环')
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)  # set_event_loop() 指定事件循环为当前线程默认事件循环
        self._event_loop.run_forever()  # run_forever() 启动事件循环并一直运行，直到被显式停止或程序退出

    async def _init_agent(self):
        '''初始化 Agent'''
        logger.debug('<_init_agent> 初始化 Agent')
        try:
            await self._agent.init_graph()
        except:
            error = traceback.format_exc()
            self.occur_error.emit('<_init_agent>\n' + error)
            logger.error('<_init_agent>\n' + error)

    # ---------- 关闭 ----------
    @Slot()
    def close(self):
        '''槽函数，关闭 Agent，运行清理任务，关闭并清理事件件循环，线程，任务'''
        logger.debug('<close> 关闭 Agent')
        if self._event_loop and self._event_loop.is_running():
            logger.debug('<close> 执行关闭任务')
            self._event_loop.call_soon_threadsafe(asyncio.create_task(self._shutdown_task()))
            # call_soon_threadsafe() 线程安全地向事件循环提交回调函数，确保该回调函数在事件循环所在的线程中尽快执行
        else:
            logger.warning('<close> 事件循环不存在或未运行！！！')
            self.mcp_host_finish.emit()

    def _shutdown_task(self):
        '''关闭任务'''
        logger.debug('<_shutdown_task> 关闭任务')
        asyncio.create_task(self._shutdown())  # create_task() 将协程包装为任务，立即运行，不阻塞，允许并发

    async def _shutdown(self):
        '''关闭'''
        logger.debug('<_shutdown> 关闭')
        try:
            logger.debug('<_shutdown> 开始清理')
            await self._clean()
        except:
            error = traceback.format_exc()
            self.occur_error.emit('<_shutdown>\n' + error)
            logger.debug('<_shutdown>\n' + error)
        finally:
            logger.debug('<_shutdown> 停止事件循环')
            self._event_loop.stop()
            self.mcp_host_finish.emit()

    async def _clean(self):
        '''清理，在事件循环关闭前，执行所有必要的异步清理操作'''
        logger.debug('<_clean> 清理')
        await self._agent.activate_gpt_sovits(False)
        await self._agent.activate_mcp_client(False)
        await self._agent.activate_llm('', '')

        if self._agent.async_sqlite_saver and self._agent.db_connection:
            logger.debug('<_clean> 清理图结构，清理异步 SQLite 文件检查点保存器，关闭并清理数据库')
            self._agent.graph = None
            self._agent.async_sqlite_saver = None
            await self._agent.db_connection.close()
            self._agent.db_connection = None

    # ---------- 动态服务 ----------
    @Slot(str, str)
    def activate_llm(self, platform, model):
        '''槽函数，激活 LLM'''
        logger.debug('<activate_llm> 激活 LLM')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.activate_llm(platform, model), self._event_loop)

    @Slot(bool)
    def activate_mcp_client(self, activation):
        '''槽函数，激活 MCP 客户端'''
        logger.debug('<activate_mcp_client> 激活 MCP 客户端')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.activate_mcp_client(activation), self._event_loop)

    @Slot(str)
    def user_message_input(self, input):
        '''User Message 输入'''
        if self._event_loop and self._event_loop.is_running():
            callbacks = {
                'on_occur_error': self._create_signal_emit_callback(self.occur_error),
                'on_ai_message_chunk': self._create_signal_emit_callback(self.ai_message_chunk),
                'on_ai_message_chunk_finish': self._create_signal_emit_callback(self.ai_message_chunk_finish),
                'on_graph_state_chunk': self._create_signal_emit_callback(self.graph_state_update),
            }
            asyncio.run_coroutine_threadsafe(
                self._agent.user_message_input(self._agent.current_thread_id(), input, callbacks), self._event_loop
            )

    # ---------- 基础功能 ----------
    @Slot()
    def new_chat(self):
        '''槽函数，新建对话'''
        logger.debug('<new_chat> 新建对话')
        self._agent.current_thread_id = str(uuid.uuid4())
        self.load_chat_history.emit([])  # ??????????

    @Slot(str)
    def load_chat(self, thread_id):
        '''槽函数，加载对话'''
        logger.debug('<load_chat> 加载对话')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.load_chat(thread_id), self._event_loop)

    @Slot()
    def update_history_list(self):
        '''槽函数，更新历史列表'''
        logger.debug('<update_histor_list> 更新历史列表')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.update_history_list(), self._event_loop)

    # ---------- 辅助 ----------
    def _create_signal_emit_callback(self, signal: Signal):
        '''创建信号发射回调'''

        async def signal_emit(*args):
            '''信号发射'''
            event_loop = asyncio.get_running_loop()
            event_loop.call_soon_threadsafe(signal.emit, *args)

        return signal_emit

    # @Slot(bool)
    # def activate_gpt_sovits(self, activation):
    #     '''槽函数，激活 GPT_SoVITS'''
    #     logger.debug('activate_gpt_sovits --- 激活 GPT_SoVITS 槽函数')
    #     if self._event_loop and self._event_loop.is_running():
    #         future = asyncio.run_coroutine_threadsafe(self._agent.activate_gpt_sovits(activation), self._event_loop)
