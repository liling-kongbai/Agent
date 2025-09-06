from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from . import (
    IntentClassification,
    IntrospectionClassification,
    MainState,
    ReActState,
    intent_classifier_node,
    introspection_entry_node,
    introspection_node,
    react_graph_adapter_node,
)


async def create_react_graph(chat_node, llm, tools):
    '''创建 ReAct 图。连接：对话节点，工具节点'''
    react_graph_builder = StateGraph(ReActState)

    react_graph_builder.add_node('chat_node', partial(chat_node, llm=llm))  # partial() 固定函数的部分参数，返回偏函数
    tool_node = ToolNode(tools)
    react_graph_builder.add_node('tool_node', tool_node)

    react_graph_builder.add_edge(START, 'chat_node')
    react_graph_builder.add_conditional_edges(
        'chat_node', tools_condition, {'tools': 'tool_node', '__end__': END}
    )  # tools_condition 工具调用条件边
    react_graph_builder.add_edge('tool_node', 'chat_node')

    return react_graph_builder.compile()


async def create_main_graph_builder(llm, chat_node, tools):
    '''创建主图构建器，分层路由结构 + 反思。连接：意图分类节点，ReAct 图适配器节点，反思入口节点'''
    main_graph_builder = StateGraph(MainState)

    real_intent_classifier_node = partial(intent_classifier_node, llm=llm)
    main_graph_builder.add_node(
        'react_graph_adapter_node', partial(react_graph_adapter_node, chat_node=chat_node, llm=llm, tools=tools)
    )
    main_graph_builder.add_node('introspection_entry_node', introspection_entry_node)

    main_graph_builder.add_conditional_edges(
        START, real_intent_classifier_node, {IntentClassification.REACT_GRAPH: 'react_graph_adapter_node'}
    )

    main_graph_builder.add_edge('react_graph_adapter_node', 'introspection_entry_node')

    main_graph_builder.add_conditional_edges(
        introspection_entry_node,
        introspection_node,
        {IntrospectionClassification.RealIntentClassifierNode: 'real_intent_classifier_node', '__end__': END},
    )
    return main_graph_builder


# ！！！！！ 考虑意图分类提示词是否需要更改，是否需要添加错误处理或重新处理的判断，或再次处理的判断
