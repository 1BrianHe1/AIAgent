# test_api.py

import os
from dotenv import load_dotenv
import dashscope

print("--- Starting API Test ---")
load_dotenv() # 加载 .env 文件

api_key = os.getenv("DASHSCOPE_API_KEY")
model_name = os.getenv("MODEL_NAME")

if not api_key:
    print("❌ ERROR: DASHSCOPE_API_KEY not found in .env file.")
    exit()
if not model_name:
    print("❌ ERROR: MODEL_NAME not found in .env file.")
    exit()

print(f"  - API Key found: ...{api_key[-4:]}") # 打印部分key以确认加载
print(f"  - Model to be used: {model_name}")

dashscope.api_key = api_key
messages = [{'role': 'user', 'content': '你好'}]

try:
    print("  - Calling DashScope API...")
    response = dashscope.Generation.call(
        model=model_name,
        messages=messages,
        result_format='message'
    )
    print("--- API Response Received ---")
    # 打印完整的原始返回对象，这包含了所有诊断信息
    print(response)

except Exception as e:
    print("--- An Exception Occurred ---")
    print(f"Exception details: {e}")

print("--- Test Finished ---")