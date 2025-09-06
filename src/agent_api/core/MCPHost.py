import asyncio
import threading
import traceback
import aiosqlite
import os
import uuid
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages.human import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from langmem import create_memory_store_manager, ReflectionExecutor

from .Config import Config
from .state import State
from .graph.episode_memory import EpisodeMemory
from .tts import GPT_SoVITS_TTS

from ..utils import logger
import logging
logger = logger(is_use_console_handler=True, console_handler_level=logging.DEBUG, is_use_file_handler=True, log_path='MCPHost.log')


class MCPHost(QObject):
    '''MCP 主机，动态服务管理器'''
    occur_error = Signal(str) # 报错
    ai_message_chunk = Signal(str) # AI Message Chunk
    ai_message_chunk_finish = Signal() # AI Message Chunk 结束
    graph_state = Signal(str) # 图状态
    input_ready = Signal() # 输入准备，后端准备就绪
    input_unready = Signal()  # 输入未准备，后端未准备就绪
    graph_ready = Signal() # 图准备，图准备就绪
    load_chat_history = Signal(list) # 加载会话历史
    update_chat_history_list = Signal(list) # 更新会话历史列表
    mcp_host_finish = Signal() # MCP 主机结束信号


    def __init__(self, config: Config):
        super().__init__()
        self._config = config
        self._user_name = self._config.user_name
        self._ai_name = self._config.ai_name


        # --- 事件相关 ---
        self._event_loop = None
        self._asyncio_thread = None


        # --- 状态相关 ---
        self._graph_ready = False
        self._llm_activated = False


        # --- 图相关 ---
        self._graph_builder = None
        self._tool_node = None # 工具调用节点
        self._db_connection = None
        self._async_sqlite_saver = None # 异步 SQLite 文件检查点保存器
        self._episode_memory_manager = None
        self._episode_memory_reflection_executor = None
        self._graph = None
        self._current_thread_id = None
        self._run_config = None


        # --- 会话相关 ---
        self.chat_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    'system',
                    # '主人的名字叫：{user_name} --- 自己的名字叫：{ai_name} --- {incantation} --- 请使用{chat_language}进行对话'
                    '用户的名字叫：{user_name} --- 自己的名字叫：{ai_name} --- {incantation} --- 请使用{chat_language}进行对话'

                ),
                MessagesPlaceholder(variable_name='messages')
            ]
        ) # 会话提示


        # --- LLM 相关 ---
        self._llm = None
        self._llm_with_tools = self._llm
        self._llm_connectors = {
            'ollama': self._connect_ollama_llm,
            'deepseek': self._connect_deepseek_llm
        }
        self._last_llm_platform = 'ollama'
        self._last_llm = 'qwen2.5:3b'


        # --- GPT_SoVITS ---
        self._gpt_sovits = None


        # MCP
        self._multi_server_mcp_client = None
        self._mcp_tools = []


    # --- 启动 ---
    @Slot()
    def start(self):
        '''槽函数，启动 MCP 主机，创建事件循环和任务'''
        logger.debug('start --- 启动 MCP 主机')
        try:
            logger.debug('start --- 创建并设置事件循环')
            self._event_loop = asyncio.new_event_loop()
            self._asyncio_thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._asyncio_thread.start()
            asyncio.run_coroutine_threadsafe(self._init_graph(), self._event_loop) 
            logger.debug('start --- 启动 MCP 主机结束')
        except Exception as e:
            error = traceback.format_exc()
            self.occur_error.emit('start ---\n' + error)
            logger.error('start ---\n' + error)


    def _run_event_loop(self):
        '''运行事件循环'''
        logger.debug('_run_event_loop --- 设置并运行事件循环')
        asyncio.set_event_loop(self._event_loop) # set_event_loop() 指定事件循环为当前线程默认事件循环
        self._event_loop.run_forever()
        # run_forever() 启动事件循环并一直运行，直到被显式停止或程序退出，在 GUI 里，会同时驱动 Qt 事件循环和 asyncio 事件循环


    async def _check_emit(self):
        '''检查和发送 input_ready 信号，防止竞态'''
        logger.debug('_check_emit --- 检查和发送 input_ready 信号，防止竞态')
        if self._llm_activated and self._graph_ready:
            self.input_ready.emit()
            logger.debug('_check_emit --- 检查通过，发送 input_ready 信号')


    async def _init_graph(self):
        '''初始化并编译图'''
        logger.debug('_init_graph --- 初始化并编译图')
        try:
            await self._init_graph_structure(self._mcp_tools)
            logger.debug('_init_graph --- 初始化数据库')
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
            )
            await self._db_connection.commit()
            logger.debug('_init_graph --- 初始化异步 SQLite 文件检查点保存器')
            self._async_sqlite_saver = AsyncSqliteSaver(conn=self._db_connection)
            logger.debug('_init_graph --- 编译图')
            await self._compile_graph()
            logger.debug('_init_graph --- 初始化并编译图结束')
            self.graph_ready.emit()
            self._graph_ready = True
            await self._check_emit()
        except Exception as e:
            error = traceback.format_exc()
            self.occur_error.emit('_init_graph ---\n' + error)
            logger.error('_init_graph ---\n' + error)


    async def _init_graph_structure(self, mcp_tools):
        '''初始图结构'''
        self._graph_builder = StateGraph(State)
        self._tool_node = ToolNode(mcp_tools)
        self._graph_builder.add_node('chat_node', self._chat_node)
        self._graph_builder.add_node('tool_node', self._tool_node)
        self._graph_builder.add_edge(START, 'chat_node')
        self._graph_builder.add_conditional_edges(
            source='chat_node',
            path=tools_condition,
            path_map={
                'tools': 'tool_node',
                '__end__': END
            }
        ) # tools_condition 工具调用条件边
        self._graph_builder.add_edge('tool_node', 'chat_node')


    async def _compile_graph(self):
        '''编译图'''
        if self._async_sqlite_saver:
            logger.debug('_compile_graph --- 编译图')
            self._graph = self._graph_builder.compile(checkpointer=self._async_sqlite_saver)
        else:
            logger.error('_compile_graph --- 异步 SQLite 文件检查点保存器不存在，未编译图！！！')


    async def _chat_node(self, state):
        '''节点，会话'''
        chat_messages = self.chat_prompt.invoke(
            {   
                'user_name': self._user_name,
                'ai_name': self._ai_name,
                'incantation': state['system_prompt'],
                'chat_language': state['chat_language'],
                'messages': state['messages']
            }
        )
        ai_message = None
        async for chunk in self._llm_with_tools.astream(chat_messages):
            chunk_content = chunk.content
            if ai_message is None:
                if chunk_content:
                    self.ai_message_chunk.emit(chunk_content)
                    if self._gpt_sovits:
                        await self._gpt_sovits.put_text(chunk_content) # 这里可能有问题，因为 TTS 没写流式，不一定能成功
                    ai_message = chunk
            else:
                if chunk_content:
                    self.ai_message_chunk.emit(chunk_content)
                    if self._gpt_sovits:
                        await self._gpt_sovits.put_text(chunk_content) # 这里可能有问题，因为 TTS 没写流式，不一定能成功
                    ai_message += chunk
        self.ai_message_chunk_finish.emit()
        return {'messages': [ai_message]}


    # --- 关闭 ---
    @Slot()
    def close(self):
        '''槽函数，关闭 MCP 主机'''
        logger.debug('close --- 关闭 MCP 主机')
        if self._event_loop and self._event_loop.is_running():
            logger.debug('close --- 执行关闭任务')
            self._event_loop.call_soon_threadsafe(self._shutdown_task)
        else:
            logger.warning('close --- 事件循环不存在或未运行！！！')
            self.mcp_host_finish.emit()

    
    def _shutdown_task(self):
        '''清理触发任务'''
        asyncio.create_task(self._shutdown()) # create_task() 将协程包装为任务，立即运行，不阻塞，允许并发


    async def _shutdown(self):
        '''清理触发'''
        logger.debug('_shutdown --- 清理触发')
        try:
            logger.debug('_shutdown --- 开始清理任务')
            await self._clean()
        except Exception as e:
            error = traceback.format_exc()
            self.occur_error.emit('_shutdown --- 清理触发\n' + error)
            logger.debug('_shutdown --- 清理触发\n' + error)
        finally:
            logger.debug('_shutdown --- 停止事件循环')
            self._event_loop.stop()
            self.mcp_host_finish.emit()


    async def _clean(self):
        '''清理任务，在事件循环关闭前，执行所有必要的异步清理操作'''
        logger.debug('_clean --- 清理任务启动')
        await self._activate_gpt_sovits(False)
        await self._activate_mcp_client(False)
        await self._activate_llm('', '')


        if self._db_connection:
            logger.debug('_clean --- 清理图，清理异步 SQLite 文件检查点保存器，关闭并清理数据库')
            self._graph = None
            if self._async_sqlite_saver:
                self._async_sqlite_saver = None
            await self._db_connection.close()
            self._db_connection = None


    # LLM 动态服务
    async def _connect_ollama_llm(self, model, base_url, temperature, num_predict):
        '''连接 Ollama 平台的 LLM'''
        logger.debug('_connect_ollama_llm --- 连接 Ollama 平台的 LLM')
        params = {
            'model': model
        }
        params['base_url'] = base_url if base_url else r'http://localhost:11434'
        if temperature:
            params['temperature'] = temperature
        if num_predict:
            params['num_predict'] = num_predict
        llm = ChatOllama(**params)
        return llm
    async def _connect_deepseek_llm(self, model, api_key, temperature, max_tokens):
        '''连接 DeepSeek 平台的 LLM'''
        logger.debug('_connect_deepseek_llm --- 连接 DeepSeek 平台的 LLM')
        params = {
            'model': model,
        }
        params['api_key'] = api_key if api_key else os.getenv('DEEPSEEK_API_KEY')
        if temperature:
            params['temperature'] = temperature
        if max_tokens:
            params['max_tokens'] = max_tokens
        llm = ChatDeepSeek(**params)
        return llm


    @Slot(str, str)
    def activate_llm(self, platform, model):
        '''槽函数，激活 LLM'''
        logger.debug('activate_llm --- 激活 LLM 槽函数')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._activate_llm(platform, model), self._event_loop)
    async def _activate_llm(self, platform, model):
        '''激活 LLM'''



        if self._episode_memory_manager or self._episode_memory_reflection_executor:
            await self._episode_memory_reflection_executor.shutdown()
            self._episode_memory_manager = None
            self._episode_memory_reflection_executor = None



        # 清理
        if not platform or not model:
            logger.debug('_activate_llm --- 停止和清理 LLM')
            if self._llm_activated:
                self.input_unready.emit()
            self._llm_with_tools = None
            self._llm = None
            self._llm_activated = False
            return
        # 停止
        if self._llm_activated:
            self.input_unready.emit()
        self._llm = None
        self._llm_with_tools = self._llm
        self._llm_activated = False
        # 连接
        logger.debug('_activate_llm --- 连接 LLM')
        try:
            if platform in list(self._llm_connectors.keys()):
                self._llm = await self._llm_connectors[platform](model, None, None, None)
            await self._update_mcp_tools()
            self._llm_activated = True
            await self._check_emit()



            if self._llm:
                self._episodic_memory_manager = create_memory_store_manager(
                    self._llm,
                    schemas=[EpisodeMemory],
                    store=self._async_sqlite_saver,
                    namespace=('episodes', '{thread_id}')
                )
                self._episodic_memory_reflection_executor = ReflectionExecutor(
                    self._episodic_memory_manager
                )



            self._last_llm_platform = platform
            self._last_llm = model
        except Exception as e:
            error = traceback.format_exc()
            self.occur_error.emit('_activate_llm --- 连接 LLM\n' + error)
            logger.debug('_activate_llm --- 连接 LLM\n' + error)


    # MCP 客户端动态服务
    @Slot(bool)
    def activate_mcp_client(self, activation):
        '''槽函数，激活 MCP 客户端'''
        logger.debug('activate_mcp_client --- 激活 MCP 客户端槽函数')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._activate_mcp_client(activation), self._event_loop)
    async def _activate_mcp_client(self, activation):
        '''激活 MCP 客户端'''
        if activation and not self._multi_server_mcp_client:
            logger.debug('连接多服务器 MCP')
            self._multi_server_mcp_client = MultiServerMCPClient(
                {
                    'test': {
                        'transport': 'stdio',
                        'command': 'uv',
                        'args': ['run', r'C:\Users\kongbai\study\project\AgentDevelop\MCPSever\src\mcp_server_app\MCPServer.py'],
                        'cwd': r'C:\Users\kongbai\study\project\AgentDevelop\MCPSever'
                    }
                }
            )
            logger.debug('加载多服务器 MCP 工具')
            self._mcp_tools = await self._multi_server_mcp_client.get_tools()
        elif not activation and self._multi_server_mcp_client:
            logger.debug('_activate_mcp_client --- 激活 MCP 客户端工具')
            self._multi_server_mcp_client = None
            self._mcp_tools = []
        await self._update_mcp_tools()


    # GPT_SoVITS 动态服务
    @Slot(bool)
    def activate_gpt_sovits(self, activation):
        '''槽函数，激活 GPT_SoVITS'''
        logger.debug('activate_gpt_sovits --- 激活 GPT_SoVITS 槽函数')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._activate_gpt_sovits(activation), self._event_loop)
    async def _activate_gpt_sovits(self, activation):
        '''激活 GPT_SoVITS'''
        if activation and not self._gpt_sovits:
            self._gpt_sovits = GPT_SoVITS_TTS(self._config)
            await self._gpt_sovits.start()
        elif not activation and self._gpt_sovits:
            await self._gpt_sovits.stop()
            self._gpt_sovits = None


    # User Message Input 动态服务
    @Slot(str)
    def user_message_input(self, input):
        '''槽函数，User Message 输入'''
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._user_message_input(input), self._event_loop)
    async def _user_message_input(self, input):
        '''User Message 输入，运行图'''
        self._run_config = {
            'configurable': {
                'thread_id': self._current_thread_id
            }
        }
        try:
            state = await self._graph.aget_state(self._run_config)
            is_new_chat = not state.values.get('messages', [])
            messages = state.values.get('messages', []) + [HumanMessage(input)]
            current_state = {
                'messages': messages,
                'system_prompt': self._config.state['system_prompt'],
                'chat_language': self._config.state['chat_language']
            }

            step_message = '--------------------Step--------------------\n'
            async for event in self._graph.astream(current_state, self._run_config):
                for node, node_state in event.items():
                    step_message += f'Node: {node}\n'
                    for i in node_state['messages']:
                        step_message += f"Node_State: {type(i).__name__}({i!r})\n" # ！！！！！！！！！！！！！！！！
                    self.graph_state.emit(step_message)
                    logger.debug(step_message)



            if self._episode_memory_reflection_executor:
                final_state = await self._graph.aget_state(self._run_config)
                final_message = final_state.values.get('messages', [])
                if final_message:
                    delay_seconds = 5 * 60
                    self._episode_memory_reflection_executor.submit(
                        {'messages': final_message},
                        config=self._run_config,
                        key=self._current_thread_id,
                        after_seconds=delay_seconds
                    )



            if is_new_chat:
                time = datetime.now()
                title = input[:20] + '···' if len(input) > 20 else input
                await self._db_connection.execute(
                    'INSERT INTO ChatHistory (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)',
                    (self._current_thread_id, title, time, time)
                )
                await self._db_connection.commit()
                await self._update_history_list()
            else:
                await self._db_connection.execute(
                    'UPDATE ChatHistory SET updated_at = ? WHERE thread_id = ?',
                    (datetime.now(), self._current_thread_id)
                )
                await self._db_connection.commit()
                await self._update_history_list()
        except Exception as e:
            error = traceback.format_exc()
            self.occur_error.emit('User Message 输入槽函数 ---' + error)
            logger.debug('User Message 输入槽函数 ---' + error)


    # --- 更新工具相关 ---
    async def _update_mcp_tools(self):
        '''更新 MCP 工具'''
        if self._multi_server_mcp_client:
            logger.debug('更新 MCP 工具')
            if self._mcp_tools:
                logger.debug('更新 MCP 工具')
                print(self._mcp_tools)
                self._llm_with_tools = self._llm.bind_tools(self._mcp_tools)
            else:
                logger.warning('无 MCP 工具')
                self._llm_with_tools = self._llm
                self._mcp_tools = []
        else:
            logger.warning('无 MCP 工具')
            self._llm_with_tools = self._llm
            self._mcp_tools = []
        await self._init_graph_structure(self._mcp_tools)
        await self._compile_graph()


    @Slot()
    def new_chat(self):
        '''新建会话'''
        logger.debug('new_chat --- 新建会话')
        self._current_thread_id = str(uuid.uuid4())
        self.load_chat_history.emit([])


    @Slot(str)
    def load_chat(self, thread_id):
        '''槽函数，加载会话'''
        logger.debug('load_chat --- 加载会话槽函数')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._load_chat(thread_id), self._event_loop)
    async def _load_chat(self, thread_id):
        '''加载会话'''
        logger.debug('_load_chat --- 加载会话')
        self._current_thread_id = thread_id
        self._run_config = {
            'configurable': {
                'thread_id': self._current_thread_id
            }
        }
        try:
            state = await self._graph.aget_state(self._run_config)
            messages = state.values.get('messages', [])
            history = []
            for m in messages:
                is_user = isinstance(m, HumanMessage)
                history.append(
                    {
                        'text': m.content,
                        'is_user': is_user
                    }
                )
            self.load_chat_history.emit(history)
            self.input_ready.emit()
        except Exception as e:
            error = traceback.format_exc()
            self.occur_error.emit('_load_chat --- 加载会话' + error)
            logger.debug('_load_chat --- 加载会话' + error)


    @Slot()
    def update_history_list(self):
        '''槽函数，更新历史列表'''
        logger.debug('update_histor_list --- 更新历史列表槽函数')
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._update_history_list(), self._event_loop)
    async def _update_history_list(self):
        async with self._db_connection.execute('SELECT thread_id, title, updated_at FROM ChatHistory ORDER BY updated_at DESC') as cursor:
            rows = await cursor.fetchall() # fetchall() 把查询得到的所有剩余行一次性取回来并返回列表，列表里每个元素是一条 row （行）
            history_list = [{'thread_id': row[0], 'title': row[1]} for row in rows]
            self.update_chat_history_list.emit(history_list)