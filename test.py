import atexit

from langchain_core.runnables.config import RunnableConfig
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.func import entrypoint
from langgraph.store.postgres import PostgresStore
from langgraph.store.postgres.base import PostgresIndexConfig
from langmem import create_memory_store_manager
from psycopg import Connection
from psycopg_pool import ConnectionPool

from src.agent_api.core.graph.assist.reflection_persistence import PersistenceExecutor
from src.agent_api.core.graph.type import EpisodeMemory

# ---------- 数据库配置 ----------
postgres_connection_string = 'postgresql://postgres:root@localhost:5432/test'  # 数据库连接字符串
postgres_index_config: PostgresIndexConfig = {
    'dims': 1024,  # 向量维度，嵌入模型输出向量维度
    'embed': OllamaEmbeddings(model='bge-m3:latest'),  # 嵌入模型
    'fields': [
        'content.observation',
        'content.thought',
        'content.action',
        'content.result',
    ],  # 文本内容提取规则，提取 content 对象下的字段并拼接用于生成向量
    'ann_index_config': {
        'kind': 'hnsw',
        'vector_type': 'vector',
    },  # 近似最近邻索引配置，近似最近邻检索，索引类型，向量类型
    'distance_type': 'cosine',  # 距离类型，距离度量算法，'l2', 'inner_product', 'cosine'
}  # 数据库向量索引配置


# ---------- 初始化数据库 ----------
with Connection.connect(postgres_connection_string, autocommit=True) as connection:
    temporary_store = PostgresStore(connection, index=postgres_index_config)
    temporary_store.setup()

    PersistenceExecutor.setup(connection)
# ---------- 构建数据库连接池 ----------
connection_kwargs = {'autocommit': True}
postgres_connection_pool = ConnectionPool(postgres_connection_string, kwargs=connection_kwargs, min_size=2, max_size=3)
# ---------- 构建数据库 ----------
postgres_store = PostgresStore(postgres_connection_pool, index=postgres_index_config)


# ---------- 构建记忆仓库管理员 ----------
llm = ChatOllama(model='qwen2.5:7b')
manager = create_memory_store_manager(
    llm, schemas=[EpisodeMemory], namespace=('memories', 'user_test'), store=postgres_store
)


# ---------- 构建持久化反思执行器 ----------
executor = PersistenceExecutor(manager, postgres_store)


# ---------- 测试信息 ----------
langgraph_user_id = 'user_test'
runnable_config = RunnableConfig(
    configurable={'langgraph_user_id': langgraph_user_id, 'thread_id': 'duihuaceshi111222333'}
)  # Runnable 配置s

old_messages = [
    {'role': 'user', 'content': '什么是二叉树？我平常做家谱，这能帮到我吗？'},
    {
        'role': 'assistant',
        'content': '二叉树就像家谱，但每位‘父母’最多只能有两个‘孩子’。举个简单例子：\n   鲍勃\n  /  \\\n艾米  卡尔\n\n和家谱一样，我们称鲍勃为‘父节点’，艾米和卡尔为‘子节点’。',
    },
    {'role': 'user', 'content': '哦，明白了！那在二叉搜索树里，是不是就像按年龄给家族排序？'},
    {'role': 'user', 'content': '给我介绍一下LangMem中的记忆方面的知识点吧！'},
    {
        'role': 'assistant',
        'content': '''
        LangMem helps agents learn and adapt from their interactions over time.
        It provides tooling to extract important information from conversations, optimize agent behavior through prompt refinement, and maintain long-term memory.
        It offers both functional primitives you can use with any storage system and native integration with LangGraph's storage layer.
        This lets your agents continuously improve, personalize their responses, and maintain consistent behavior across sessions.
        ''',
    },
]
# print('---------- 打印测试 111 ----------')
# manager.invoke({'messages': old_messages}, config=runnable_config)
# print('---------- 打印测试 111 ----------')


# ---------- ---------- ----------


