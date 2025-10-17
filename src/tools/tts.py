import hashlib
import time

TTS_BASE_LATENCY_SECONDS = 0.2  # 模拟 API 调用的基础网络延迟
TTS_SECONDS_PER_CHAR = 0.05     # 模拟每生成一个字符的语音所需时间

def generate_audio_placeholder(text: str) -> str:

    simulated_duration = TTS_BASE_LATENCY_SECONDS + (len(text) * TTS_SECONDS_PER_CHAR)
    
    time.sleep(simulated_duration)
    
    timestamp = int(time.time() * 1000)
    hash_object = hashlib.md5(f"{text}{timestamp}".encode())
    unique_id = hash_object.hexdigest()[:8]
    
    return f"audio/{unique_id}.mp3"