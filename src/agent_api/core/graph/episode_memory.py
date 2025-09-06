from pydantic import BaseModel, Field


class EpisodeMemory(
    BaseModel
):  # BaseModel 数据模型基类，把外部原始数据通过类型注解，校验，生成强类型对象，并可序列化回去
    '''
    情景记忆。
    以身处对话中的智能体的视角，撰写这段对话为情景记忆，利用后见之明来记录这段优秀的对话，以便之后进行回忆和学习。
    分析并保存：对话的情况，智能体的思维过程，智能体的行动，对话的结果和这段情景记忆为什么优秀的分析总结。
    '''

    observation: str = Field(
        ..., description='对话上下文，即当时对话的情况，发生了什么，进行了怎样的对话？'
    )  # Field() 给模型字段外加规则
    thought: str = Field(..., description='智能体在对话情景中，达成目标的内部推理过程与观察，即我（智能体）怎么想的？')
    action: str = Field(
        ...,
        description='智能体做了什么，如何做的，以及以何种方式。包括任何对行动成功至关重要的信息，即我（智能体）怎么做的？',
    )
    result: str = Field(
        ...,
        description='结果与复盘，哪些方面做得好？下次在哪些方面可以做得更好？即我（智能体）对此此情景进行思考和总结。',
    )
