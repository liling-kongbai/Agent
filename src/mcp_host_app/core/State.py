from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    '''图状态，共享数据结构'''
    # TypedDict 字典类型，定义结构化字典类型
    system_prompt: str # 系统提示词
    chat_language: str # 对话使用语言
    messages: Annotated[list, add_messages] # 上下文
    # Annotated 类型可加元数据类型，在类型注解中添加额外元数据
    # list 列表类型，支持泛型语法，指定变量类型
    # add_messages 追加合并两个消息列表或通过 ID 更新现有消息