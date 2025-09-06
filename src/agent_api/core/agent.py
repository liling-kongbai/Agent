import datetime
import traceback

import aiosqlite
from langchain_core.messages.human import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..utils import logger
from . import chat_node, connect_deepseek_llm, connect_ollama_llm, create_main_graph_builder


class Agent:
    def __init__(self, config):
        super().__init__()
        self._config = config

        # ---------- 状态相关 ----------
        self._graph_ready = False
        self._llm_activated = False

        # ---------- 存储相关 ----------
        self.db_connection = None
        self.async_sqlite_saver = None  # 异步 SQLite 文件检查点保存器

        # ---------- 图结构相关 ----------
        self.graph = None

        # ---------- LLM 相关 ----------
        self._llm = None
        self._llm_with_tools = self._llm

        # ---------- MCP 相关 ----------
        self._multi_server_mcp_client = None
        self._mcp_tools = []

        # ---------- 监听相关 ----------
        self._listeners = []  # 监听者

        # self._episode_memory_manager = None
        # self._episode_memory_reflection_executor = None
        self._run_config = None
        self.current_thread_id = None

        self._llm_connectors = {'ollama': connect_ollama_llm, 'deepseek': connect_deepseek_llm}
        self._last_llm_platform = 'ollama'
        self._last_llm = 'qwen2.5:3b'

        # # --- GPT_SoVITS ---
        # self._gpt_sovits = None

    async def init_graph(self):
        '''初始化图结构'''
        logger.debug('<init_graph> 初始化图结构')
        try:
            logger.debug('<init_graph> 初始化数据库')
            self._db_connection = await aiosqlite.connect(r'C:\Users\kongbai\study\project\AgentDevelop\memory.db')
            await self._db_connection.execute(
                '''
                    CREATE TABLE IF NOT EXISTS ChatHistory (
                        thread_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                '''
            )  # 创建一个名为 ChatHistory 的表，如果不存在
            await self._db_connection.commit()

            logger.debug('<init_graph> 初始化异步 SQLite 文件检查点保存器')
            self._async_sqlite_saver = AsyncSqliteSaver(conn=self._db_connection)

            logger.debug('<init_graph> 编译图')
            await self._compile_graph()
        except:
            error = traceback.format_exc()
            self._broadcast('occur_error_emit', '<init_graph>\n' + error)
            logger.error('<init_graph>\n' + error)

    async def _compile_graph(self):
        '''编译图结构'''
        logger.debug('<_compile_graph> 编译图结构')
        if self._async_sqlite_saver:
            graph_builder = await create_main_graph_builder(self._llm_with_tools, chat_node, self._mcp_tools)
            self._graph = graph_builder.compile(checkpointer=self._async_sqlite_saver)

            self._graph_ready = True
            self._broadcast('graph_ready_emit')
            await self._input_ready_check()
        else:
            logger.error('<_compile_graph> 异步 SQLite 文件检查点保存器不存在，未编译图结构！！！')

    async def _input_ready_check(self):
        '''输入准备检查'''
        logger.debug('<_input_ready_check> 输入准备检查')
        if self._graph_ready and self._llm_activated:
            self._broadcast('input_ready_emit')

    async def activate_llm(self, platform, model):
        '''激活 LLM'''
        if self._llm_activated:
            self._llm_activated = False
            self._broadcast('input_unready_emit')

        self._llm_with_tools = None
        self._llm = None

        # 清理
        if not platform or not model:
            return

        # 连接
        try:
            if platform in list(self._llm_connectors.keys()):
                self._llm = await self._llm_connectors[platform](model, None, None, None)
                await self._update_tools()
                self._llm_activated = True
                await self._input_ready_check()
                self._last_llm_platform = platform
                self._last_llm = model
        except:
            error = traceback.format_exc()
            self._broadcast('activate_llm_emit', error)
            logger.debug('activate_llm --- 激活 LLM\n' + error)

    async def _activate_mcp_client(self, activation):
        '''激活 MCP 客户端'''
        if activation and not self._multi_server_mcp_client:
            logger.debug('连接多服务器 MCP')
            self._multi_server_mcp_client = MultiServerMCPClient(
                {
                    'test': {
                        'transport': 'stdio',
                        'command': 'uv',
                        'args': [
                            'run',
                            r'C:\Users\kongbai\study\project\AgentDevelop\MCPSever\src\mcp_server_app\MCPServer.py',
                        ],
                        'cwd': r'C:\Users\kongbai\study\project\AgentDevelop\MCPSever',
                    }
                }
            )
            logger.debug('加载多服务器 MCP 工具')
            self._mcp_tools = await self._multi_server_mcp_client.get_tools()
        elif not activation and self._multi_server_mcp_client:
            self._multi_server_mcp_client = None
            self._mcp_tools = []
        await self._update_tools()

    async def user_message_input(self, input):
        '''User Message 输入，运行图'''
        self._run_config = {'configurable': {'thread_id': self._current_thread_id}}
        try:
            state = await self._graph.aget_state(self._run_config)
            is_new_chat = not state.values.get('messages', [])
            messages = state.values.get('messages', []) + [HumanMessage(input)]
            current_state = {
                'messages': messages,
                'system_prompt': self._config.state['system_prompt'],
                'user_name': self._config.state['user_name'],
                'ai_name': self._config.state['ai_name'],
                'chat_language': self._config.state['chat_language'],
            }

            step_message = '--------------------Step--------------------\n'
            async for event in self._graph.astream(current_state, self._run_config):
                for node, node_state in event.items():
                    step_message += f'Node: {node}\n'
                    for i in node_state['messages']:
                        step_message += f"Node_State: {type(i).__name__}({i!r})\n"  # ！！！！！！！！！！！！！！！！
                    self.graph_state.emit(step_message)
                    logger.debug(step_message)

            if is_new_chat:
                time = datetime.now()
                title = input[:20] + '···' if len(input) > 20 else input
                await self._db_connection.execute(
                    'INSERT INTO ChatHistory (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
                    (self._current_thread_id, title, time, time),
                )
                await self._db_connection.commit()
                await self._update_history_list()
            else:
                await self._db_connection.execute(
                    'UPDATE ChatHistory SET updated_at = ? WHERE thread_id = ?',
                    (datetime.now(), self._current_thread_id),
                )
                await self._db_connection.commit()
                await self._update_history_list()
        except:
            error = traceback.format_exc()
            self._broadcast('occur_error_emit', error)
            logger.debug('User Message 输入槽函数 ---' + error)

    async def _update_tools(self):
        '''更新工具'''
        if self._multi_server_mcp_client:
            if self._mcp_tools:
                self._llm_with_tools = self._llm.bind_tools(self._mcp_tools)
            else:
                self._llm_with_tools = self._llm
                self._mcp_tools = []
        else:
            self._llm_with_tools = self._llm
            self._mcp_tools = []
        await self._compile_graph(self._llm_with_tools, chat_node, self._mcp_tools)

    async def update_history_list(self):
        async with self._db_connection.execute(
            'SELECT thread_id, title, updated_at FROM ChatHistory ORDER BY updated_at DESC'
        ) as cursor:
            rows = (
                await cursor.fetchall()
            )  # fetchall() 把查询得到的所有剩余行一次性取回来并返回列表，列表里每个元素是一条 row （行）
            history_list = [{'thread_id': row[0], 'title': row[1]} for row in rows]
            self._broadcast('update_history_list_emit', history_list)

    async def add_listener(self, listener):
        '''添加监听者'''
        if listener and listener not in self._listeners:
            self._listeners.append(listener)

    async def remove_listener(self, listener):
        '''移除监听者'''
        if listener and listener in self._listeners:
            self._listeners.remove(listener)

    async def _broadcast(self, signal_name: str, *args, **kwargs):
        '''广播'''
        for listener in self._listeners:
            if hasattr(listener, signal_name):
                method = getattr(listener, signal_name)
                method(*args, **kwargs)

    async def _load_chat(self, thread_id):
        '''加载会话'''
        logger.debug('_load_chat --- 加载会话')
        self._current_thread_id = thread_id
        self._run_config = {'configurable': {'thread_id': self._current_thread_id}}
        try:
            state = await self._graph.aget_state(self._run_config)
            messages = state.values.get('messages', [])
            history = []
            for m in messages:
                is_user = isinstance(m, HumanMessage)
                history.append({'text': m.content, 'is_user': is_user})
            self.load_chat_history.emit(history)
            self.input_ready.emit()
        except Exception as e:
            error = traceback.format_exc()
            self.occur_error.emit('_load_chat --- 加载会话' + error)
            logger.debug('_load_chat --- 加载会话' + error)

    # async def _activate_gpt_sovits(self, activation):
    #     '''激活 GPT_SoVITS'''
    #     if activation and not self._gpt_sovits:
    #         self._gpt_sovits = GPT_SoVITS_TTS(self._config)
    #         await self._gpt_sovits.start()
    #     elif not activation and self._gpt_sovits:
    #         await self._gpt_sovits.stop()
    #         self._gpt_sovits = None
