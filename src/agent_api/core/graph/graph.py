from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .node import (
    add_final_response_node,
    intent_classifier_entry_node,
    intent_classifier_node,
    introspection_classifier_entry_node,
    introspection_node,
    react_graph_adapter_node,
)
from .state import MainState, ReActState
from .type import IntentClassification, IntrospectionClassification


async def create_react_graph(chat_node, llm, tools):
    '''图，创建 ReAct 图。结构：ReAct结构。连接：对话，工具'''
    react_graph_builder = StateGraph(ReActState)
    react_graph_builder.add_node('chat_node', partial(chat_node, llm=llm))  # partial() 固定函数的部分参数，返回偏函数
    tool_node = ToolNode(tools)  # ！！！！！需要考虑 tools 为空的情况，可能需要写一个判断或分支路线
    react_graph_builder.add_node('tool_node', tool_node)

    react_graph_builder.add_edge(START, 'chat_node')
    react_graph_builder.add_conditional_edges(
        'chat_node', tools_condition, {'tools': 'tool_node', '__end__': END}
    )  # tools_condition 工具调用条件
    react_graph_builder.add_edge('tool_node', 'chat_node')
    return react_graph_builder.compile()


async def create_main_graph_builder(chat_node, llm, tools):
    '''图，创建主图构建器。结构：意图分类路由 + 反思路由。连接：意图分类器入口，ReAct 图适配器，反思分类器入口，添加最终回复'''
    main_graph_builder = StateGraph(MainState)
    main_graph_builder.add_node('intent_classifier_entry_node', intent_classifier_entry_node)
    main_graph_builder.add_node(
        'react_graph_adapter_node',
        partial(react_graph_adapter_node, react_graph=await create_react_graph(chat_node, llm, tools)),
    )
    main_graph_builder.add_node('introspection_classifier_entry_node', introspection_classifier_entry_node)
    main_graph_builder.add_node('add_final_response_node', add_final_response_node)

    main_graph_builder.add_edge(START, 'intent_classifier_entry_node')
    main_graph_builder.add_conditional_edges(
        'intent_classifier_entry_node',
        partial(intent_classifier_node, llm=llm),
        {IntentClassification.ReactGraphAdapterNode: 'react_graph_adapter_node'},
    )
    main_graph_builder.add_edge('react_graph_adapter_node', 'introspection_classifier_entry_node')
    main_graph_builder.add_conditional_edges(
        'introspection_classifier_entry_node',
        partial(introspection_node, llm=llm),
        {
            IntrospectionClassification.IntentClassifierEntryNode: 'intent_classifier_entry_node',
            IntrospectionClassification.AddFinalResponseNode: 'add_final_response_node',
        },
    )
    main_graph_builder.add_edge('add_final_response_node', END)
    return main_graph_builder


# ！！！！！考虑意图分类提示词是否需要更改，是否需要添加错误处理或重新处理的判断，或再次处理的判断
# ！！！！！如果有多个分支，当反思认为草稿无法完成任务时，然后转移到意图分类，那么此时，草稿中的内容应该清空还是传递给意图分类的子图
