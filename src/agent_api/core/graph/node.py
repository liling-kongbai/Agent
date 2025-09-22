from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .assist.assist import create_intent_classifier_chain, create_introspection_classifier_chain
from .type import IntentClassification, IntrospectionClassification


# ---------- 通用相关 ----------
async def chat_node(state, llm: BaseChatModel) -> dict:
    '''节点，对话。传入 LLM 并定义对话提示模板，整合为链，填充对话提示模板并调用 LLM 给出回复，返回 AIMessage 或 ToolMessage'''
    chat_prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                'system',
                '{system_prompt}\n用户的名字叫：{user_name}，你的名字叫：{ai_name}\n请使用{chat_language}进行对话！',
            ),
            MessagesPlaceholder(variable_name='messages'),
        ]
    )  # 对话提示模板
    chain = chat_prompt_template | llm
    response = await chain.ainvoke(
        {
            'system_prompt': state.system_prompt,
            'user_name': state.user_name,
            'ai_name': state.ai_name,
            'chat_language': state.chat_language,
            'messages': state.messages,
        }
    )
    return {'messages': response}


# ---------- 主图相关 ----------
async def intent_classifier_entry_node(state) -> dict:
    '''节点，意图分类器入口，意图路由器入口。'''
    return {}


async def intent_classifier_node(state, llm: BaseChatModel) -> IntentClassification:
    '''伪节点，意图分类器，意图路由器。传入 LLM，创建意图分类链，填充 messages，返回意图类别'''
    try:
        chain = await create_intent_classifier_chain(llm)
        classification = await chain.ainvoke({'messages': state.messages})
        return classification.intent
    except:
        return IntentClassification.ReactGraphAdapterNode


async def react_graph_adapter_node(state, react_graph) -> dict:
    '''节点，ReAct 图适配器。从主图状态适配 ReAct 图状态，运行 ReAct 图得到回复，返回到回复草稿'''
    # ！！！！！是否需要确保每次调用 ReAct 之前，显示设置图状态各项均为空，然后传入新的状态
    react_state = await react_graph.ainvoke(
        {
            'system_prompt': state.system_prompt,
            'user_name': state.user_name,
            'ai_name': state.ai_name,
            'chat_language': state.chat_language,
            'messages': state.messages,
        }
    )
    return {'response_draft': react_state.get('messages')[-1]}  # ！！！！！为什么使用的是 get


async def introspection_classifier_entry_node(state) -> dict:
    '''空节点，反思分类器入口，反思路由器入口。'''
    return {}


async def introspection_node(state, llm: BaseChatModel) -> IntrospectionClassification:
    '''伪节点，反思分类器，反思路由器。传入 LLM，创建反思链，填充 messages 和 response_draft，返回反思类别'''
    try:
        chain = await create_introspection_classifier_chain(llm)
        classification = await chain.ainvoke({'messages': state.messages, 'response_draft': state.response_draft})
        return classification.introspection
    except:
        return IntrospectionClassification.AddFinalResponseNode


async def add_final_response_node(state) -> dict:
    '''节点，添加最终回复。将回复草稿中的内容添加到 messages 中'''
    final_response = state.response_draft
    return {'messages': [final_response]}  # ！！！！！是否需要设为 None


# ！！！！！四种记忆相关的功能需要考虑是否能够分离为节点，需要严格讨论
