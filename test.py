import atexit

from langchain_core.runnables.config import RunnableConfig
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.func import entrypoint
from langgraph.store.postgres import PostgresStore
from langgraph.store.postgres.base import PostgresIndexConfig
from langmem import create_memory_store_manager
from psycopg import Connection
from psycopg_pool import ConnectionPool

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
# ---------- 构建数据库连接池 ----------
postgres_connection_pool = ConnectionPool(postgres_connection_string, min_size=1, max_size=2)
# ---------- 构建数据库 ----------
postgres_store = PostgresStore(postgres_connection_pool, index=postgres_index_config)


# ---------- 构建记忆仓库管理员 ----------
llm = ChatOllama(model='qwen2.5:7b')
manager = create_memory_store_manager(llm, schemas=[EpisodeMemory], store=postgres_store)


# ---------- 测试信息 ----------
langgraph_user_id = 'user_test'
runnable_config = RunnableConfig(configurable={'langgraph_user_id': langgraph_user_id})  # Runnable 配置

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
print('---------- 打印测试 111 ----------')
manager.invoke({'messages': old_messages}, config=runnable_config)
print('---------- 打印测试 111 ----------')


# ---------- ---------- ----------


@entrypoint()
def agent(messages):
    print('---------- 打印测试 222 ----------')
    similar_memory = postgres_store.search(('memories', langgraph_user_id), query=messages[-1]['content'], limit=1)
    print('---------- 打印测试 222 ----------')
    system_message = '你是一位乐于助人的助手。'
    if similar_memory:
        system_message += '\n\n### 情景记忆'
        for i, item in enumerate(similar_memory, start=1):
            print('---------- item ----------')
            print(item)
            print('---------- item.value ----------')
            print(item.value)
            print('---------- 分割 ----------')
            episode_similar_memory = item.value['content']
            system_message += f'''
            经历 {i}：
            情景：{episode_similar_memory['observation']}
            思考：{episode_similar_memory['thought']}
            行动：{episode_similar_memory['action']}
            结果：{episode_similar_memory['result']}
            '''

    response = llm.invoke([{'role': 'system', 'content': system_message}, *messages])
    print('---------- response ----------')
    print(response)
    print('---------- response ----------')
    print('---------- 打印测试 333 ----------')
    manager.invoke({'messages': messages + [response]}, config=runnable_config)
    print('---------- 打印测试 333 ----------')
    return response


# ---------- 测试 ----------
print('---------- 打印测试 444 ----------')
agent.invoke([{'role': 'user', 'content': '什么是二叉树？我平时会翻看家谱，这能帮到我吗？'}], config=runnable_config)
print('---------- 打印测试 444 ----------')

# ---------- 搜索测试 ----------
print('---------- 打印测试 555 ----------')
print('---------- 搜索测试 ----------')
print(postgres_store.search(('memories', langgraph_user_id), query='tree'))
print('---------- 搜索测试 ----------')
print('---------- 打印测试 555 ----------')


@atexit.register  # 注册退出登记函数，确保函数在 Python 解释器正常终止时被自动，无参数地调用
def close_postgres_connection_pool():
    postgres_connection_pool.close()  # close() 安全地关闭所有数据库连接并清理资源，确保程序干净退出
