class Config():
    '''配置'''
    def __init__(self):
        super().__init__()
        self.user_name = '理灵'
        self.ai_name = '洛璃'


        self.system_prompt = ''' '--- 工具使用指南 ---\n'
                    '你可以使用工具来回答问题。如果你决定使用一个工具，你的回应必须 **包含一个JSON代码块**，\n'
                    然后调用工具，给出调用结果'''

        
        
        
        
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