# @entrypoint()
# def agent(messages):
#     print('---------- 打印测试 222 ----------')
#     similar_memory = postgres_store.search(('memories', langgraph_user_id), query=messages[-1]['content'], limit=1)
#     print('---------- 打印测试 222 ----------')
#     system_message = '你是一位乐于助人的助手。'
#     if similar_memory:
#         system_message += '\n\n### 情景记忆'
#         for i, item in enumerate(similar_memory, start=1):
#             print('---------- item ----------')
#             print(item)
#             print('---------- item.value ----------')
#             print(item.value)
#             print('---------- 分割 ----------')
#             episode_similar_memory = item.value['content']
#             system_message += f'''
#             经历 {i}：
#             情景：{episode_similar_memory['observation']}
#             思考：{episode_similar_memory['thought']}
#             行动：{episode_similar_memory['action']}
#             结果：{episode_similar_memory['result']}
#             '''

#     response = llm.invoke([{'role': 'system', 'content': system_message}, *messages])
#     print('---------- response ----------')
#     print(response)
#     print('---------- response ----------')
#     print('---------- 打印测试 333 ----------')
#     manager.invoke({'messages': messages + [response]}, config=runnable_config)
#     print('---------- 打印测试 333 ----------')
#     return response


# ---------- 测试 1 ----------
# print('---------- 打印测试 444 ----------')
# agent.invoke([{'role': 'user', 'content': '什么是二叉树？我平时会翻看家谱，这能帮到我吗？'}], config=runnable_config)
# print('---------- 打印测试 444 ----------')


# ---------- 测试 2 ----------
new_messages = [
    {'role': 'user', 'content': 'Python的 `requests` 库和 `httpx` 库有什么主要区别？'},
    {
        'role': 'assistant',
        'content': '主要区别在于 `httpx` 支持异步请求（async/await），而 `requests` 只支持同步。这意味着在需要高并发网络请求时，`httpx` 的性能会好得多。同时，`httpx` 也完全兼容 `requests` 的API，迁移起来很方便。',
    },
    {'role': 'user', 'content': '我感觉我现在的项目管理就像在指挥一群猫，完全失控，有什么好办法吗？'},
    {
        'role': 'assistant',
        'content': '“指挥一群猫”这个比喻非常贴切！很多项目初期都会有这种感觉。既然是“指挥猫”，那我们不妨顺着猫的习性来想：\n\n1.  **传统方法（瀑布式）**：就像试图让所有猫排成一条直线，跟着你走到唯一的那个饭盆前。这几乎不可能成功，因为每只猫都有自己的想法，任何一点意外都会让队伍彻底乱掉。\n\n2.  **敏捷方法（Agile）**：更像是你在房间的各个角落放上好几个小饭盆（短期目标/迭代任务）。你不用强迫所有猫都去同一个地方，而是鼓励它们各自找最近的饭盆吃饭。猫（团队成员）有更大的自主权，它们的目标更清晰、也更容易达成。你作为指挥者，只需要确保饭盆被及时填满（分配任务）和清理（验收成果）就行了。\n\n所以，你或许可以试试“敏捷”的管理方式，把那个遥远的大目标，拆分成许多个独立、短期就能看到成果的小任务，让你的“猫咪们”自己选择去完成。',
    },
    {'role': 'user', 'content': '哇！用猫的比喻来解释敏捷开发，我一下子就懂了！这个思路太棒了，谢谢！'},
    {'role': 'assistant', 'content': '不客气！能帮你把复杂的问题变清晰，是我的荣幸。'},
    {'role': 'user', 'content': '再帮我个小忙，帮我想一个关于咖啡的广告语，要听起来很提神。'},
    {'role': 'assistant', 'content': '当然。试试这个怎么样：**“灌注灵感，唤醒每个细胞。”**'},
]

after_seconds = 10
executor.submit({'messages': new_messages}, config=runnable_config, after_seconds=after_seconds)
executor.shutdown()

# ---------- 搜索测试 ----------
# print('---------- 打印测试 555 ----------')
# print('---------- 搜索测试 ----------')
# print(postgres_store.search(('memories', langgraph_user_id), query='tree'))
# print('---------- 搜索测试 ----------')
# print('---------- 打印测试 555 ----------')


@atexit.register  # 注册退出登记函数，确保函数在 Python 解释器正常终止时被自动，无参数地调用
def close_postgres_connection_pool():
    postgres_connection_pool.close()  # close() 安全地关闭所有数据库连接并清理资源，确保程序干净退出
