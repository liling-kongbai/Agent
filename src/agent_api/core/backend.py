import asyncio
import logging
import threading
import traceback
import uuid

from PySide6.QtCore import QObject, Signal, Slot

from ..utils import create_logger

logger = create_logger(
    is_use_console_handler=True, console_handler_level=logging.DEBUG, is_use_file_handler=True, log_path='backend.log'
)

from .agent import Agent


class Backend(QObject):
    '''后端，响应前端，连接后端'''

    occur_error = Signal(str)  # 报错

    # agent_finish = Signal()  # agent 结束

    graph_ready = Signal()  # 图结构准备，图结构准备就绪
    input_ready = Signal()  # 输入准备，后端准备就绪
    input_unready = Signal()  # 输入未准备，后端未准备就绪

    ai_message_chunk = Signal(str)  # AI Message Chunk
    ai_message_chunk_finish = Signal()  # AI Message Chunk 结束
    graph_state_update = Signal(str)  # 图状态更新

    load_chat_signal = Signal(list)  # 加载对话
    update_chat_history_list_signal = Signal(list)  # 更新对话历史列表

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
        '''槽函数，启动。创建线程，事件循环，任务，运行 Agent'''
        logger.debug('<start> 启动')
        try:
            logger.debug('<start> 创建并启动线程，运行后台任务，运行 Agent')
            self._thread = threading.Thread(target=self._run_agent, daemon=True)
            self._thread.start()
        except:
            error = traceback.format_exc()
            self.occur_error.emit('<start>\n' + error)
            logger.error('<start>\n' + error)

    def _run_agent(self):
        '''运行 Agent。创建并设置事件循环'''
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
            self.occur_error.emit('<_run_agent>\n' + error)
            logger.error('<_run_agent>\n' + error)

    # ---------- 关闭 ----------
    @Slot()
    def close(self):
        '''槽函数，关闭。运行关闭任务，关闭并清理事件件循环，关闭 Agent'''

        # ！！！！！这里不用清理 threading 吗？

        logger.debug('<close> 关闭')
        if self._event_loop and self._event_loop.is_running():
            logger.debug('<close> 运行关闭任务')
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._event_loop)
        else:
            logger.warning('<close> 事件循环不存在或未运行！！！')
            # self.agent_finish.emit()

    # async def _shutdown(self):
    #     '''关闭。并在关闭之前，等待所有当前正在运行的任务完成，再执行清理'''
    #     logger.debug('<_shutdown> 关闭')
    #     try:
    #         logger.debug('<_shutdown> 等待所有当前正在运行的任务完成')
    #         pending_tasks = [
    #             task for task in asyncio.all_tasks(self._event_loop) if task is not asyncio.current_task()
    #         ]  # all_tasks() 返回当前正在运行的事件循环中所有未完成的任务  current_task() 返回当前正在运行的协程所在的 Task 示例

    #         if pending_tasks:
    #             await asyncio.wait(pending_tasks, timeout=20)

    #         logger.debug('<_shutdown> 运行清理')
    #         await self._agent.clean()
    #     except:
    #         error = traceback.format_exc()
    #         self.occur_error.emit('<_shutdown>\n' + error)
    #         logger.debug('<_shutdown>\n' + error)
    #     finally:
    #         logger.debug('<_shutdown> 停止事件循环')
    #         if self._event_loop:
    #             self._event_loop.stop()
    #             # self.agent_finish.emit()

    # backend.py -> _shutdown (带有详细日志的版本)

    async def _shutdown(self):
        '''
        关闭。首先取消所有正在运行的任务，等待它们结束后再执行清理，
        最后停止事件循环。
        '''
        logger.debug('<_shutdown> 开始异步关闭流程')

        # 1. 获取当前事件循环中除了自身以外的所有任务
        tasks = [t for t in asyncio.all_tasks(loop=self._event_loop) if t is not asyncio.current_task()]

        # 2. 如果有正在运行的任务，【打印它们的详细信息】
        if tasks:
            logger.info(f'--- 发现 {len(tasks)} 个正在运行的任务需要关闭 ---')
            for i, task in enumerate(tasks):
                # 尝试获取任务的名字（如果设置了）
                task_name = task.get_name()
                # 获取任务正在执行的协程
                coro = task.get_coro()
                logger.info(f"  任务 #{i+1}:")
                logger.info(f"    - 名称: {task_name}")
                logger.info(f"    - 协程: {coro.__qualname__ if hasattr(coro, '__qualname__') else coro}")
                # done(), cancelled(), exception() 等方法可以提供更多状态信息
                logger.info(f"    - 状态: done={task.done()}, cancelled={task.cancelled()}")
            logger.info('-----------------------------------------')

            # 3. 向它们发送取消请求 (这部分不变)
            logger.debug(f'<_shutdown> 正在取消 {len(tasks)} 个挂起的任务...')
            for task in tasks:
                task.cancel()

            # 4. 等待所有任务真正地完成 (这部分不变)
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug('<_shutdown> 所有挂起的任务已取消并结束。')
        else:
            logger.info("--- 没有正在运行的任务需要关闭 ---")

        # 5. 安全地执行清理 (这部分不变)
        try:
            logger.debug('<_shutdown> 运行清理')
            await asyncio.wait_for(self._agent.clean(), timeout=5.0)
            logger.info('<_shutdown> [诊断] 清理已成功结束。')  # <--- 如果你没看到这条日志，说明 _clean 卡住了
        except asyncio.TimeoutError:
            logger.error('<_shutdown> 清理操作超时！')
        except Exception:
            error = traceback.format_exc()
            # self.occur_error.emit(f'<_shutdown> 清理时出错:\n{error}')
            logger.error(f'<_shutdown> 清理时出错:\n{error}')
        finally:
            # 6. 最后，停止事件循环 (这部分不变)
            logger.debug('<_shutdown> 停止事件循环')
            if self._event_loop and self._event_loop.is_running():
                self._event_loop.stop()

            # self.agent_finish.emit()

    # ---------- 动态服务 ----------
    @Slot(str, str)
    def activate_llm(self, platform, model):
        '''槽函数，激活 LLM。'''
        logger.debug('<activate_llm> 激活 LLM')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._agent.activate_llm(platform, model), self._event_loop
            )  # run_coroutine_threadsafe() 从同步线程中调度协程到指定事件循环中执行

    @Slot(bool)
    def activate_mcp_client(self, activation):
        '''槽函数，激活 MCP 客户端。'''
        logger.debug('<activate_mcp_client> 激活 MCP 客户端')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.activate_mcp_client(activation), self._event_loop)

    @Slot(bool)
    def activate_gpt_sovits(self, activation):
        '''槽函数，激活 GPT_SoVITS。'''
        logger.debug('<activate_gpt_sovits> 激活 GPT_SoVITS 槽函数')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.activate_gpt_sovits(activation), self._event_loop)

    # ---------- 运行 ----------
    @Slot(str)
    def user_message_input(self, input):
        '''槽函数，User Message 输入。'''
        if self._event_loop and self._event_loop.is_running():
            callbacks = {
                'on_ai_message_chunk': self._create_signal_emit_callback(self.ai_message_chunk),
                'on_ai_message_chunk_finish': self._create_signal_emit_callback(self.ai_message_chunk_finish),
                'on_graph_state_update': self._create_signal_emit_callback(self.graph_state_update),
            }
            asyncio.run_coroutine_threadsafe(self._agent.user_message_input(input, callbacks), self._event_loop)

    # ---------- 对话历史 ----------
    @Slot()
    def new_chat(self):
        '''槽函数，新建对话。'''
        logger.debug('<new_chat> 新建对话')
        self._agent.current_thread_id = str(uuid.uuid4())
        self.load_chat_signal.emit([])

    @Slot(str)
    def load_chat(self, thread_id):
        '''槽函数，加载对话。'''
        logger.debug('<load_chat> 加载对话')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.load_chat(thread_id), self._event_loop)

    @Slot()
    def update_chat_history_list(self):
        '''槽函数，更新对话历史列表。'''
        logger.debug('<update_histor_list> 更新历史列表')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._agent.update_chat_history_list(), self._event_loop)

    # ---------- 辅助 ----------
    def _create_signal_emit_callback(self, signal: Signal):
        '''创建信号发射回调。'''

        async def signal_emit(*args):
            '''信号发射。'''
            event_loop = asyncio.get_running_loop()
            event_loop.call_soon_threadsafe(signal.emit, *args)

        return signal_emit

    # ---------- 监听与广播 ----------
    def occur_error_monitor(self, occur_error: str):
        '''报错监听。'''
        self.occur_error.emit(occur_error)

    def graph_ready_monitor(self):
        '''图准备监听'''
        self.graph_ready.emit()

    def input_ready_monitor(self):
        '''输入准备监听'''
        self.input_ready.emit()

    def input_unready_monitor(self):
        '''输入未准备监听'''
        self.input_unready.emit()

    def load_chat_signal_monitor(self, chat_history: list):
        '''加载对话监听'''
        self.load_chat_signal.emit(chat_history)

    def update_chat_history_list_signal_monitor(self, chat_history_list: list):
        '''跟新对话历史列表监听'''
        self.update_chat_history_list_signal.emit(chat_history_list)
