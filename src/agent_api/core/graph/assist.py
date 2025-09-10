import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langchain_core.prompts import ChatMessagePromptTemplate, ChatPromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama

from .type import Intent, IntentClassification, Introspection, IntrospectionClassification


async def create_intent_classifier_chain(llm: BaseChatModel) -> RunnableSequence:
    '''辅助，创建意图分类器链。传入 LLM，创建 Pydantic 输出解析和对话提示模板，引导 LLM 进行意图分类，整合为链并返回'''
    parser = PydanticOutputParser(
        pydantic_object=Intent
    )  # PydanticOutputParser() 将 LLM 的非结构化输出解析为结构化的 Pydantic 对象
    message_prompt_template = ChatMessagePromptTemplate.from_template(
        '''
            <<<{messages}>>>
            分析所有消息，尤其是用户的最新消息，然后将用户接下来的意图分为以下之一：<<<{intent_classification}>>>
            {format_instruction}
        ''',
        partial_variables={
            'intent_classification': ', '.join([e for e in IntentClassification]),
            'format_instruction': parser.get_format_instructions(),
        },
        role='system',
    )  # get_format_instructions() 生成系统提示词，指导 LLM 按照指定的 Pydantic 对象输出 JSON 数据

    # ！！！！！ 注意输出可能是 JSON 数据，可能需要提取为 str

    prompt_template = ChatPromptTemplate.from_messages([message_prompt_template])
    return prompt_template | llm | parser


async def create_introspection_chain(llm: BaseChatModel) -> RunnableSequence:
    '''辅助，创建反思链'''
    parser = PydanticOutputParser(pydantic_object=Introspection)
    message_prompt_template = ChatMessagePromptTemplate.from_template(
        '''
            阅读最新的几条消息，分析用户的意图和要求，结合回复内容，请判断回复内容是否能满足用户的意图和要求，根据情况返回以下选项之一：<<<{introspection_classification}>>>
            如果回复内容能满足用户的意图和要求，请返回<<<{IntrospectionClassification_AddFinalResponseNode}>>>;
            如果回复内容能不能满足用户的意图和要求，请返回<<<{IntrospectionClassification_IntentClassifierEntryNode}>>>;
            {format_instruction}
            消息：<<<{messages}>>>
            回复内容：<<<{response_draft}>>>
        ''',
        partial_variables={
            'introspection_classification': ', '.join([e for e in IntrospectionClassification]),
            'IntrospectionClassification_AddFinalResponseNode': IntrospectionClassification.AddFinalResponseNode,
            'IntrospectionClassification_IntentClassifierEntryNode': IntrospectionClassification.IntentClassifierEntryNode,
            'format_instruction': parser.get_format_instructions(),
        },
        role='system',
    )
    prompt_template = ChatPromptTemplate.from_messages([message_prompt_template])
    return prompt_template | llm | parser


async def connect_ollama_llm(model, base_url, temperature, num_predict):
    '''连接 Ollama 平台的 LLM'''
    params = {'model': model}
    params['base_url'] = base_url if base_url else r'http://localhost:11434'
    if temperature:
        params['temperature'] = temperature
    if num_predict:
        params['num_predict'] = num_predict
    llm = ChatOllama(**params)
    return llm


async def connect_deepseek_llm(model, api_key, temperature, max_tokens):
    '''连接 DeepSeek 平台的 LLM'''
    params = {'model': model}
    params['api_key'] = api_key if api_key else os.getenv('DEEPSEEK_API_KEY')
    if temperature:
        params['temperature'] = temperature
    if max_tokens:
        params['max_tokens'] = max_tokens
    llm = ChatDeepSeek(**params)
    return llm
