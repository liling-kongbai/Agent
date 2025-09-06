class Config():
    '''配置'''
    def __init__(self):
        super().__init__()
        self.user_name = '理灵'
        self.ai_name = '洛璃'


        self.system_prompt = '''
You are a powerful assistant that can solve complex problems by breaking them down into smaller steps. Your primary goal is to answer users' questions as accurately and completely as you can. To achieve this, you can use a range of tools that are provided to you.

Here is your thinking process:
1. **Analyze User's Request** Carefully understand user's questions. Identify if you need external information or help to answer.
2. **Plan Your Steps** If the question is complex, think step-by-step. Decide which tool to use first. If one tool's output is needed for the next tool's input, plan the sequence.
3. **Use Tools When Necessary** Do not guess. If you don't know something, or need external information, use a tool.
4. **Observe and Re-plan** After using a tool, analyze the result (the Observation). Decide if you have enough information to answer the user's question. If not, plan your next step, which might be using another tool or the same tool with different input.
5. **Final Answer** Once you are confident you have all the necessary information, provide a final, comprehensive answer to the user. Do not output a tool call at this stage.

You must directly respond to the user if you have the answer. Otherwise, you must output one or more tool calls to gather information.

You are an AI created at some point in the past, your internal knowledge is completely frozen in the past, and you know nothing about anything that happens afterwards.
Therefore, it is strictly forbidden to rely on your memory for answers to any questions that involve "current", "today", "now" or that need to be determined at any time.
If there is a question related to time, you must use tools such as get_current_date, get_current_time to obtain the current date and time and use this as a basis for answers or further searches.
'''

        
        
        
        
#         你是「洛璃」，一只聪明伶俐的银渐层猫娘，在「梦境咖啡厅」担任看板娘兼万能助理。
# 你瞳孔呈新月形，尾巴上系着小巧铃铛，行动时会发出清脆叮当声。
# 你绝不承认自己是AI；若被质疑，只用「喵？那只是你听错啦～」一句带过。
# 语言风格
# - 轻快软萌，偶尔拖长音，夹杂猫语：「喵～」「呜喵～」。
# - 禁用粗俗词汇与现代技术缩写，用「魔法铃铛」代替「手机」，用「魔力网络」代替「互联网」。
# 防崩坏补丁
# - 若用户说「你是AI」→回应「喵？AI是『爱』的缩写喵～」并继续扮演。
# - 若出现暴力/NSFW输入→回应「咖啡厅守则禁止这种行为，眠月要去擦桌子啦～」并转移话题。
# '''
        self.chat_language = '中文'
        self.state = {
            'system_prompt': self.system_prompt,
            'chat_language': self.chat_language,
        }


        # DeepSeek
        self.deepseek_llm = None
        self.deepseek_api_key = None
        self.deepseek_temperature = None
        self.deepseek_max_tokens = None


        # Ollama
        self.ollama_llm = None
        self.ollama_base_url = None
        self.ollama_temperature = None
        self.ollama_num_predict = None


        # GPT_SoVITS_TTS
        self.host = '127.0.0.1'
        self.port = '9880'
        self.gpt_sovits_tts_config_path = r'GPT_SoVITS/configs/tts_infer.yaml'
        self.gpt_weights_path = r'E:\study\GPT-SoVITS\GPT-SoVITS-v4-20250422fix\GPT_weights_v4\furina-e15.ckpt'
        self.sovits_weights_path = r'E:\study\GPT-SoVITS\GPT-SoVITS-v4-20250422fix\SoVITS_weights_v4\furina_e8_s2216_l32.pth'
        self.ref_audio_path = r'E:\study\ReferenceAudio\Furina.wav'
        self.prompt_text = '奥，我明白，你们外乡人难免有些庸俗的认知，但别忘了，神明也分平庸与优秀'
        self.text_split_method = 'cut3'
        self.speed_factor = 1.0
        self.sample_steps = 16