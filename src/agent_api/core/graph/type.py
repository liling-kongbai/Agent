from enum import Enum

from pydantic import BaseModel


class IntentClassification(str, Enum):
    '''枚举，意图类别，意图路由表'''

    REACT_GRAPH = 'react_graph'


class Intent(BaseModel):
    '''数据模型，意图'''

    intent: IntentClassification


class IntrospectionClassification(str, Enum):
    '''枚举，反思类别'''

    IntentClassifierEntryNode = 'intent_classifier_entry_node'
    AddFinalResponseNode = 'add_final_response_node'


class Introspection(BaseModel):
    '''数据模型，反思'''

    introspection: IntrospectionClassification
