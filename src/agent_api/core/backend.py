import asyncio
import logging
import traceback
import uuid

from PySide6.QtCore import QObject, Signal, Slot

from ..utils import create_logger

logger = create_logger(
    is_use_console_handler=True, console_handler_level=logging.DEBUG, is_use_file_handler=True, log_path='backend.log'
)


from .agent import Agent


class Backend(QObject):
    '''后端。响应前端，连接服务'''

    occur_error_signal = Signal(str)  # 报错信号

    agent_finish_signal = Signal()  # agent 结束信号

    graph_ready_signal = Signal()  # 图结构准备信号，图结构准备就绪
    input_ready_signal = Signal()  # 输入准备信号，后端准备就绪
    input_unready_signal = Signal()  # 输入未准备信号，后端未准备就绪

    ai_message_chunk_signal = Signal(str)  # AI Message Chunk 信号
    ai_message_chunk_finish_signal = Signal()  # AI Message Chunk 结束信号
    graph_state_update_signal = Signal(str)  # 图状态更新信号

    load_chat_signal = Signal(list)  # 加载对话信号
    update_chat_history_signal = Signal(list)  # 更新对话历史信号

    def __init__(self, config):
        super().__init__()
        self._agent = Agent(config)
        self._agent.add_listener(self)

        # 事件相关
        self._thread = None
        self._event_loop = None

    # ---------- 启动 ----------
    @Slot()
    def start(self):
        '''槽函数，启动。创建并启动线程，运行 Agent'''
        logger.debug('<start> 启动')
        try:
            # logger.debug('<start> 创建并启动线程，运行 Agent')
            # self._thread = threading.Thread(target=self._run_agent, daemon=True)
            # self._thread.start()
            self._run_agent()
        except:
            error = traceback.format_exc()
            self.occur_error_signal.emit('<start>\n' + error)
            logger.error('<start>\n' + error)

    def _run_agent(self):
        '''运行 Agent。创建并设置事件循环，初始化图'''
        logger.debug('<_run_agent> 运行 Agent')
        try:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)  # set_event_loop() 指定事件循环为当前线程默认事件循环
            self._event_loop.create_task(
                self._agent.init_graph()
            )  # create_task() 将协程包装为任务，立即运行，不阻塞，允许并发
            self._event_loop.run_forever()  # run_forever() 启动事件循环并一直运行，直到被显式停止或程序退出
        except:
            error = traceback.format_exc()
            self.occur_error_signal.emit('<_run_agent>\n' + error)
            logger.error('<_run_agent>\n' + error)
        finally:
            if self._event_loop:
                logger.debug('<_shutdown> 关闭事件循环')
                self._event_loop.close()  # close() 把事件循环内部所有队列，句柄，IO 资源清空并关闭，该循环对象永久报废，不能再启动

                if self._event_loop.is_closed():
                    logger.debug('<_shutdown 事件循环已关闭>')
                    self.agent_finish_signal.emit()
                else:
                    logger.warning('<_shutdown> 事件循环未关闭！！！！！')
            else:
                logger.warning('<_shutdown> 事件循环已关闭！！！！！')

    # ---------- 关闭 ----------
    @Slot()
    def close(self):
        '''槽函数，关闭。运行关闭，关闭 Agent'''
        logger.debug('<close> 关闭')
        if self._event_loop and self._event_loop.is_running():
            logger.debug('<close> 运行关闭任务')
            asyncio.run_coroutine_threadsafe(
                self._shutdown(), self._event_loop
            )  # run_coroutine_threadsafe() 从同步线程中调度协程到指定事件循环中运行
        else:
            logger.warning('<close> 事件循环不存在或未运行！！！！！')
            self.agent_finish_signal.emit()

    async def _shutdown(self):
        '''关闭。在关闭之前，等待所有当前正在运行的任务完成，再运行清理'''
        logger.debug('<_shutdown> 关闭')
        try:
            logger.debug('<_shutdown> 等待所有当前正在运行的任务完成')
            pending_tasks = [
                task for task in asyncio.all_tasks(self._event_loop) if task is not asyncio.current_task()
            ]  # all_tasks() 返回当前正在运行的事件循环中所有未完成的任务  current_task() 返回当前正在运行的协程所在的 Task 示例

            if pending_tasks:
                for pending_task in pending_tasks:
                    pending_task.cancel()
                await asyncio.gather(*pending_tasks, return_exceptions=True)
            if pending_tasks:
                await asyncio.wait(pending_tasks, timeout=20.0)

            logger.debug('<_shutdown> 清理')
            await self._agent.clean()
        except:
            error = traceback.format_exc()
            self.occur_error_signal.emit('<_shutdown>\n' + error)
            logger.debug('<_shutdown>\n' + error)
        finally:
            if self._event_loop.is_running():
                logger.debug('<_shutdown> 停止事件循环')
                self._event_loop.stop()  # stop() 让事件循环在本轮回调全部执行完后立即退出 run_forever() / run_until_complete()，但不清理任何资源，也不终止协程，可再次启动
            else:
                logger.warning('<_shutdown> 事件循环未运行！！！！！')

            self.agent_finish_signal.emit()

    # ---------- 动态服务 ----------
    @Slot(str, str)
    def activate_llm(self, platform, model):
        '''槽函数，激活 LLM。'''
        logger.debug('<activate_llm> 激活 LLM')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.activate_llm(platform, model), self._event_loop)

    @Slot(bool)
    def activate_mcp_client(self, activation):
        '''槽函数，激活 MCP 客户端。'''
        logger.debug('<activate_mcp_client> 激活 MCP 客户端')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.activate_mcp_client(activation), self._event_loop)

    @Slot(bool)
    def activate_gpt_sovits(self, activation):
        '''槽函数，激活 GPT_SoVITS。'''
        logger.debug('<activate_gpt_sovits> 激活 GPT_SoVITS')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.activate_gpt_sovits(activation), self._event_loop)

    # ---------- 运行 ----------
    @Slot(str)
    def user_message_input(self, input):
        '''槽函数，User Message 输入。'''
        if self._event_loop and self._event_loop.is_running():
            callbacks = {
                'ai_message_chunk_signal': self._create_signal_emit_callback(self.ai_message_chunk_signal),
                'ai_message_chunk_finish_signal': self._create_signal_emit_callback(
                    self.ai_message_chunk_finish_signal
                ),
                'graph_state_update_signal': self._create_signal_emit_callback(self.graph_state_update_signal),
            }
            asyncio.run_coroutine_threadsafe(self._agent.user_message_input(input, callbacks), self._event_loop)

    # ---------- 对话历史 ----------
    @Slot()
    def new_chat(self):
        '''槽函数，新建对话。'''
        logger.debug('<new_chat> 新建对话')
        self._agent.current_thread_id = str(uuid.uuid4())
        self.load_chat_signal.emit([])  # ！！！！！这里要弄懂

    @Slot(str)
    def load_chat(self, thread_id):
        '''槽函数，加载对话。'''
        logger.debug('<load_chat> 加载对话')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.load_chat(thread_id), self._event_loop)

    @Slot()
    def update_chat_history(self):
        '''槽函数，更新对话历史列表。'''
        logger.debug('<update_histor_list> 更新历史列表')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.update_chat_history(), self._event_loop)

    # ---------- 辅助 ----------
    def _create_signal_emit_callback(self, signal: Signal):
        '''创建信号发射回调。'''

        async def signal_emit(*args):
            '''信号发射。'''
            event_loop = asyncio.get_running_loop()
            event_loop.call_soon_threadsafe(signal.emit, *args)

        return signal_emit

    # ---------- 监听与广播 ----------
    def occur_error_signal_monitor(self, occur_error: str):
        '''报错监听。'''
        self.occur_error_signal.emit(occur_error)

    def graph_ready_signal_monitor(self):
        '''图准备监听'''
        self.graph_ready_signal.emit()

    def input_ready_signal_monitor(self):
        '''输入准备监听'''
        self.input_ready_signal.emit()

    def input_unready_signal_monitor(self):
        '''输入未准备监听'''
        self.input_unready_signal.emit()

    def load_chat_signal_monitor(self, chat_history: list):
        '''加载对话监听'''
        self.load_chat_signal.emit(chat_history)

    def update_chat_history_list_signal_monitor(self, chat_history_list: list):
        '''跟新对话历史列表监听'''
        self.update_chat_history_signal.emit(chat_history_list)
