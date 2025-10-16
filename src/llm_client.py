# src/app/llm_client.py

import os
from http import HTTPStatus
from dotenv import load_dotenv
import dashscope

load_dotenv()


def llm(prompt: str, system: str | None = None) -> str:
    """
    调用通义千问（DashScope）大模型生成回复的统一函数。
    从 .env 中读取：
      - DASHSCOPE_API_KEY
      - MODEL_NAME (如 qwen-plus 或 qwen2.5-7b-instruct)
      - TEMP, MAX_TOKENS（可选）
    """

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("❌ 缺少 DASHSCOPE_API_KEY，请在 .env 文件中设置。")

    model = os.getenv("MODEL_NAME")
    if not model:
        raise ValueError("❌ 缺少 MODEL_NAME，请在 .env 文件中指定，例如 MODEL_NAME=qwen-plus")

    temperature = float(os.getenv("TEMP", "0.5"))
    max_tokens = int(os.getenv("MAX_TOKENS", "2048"))

    dashscope.api_key = api_key

    # =============== 构建消息 ===============
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # =============== 调用模型 ===============
    try:
        response = dashscope.Generation.call(
            model=model,
            messages=messages,
            result_format="message",   # 保证输出格式兼容 OpenAI
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # =============== 解析返回 ===============
        if response.status_code == HTTPStatus.OK:
            # 兼容两种返回结构（对象或字典）
            output = getattr(response, "output", None) or response.get("output", {})
            choices = getattr(output, "choices", None) or output.get("choices", [])
            if not choices:
                return "API_ERROR: empty choices"

            msg = getattr(choices[0], "message", None) or choices[0].get("message", {})
            content = getattr(msg, "content", None) or msg.get("content", "")
            return content.strip()

        else:
            code = getattr(response, "code", None) or response.get("code", "")
            message = getattr(response, "message", None) or response.get("message", "")
            return f"API_ERROR: DashScope {code} - {message}"

    except Exception as e:
        return f"API_ERROR: {e}"
