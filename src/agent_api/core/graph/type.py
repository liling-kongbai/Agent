from enum import Enum

from pydantic import BaseModel, Field


class IntentClassification(str, Enum):
    '''枚举，意图类别，意图路由表'''

    ReactGraphAdapterNode = 'react_graph_adapter_node'


class Intent(BaseModel):  # BaseModel 数据模型基类，把外部数据通过类型注解，校验，生成强类型对象，并可序列化回去
    '''数据模型，意图'''

    intent: IntentClassification


class IntrospectionClassification(str, Enum):
    '''枚举，反思类别，反思路由表'''

    IntentClassifierEntryNode = 'intent_classifier_entry_node'
    AddFinalResponseNode = 'add_final_response_node'


class Introspection(BaseModel):
    '''数据模型，反思'''

    introspection: IntrospectionClassification


# --------- 记忆相关 ----------
class EpisodeMemory(BaseModel):
    '''
    情景记忆记录。
    以身处对话中的智能体的视角，提取出这段对话中有价值的一部分情节，并撰写这段情节为情景记忆。
    利用事后复盘的优势来记录这段优秀的情节为情节记忆，以便以后读取这段情景记忆进行回忆和学习。
    分析并提取：对话的情景与背景，智能体的思考过程，智能体的行动，对话的结果和这段情景记忆为什么优秀的分析总结。
    '''

    observation: str = Field(
        ..., description='对话的情景与背景，即当时对话的情况，发生了什么，进行了怎样的对话？'
    )  # Field() 给模型字段外加规则
    thought: str = Field(
        ...,
        description='智能体在情景中的内部推理过程与观察，帮助它得出正确行动并获得结果的思考。用“我······”的第一人称撰写',
    )
    action: str = Field(
        ...,
        description='智能体在情景中具体做了什么？如何做的？以何种形式完成的？包括任何对行动成功至关重要的信息和细节。用“我······”的第一人称撰写',
    )
    result: str = Field(
        ..., description='结果与复盘，哪些方面做得好？下次在哪些方面可以做得更好或者改进？用“我······”的第一人称撰写'
    )
