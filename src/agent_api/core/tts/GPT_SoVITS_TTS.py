import asyncio

import aiohttp
import numpy as np
from sounddevice import OutputStream

from ...utils import create_logger

logger = create_logger(is_use_file_handler=True, log_path='GPT_SoVITS.log')


class GPT_SoVITS_TTS:
    '''GPT_SoVITS 的 TTS 功能代理'''

    def __init__(self, config):
        self.config = config

        self.is_running = False
        self.base_url = f'http://{self.config.host}:{self.config.port}'
        self.params = {
            'text_lang': 'zh',
            'ref_audio_path': self.config.ref_audio_path,
            'prompt_lang': 'zh',
            'prompt_text': self.config.prompt_text,
            'text_split_method': self.config.text_split_method,
            'speed_factor': self.config.speed_factor,
            'streaming_mode': True,
            'sample_steps': self.config.sample_steps,
        }
        self.sample_rate = 48000
        self.channels = 1

        self.byte_buffer = b''  # 缓存不完整的音频数据块
        self.is_skip_header = False  # 标记是否已跳过 WAV 头部

        self.session = None
        self.text_queue = asyncio.Queue()
        # 线程安全的异步队列
        self.audio_chunk_queue = asyncio.Queue()
        self.audio_stream = None
        self.tasks = []

    async def set_model(self):
        '''设置模型'''
        # 设置 GPT 模型，动态加载并切换 GPT 模型
        async with self.session.get(
            f'{self.base_url}/set_gpt_weights', params={'weights_path': self.config.gpt_weights_path}
        ) as response:
            response.raise_for_status()
            # raise_for_status() 检查 HTTP 响应状态码
            logger.info(f'设置 GPT 模型成功: {await response.text()}')
            # text() 读取服务器返回的完整响应正文并尝试解码为字符串

        # 设置 Sovits 模型，动态加载并切换 Sovits 模型
        async with self.session.get(
            f'{self.base_url}/set_sovits_weights', params={'weights_path': self.config.sovits_weights_path}
        ) as response:
            response.raise_for_status()
            logger.info(f'设置 Sovits 模型成功: {await response.text()}')

    async def put_text(self, text):
        '''将文本放入文本队列'''
        await self.text_queue.put(text)

    async def tts_stream_worker(self):
        '''流式 TTS API 工作协程，从文本队列获取任务，调用 TTS API 并将音频块放入音频队列'''
        while self.is_running:
            try:
                text = await self.text_queue.get()

                self.params['text'] = text

                async with self.session.post(f'{self.base_url}/tts', json=self.params) as response:
                    if response.status == 200:
                        async for chunk in response.content.iter_any():
                            # iter_any() 逐块读取 HTTP 响应的内容
                            if chunk:
                                await self.audio_chunk_queue.put(chunk)
                    else:
                        logger.error(f'TTS的API网络请求错误！ (状态码: {response.status} : {await response.text()})')
                self.text_queue.task_done()
            except asyncio.CancelledError:
                break

    async def play_audio_worker(self):
        '''音频播放工作协程，从音频队列获取音频块并播放'''
        while self.is_running:
            try:
                chunk = await self.audio_chunk_queue.get()
                self.byte_buffer += chunk

                # 处理 WAV 文件头部
                if not self.is_skip_header:
                    if len(self.byte_buffer) >= 44:
                        self.byte_buffer = self.byte_buffer[44:]
                        self.is_skip_header = True

                if self.is_skip_header:
                    # 音频数据是 16位 整数，需要按 2 字节倍数处理
                    if len(self.byte_buffer) >= 2:
                        end = len(self.byte_buffer) - (len(self.byte_buffer) % 2)
                        audio_data_to_play = self.byte_buffer[:end]
                        self.byte_buffer = self.byte_buffer[end:]

                        if not self.audio_stream:
                            self.audio_stream = OutputStream(
                                samplerate=self.sample_rate, channels=self.channels, dtype='int16'
                            )
                            # OutputStream() 创建音频输出流，将音频数据发送到音频设备进行播放
                            self.audio_stream.start()

                        audio_data = np.frombuffer(audio_data_to_play, dtype=np.int16)
                        # frombuffer() 从字节缓冲区创建 NumPy 数组
                        await asyncio.to_thread(self.audio_stream.write, audio_data)

                self.audio_chunk_queue.task_done()
            except asyncio.CancelledError:
                break

    async def start(self):
        '''启动 GPT_SoVITS_TTS 代理，连接服务器并启动任务'''
        logger.info('GPT_SoVITS_TTS 正在启动中······')

        self.is_running = True
        self.session = aiohttp.ClientSession()
        # ClientSession() 创建和管理异步 HTTP 会话，允许以异步方式发送 HTTP 请求并处理响应

        await self.set_model()

        self.tasks.append(asyncio.create_task(self.tts_stream_worker()))
        # create_task() 将协程包装成任务并排入事件循环中执行
        self.tasks.append(asyncio.create_task(self.play_audio_worker()))

        logger.info('GPT_SoVITS_TTS 启动成功！')

    async def stop(self):
        '''停止 GPT_SoVITS_TTS 代理，取消任务并清理资源'''
        logger.info('GPT_SoVITS_TTS 正在停止中······')

        self.is_running = False

        for task in self.tasks:
            task.cancel()
            # cancel() 取消正在运行的协程任务
        await asyncio.gather(*self.tasks, return_exceptions=True)
        # gather() 并发运行多个异步任务
        self.tasks.clear()

        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None

        if self.session:
            await self.session.close()
            self.session = None

        logger.info('GPT_SoVITS_TTS 停止成功！')
