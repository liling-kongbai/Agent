from typing import Annotated

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class MainState(BaseModel):  # BaseModel 继承可创建数据模型
    '''图状态，主图状态，共享数据结构'''

    system_prompt: str  # 系统提示词
    user_name: str  # 用户名
    ai_name: str  # AI 名
    chat_language: str  # 对话语言
    messages: Annotated[list[BaseMessage], add_messages]  # 上下文
    # Annotated 类型可加元数据类型，在类型注解中添加额外元数据
    # list 列表类型，支持泛型语法，指定变量类型
    # add_messages 追加合并两个消息列表或通过 ID 更新现有消息
    response_draft: AIMessage | None  # 回复草稿


class ReActState(BaseModel):
    '''图状态，ReAct 图状态，共享数据结构'''

    system_prompt: str  # 系统提示词
    user_name: str  # 用户名
    ai_name: str  # AI 名
    chat_language: str  # 对话语言
    messages: Annotated[list[BaseMessage], add_messages]  # 上下文
