import traceback
from datetime import datetime

import aiosqlite
from langchain_core.messages.human import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..utils import create_logger

logger = create_logger(is_use_file_handler=True, log_path='agent.log')

from .graph import create_main_graph_builder
from .graph.assist import connect_deepseek_llm, connect_ollama_llm
from .graph.node import chat_node
from .tts import GPT_SoVITS_TTS


class Agent:
    def __init__(self, config):
        super().__init__()
        self._config = config

        # 状态相关
        self._graph_ready = False
        self._llm_activated = False

        self._run_config = None
        self.current_thread_id = None

        # 存储或记忆相关
        self.db_connection = None
        self.async_sqlite_saver = None  # 异步 SQLite 文件检查点保存器

        # self._episode_memory_manager = None
        # self._episode_memory_reflection_executor = None

        # LLM 相关
        self._llm = None
        self._llm_with_tools = self._llm

        self._llm_connectors = {'ollama': connect_ollama_llm, 'deepseek': connect_deepseek_llm}
        self._last_llm_platform = 'ollama'  # 初始默认值为 ollama
        self._last_llm = 'qwen2.5:3b'  # 初始默认值为 qwen2.5:3b

        # MCP 相关
        self._multi_server_mcp_client = None
        self._mcp_tools = []

        # 图相关
        self.graph = None

        # GPT_SoVITS 相关
        self._gpt_sovits = None

        # 监听相关
        self._listeners = []  # 监听者

    # ---------- 初始化 ----------
    async def init_graph(self):
        '''初始化图。'''
        logger.debug('<init_graph> 初始化图')
        try:
            logger.debug('<init_graph> 初始化数据库')
            self.db_connection = await aiosqlite.connect(r'C:\Users\kongbai\study\project\AgentDevelop\memory.db')
            await self.db_connection.execute(
                '''
                    CREATE TABLE IF NOT EXISTS ChatHistory (
                        thread_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                '''
            )  # 创建一个名为 ChatHistory 的表，如果不存在
            await self.db_connection.commit()

            logger.debug('<init_graph> 初始化异步 SQLite 文件检查点保存器')
            self.async_sqlite_saver = AsyncSqliteSaver(conn=self.db_connection)

            logger.debug('<init_graph> 编译图')
            await self._compile_graph()
        except:
            error = traceback.format_exc()
            await self._broadcast('occur_error_monitor', '<init_graph>\n' + error)
            logger.error('<init_graph>\n' + error)

    async def _compile_graph(self):
        '''编译图。'''
        logger.debug('<_compile_graph> 编译图')
        if self.async_sqlite_saver:
            graph_builder = await create_main_graph_builder(self._llm_with_tools, chat_node, self._mcp_tools)
            self._graph = graph_builder.compile(checkpointer=self.async_sqlite_saver)

            self._graph_ready = True
            await self._broadcast('graph_ready_monitor')

            # ！！！！！ 图准备信号好像没有什么用处了？

            await self._input_ready_check()
        else:
            logger.error('<_compile_graph> 异步 SQLite 文件检查点保存器不存在，未编译图！！！')

    # ---------- 关闭 ----------
    async def clean(self):
        '''清理。执行所有必要的异步清理操作'''
        logger.debug('<_clean> 清理')

        if self._gpt_sovits:
            logger.info('<cleanup> [诊断] 准备停止 GPT_SoVITS...')
            await self._gpt_sovits.stop()
            self._gpt_sovits = None
            logger.info('<cleanup> [诊断] GPT_SoVITS 已停止。')

        if self._mcp_tools:
            self._mcp_tools = []
            if self._multi_server_mcp_client:
                logger.info('<cleanup> [诊断] 准备关闭 MCP 客户端...')
                self._multi_server_mcp_client = None
                logger.info('<cleanup> [诊断] MCP 客户端已关闭。')

        if self._llm_activated:
            self._llm_activated = False
            await self._broadcast('input_unready_monitor')

            self._llm_with_tools = None
            self._llm = None

        if self._graph_ready:
            logger.debug('<_clean> 清理图，清理异步 SQLite 文件检查点保存器，关闭并清理数据库')
            if self.async_sqlite_saver:
                self.graph = None
                logger.debug('<cleanup> 清理异步 SQLite 文件检查点保存器')
                self.async_sqlite_saver = None
                if self.db_connection:
                    logger.info('<cleanup> [诊断] 准备关闭数据库连接...')
                    await self.db_connection.close()
                    self.db_connection = None
                    logger.info('<cleanup> [诊断] 数据库连接已关闭。')
        logger.debug('<cleanup> Agent 资源清理完毕')

    # ---------- 激活 LLM ----------
    async def activate_llm(self, platform, model):
        '''激活 LLM。连接 LLM'''
        if self._llm_activated:
            self._llm_activated = False
            await self._broadcast('input_unready_monitor')

        self._llm_with_tools = None
        self._llm = None

        # 清理
        if not platform or not model:
            return

        # 连接
        try:
            if platform in list(self._llm_connectors.keys()):
                self._llm = await self._llm_connectors[platform](model, None, None, None)
                await self._update_tools_bind()

                self._llm_activated = True
                await self._input_ready_check()
                self._last_llm_platform = platform
                self._last_llm = model
        except:
            error = traceback.format_exc()
            await self._broadcast('occur_error_monitor', '<activate_llm>\n' + error)
            logger.debug('<activate_llm>\n' + error)

    # ---------- 激活 MCP 客户端 ----------
    async def activate_mcp_client(self, activation):
        '''激活 MCP 客户端。连接多服务器 MCP 客户端并加载工具'''
        if activation and not self._multi_server_mcp_client:
            logger.debug('<_activate_mcp_client> 激活 MCP 客户端')
            logger.debug('<_activate_mcp_client> 连接多服务器 MCP 客户端')
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
            logger.debug('<_activate_mcp_client> 加载多服务器 MCP 客户端工具')
            self._mcp_tools = await self._multi_server_mcp_client.get_tools()
        elif not activation and self._multi_server_mcp_client:
            logger.debug('<_activate_mcp_client> 关闭 MCP 客户端')
            self._multi_server_mcp_client = None
            self._mcp_tools = []

        await self._update_tools_bind()

    # ---------- 激活 GPT_SoVITS ----------
    async def activate_gpt_sovits(self, activation):
        '''激活 GPT_SoVITS。连接 GPT_SoVITS'''
        if activation and not self._gpt_sovits:
            self._gpt_sovits = GPT_SoVITS_TTS(self._config)
            await self._gpt_sovits.start()
        elif not activation and self._gpt_sovits:
            await self._gpt_sovits.stop()
            self._gpt_sovits = None

    # ！！！！！GPT_SoVITS 没有写流式 TTS，还能改造，还能更快

    # ---------- 运行 ----------
    async def user_message_input(self, input, callbacks):
        '''User Message 输入。User Message 输入，运行图'''
        await self._broadcast('input_unready_monitor')

        self._run_config = {'configurable': {'thread_id': self.current_thread_id}}

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
                'response_draft': None,
            }

            async for event in self._graph.astream(current_state, self._run_config, stream_mode='updates'):
                for node_name, node_output in event.items():
                    if node_name == 'add_final_response_node':
                        final_content = node_output['messages'][0].content
                        await callbacks['on_ai_message_chunk'](final_content)
                        await callbacks['on_ai_message_chunk_finish']()
                    else:
                        node_message = f'-------------------- {node_name} --------------------\n'
                        if node_output is not None:
                            node_message = node_output.get('messages', [])
                            for i in node_output:
                                node_message += f'{type(i).__name__}({i!r})\n'

                            # ！！！！！这句话记得弄懂

                        else:
                            node_message = node_message + '---------- None ----------'
                        await callbacks['on_graph_state_update'](node_message)
                        logger.debug(node_message)

            # 对话历史相关
            if is_new_chat:  # 新对话
                title = input[:20] + '···' if len(input) > 20 else input + '···'
                await self.db_connection.execute(
                    'INSERT INTO ChatHistory (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
                    (self.current_thread_id, title, datetime.now(), datetime.now()),
                )

                # ！！！！！这里注意占位符有些用处，注意学习

                await self.db_connection.commit()
                await self.update_chat_history_list()
            else:  # 旧对话
                await self.db_connection.execute(
                    'UPDATE ChatHistory SET updated_at = ? WHERE thread_id = ?',
                    (datetime.now(), self.current_thread_id),
                )
                await self.db_connection.commit()
                await self.update_chat_history_list()  # ！！！！！这里也是非常的频繁，应该避免

                # ！！！！！如果每一次对话都更新最后修改时间是不是太频繁了，应该可以改成最后一次对话之前更改，比如在新建对话或更换对话之前更改

        except:
            error = traceback.format_exc()
            await self._broadcast('occur_error_monitor', '<user_message_input>\n' + error)
            logger.debug('<user_message_input>\n' + error)
        finally:
            await self._broadcast('input_ready_monitor')

    # ---------- 对话历史 ----------
    async def update_chat_history_list(self):
        '''更新对话历史列表。'''
        async with self.db_connection.execute(
            'SELECT thread_id, title, updated_at FROM ChatHistory ORDER BY updated_at DESC'
        ) as cursor:
            rows = (
                await cursor.fetchall()
            )  # fetchall() 把查询得到的所有剩余行一次性取回来并返回列表，列表里每个元素是一条 row （行
            # 从 ChatHistory 表中取出所有 thread_id，title，updated_at，根据 update_at 按照降序排列
            history_list = [{'thread_id': row[0], 'title': row[1]} for row in rows]
            await self._broadcast('update_chat_history_list_signal_monitor', history_list)

    async def load_chat(self, thread_id):
        '''加载会话'''
        logger.debug('<load_chat> 加载会话')
        self.current_thread_id = thread_id
        self._run_config = {'configurable': {'thread_id': self.current_thread_id}}

        try:
            state = await self._graph.aget_state(self._run_config)
            messages = state.values.get('messages', [])
            history = []

            for m in messages:
                is_user = isinstance(m, HumanMessage)
                history.append({'text': m.content, 'is_user': is_user})

            await self._broadcast('load_chat_signal_monitor', history)
            await self._broadcast('input_ready_monitor')
        except:
            error = traceback.format_exc()
            await self._broadcast('occur_error_monitor', '<load_chat>' + error)
            logger.debug('<load_chat>' + error)

    # ---------- 辅助 ----------
    async def _input_ready_check(self):
        '''输入准备检查。检查图是否准备，LLM 是否激活，并广播输入准备信号'''
        logger.debug('<_input_ready_check> 输入准备检查')
        if self._graph_ready and self._llm_activated:
            await self._broadcast('input_ready_monitor')

    async def _update_tools_bind(self):
        '''更新工具绑定。'''
        if self._multi_server_mcp_client:
            if self._mcp_tools:
                self._llm_with_tools = self._llm.bind_tools(self._mcp_tools)
            else:
                self._llm_with_tools = self._llm
        else:
            self._llm_with_tools = self._llm
        await self._compile_graph()

    # ---------- 监听与广播 ----------
    def add_listener(self, listener):
        '''添加监听者'''
        if listener and listener not in self._listeners:
            self._listeners.append(listener)

    # ！！！！！添加谁进来？还没有添加！

    def remove_listener(self, listener):
        '''移除监听者'''
        if listener and listener in self._listeners:
            self._listeners.remove(listener)

    async def _broadcast(self, signal_name: str, *args, **kwargs):
        '''广播。获取监听者的方法并调用'''
        for listener in self._listeners:
            if hasattr(listener, signal_name):  # hasattr() 判断对象是否包含指定的属性或方法
                method = getattr(listener, signal_name)  # getattr() 动态获取对象的属性或方法，支持默认值
                method(*args, **kwargs)
