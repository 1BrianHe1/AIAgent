# scripts/test_db_save_logic.py
import json
import sys
import os
from pathlib import Path
# (移除) 不再需要 argparse
# import argparse
from typing import Dict, Any

# 确保 src 目录在路径中
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 导入数据库保存函数和模型
from database import (
    save_lesson_output,
    Base,
    TopicDB, GeneratedLessonDB, VocabularyDB, GeneratedVocabPackageDB, GeneratedQuestionDB
)

# --- (核心修改) 在这里配置测试参数 ---
# 指定要测试的输出 JSON 文件路径 (相对于项目根目录)
# 请确保这个文件存在！
TEST_JSON_FILE_PATH = "outputs/output_20251021_093402.json" #

# 指定数据库 Schema 名称
# !!! 请务必将 'your_actual_schema_name' 替换为你的真实 Schema !!!
TARGET_SCHEMA_NAME = "your_actual_schema_name"

# 指定与 TEST_JSON_FILE_PATH 对应的 Topic HSK Level
# (需要根据生成该文件时的输入来确定)
TEST_TOPIC_HSK_LEVEL = 3
# --- 结束配置 ---


# (核心修改) main 函数不再需要参数
def main():
    """
    加载固定的输出 JSON 文件，并使用 save_lesson_output 函数
    将其课程保存到指定 Schema 的数据库中。
    """
    json_file_path = project_root / TEST_JSON_FILE_PATH # 构造完整路径
    schema_name = TARGET_SCHEMA_NAME
    topic_hsk_level_for_test = TEST_TOPIC_HSK_LEVEL

    print(f"--- Testing Database Save Logic (Fixed File) ---")
    print(f"  - Loading output data from: {json_file_path}")
    print(f"  - Using Database Schema: {schema_name}")
    print(f"  - Assuming Topic HSK Level: {topic_hsk_level_for_test}")

    # 1. 加载环境变量和数据库配置 (不变)
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set in .env file.")
        sys.exit(1)

    # 2. 配置 SQLAlchemy 引擎以使用 Schema (不变)
    try:
        engine_test = create_engine(
            DATABASE_URL,
            connect_args={"options": f"-csearch_path={schema_name},public"}
        )
        SessionLocal_test = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
        # 覆盖 database.py 中的全局 SessionLocal (不变)
        import database
        database.SessionLocal = SessionLocal_test
        database.engine = engine_test
        # 测试连接 (不变)
        print("  - Testing database connection...")
        with engine_test.connect() as connection:
            print("  - Database connection successful.")
    except Exception as e:
        print(f"ERROR: Failed to configure database engine for schema '{schema_name}'.")
        print(f"Error details: {e}")
        sys.exit(1)

    # 3. 加载和解析固定的 JSON 文件 (不变)
    try:
        # 使用配置好的路径
        if not json_file_path.is_file():
            print(f"ERROR: Test JSON file not found at '{json_file_path}'.")
            print(f"Please check the TEST_JSON_FILE_PATH setting in this script.")
            sys.exit(1)

        data = json.loads(json_file_path.read_text(encoding="utf-8"))
        topic_name = data.get("topic")
        lessons_data = data.get("lessons")

        if not topic_name or not isinstance(lessons_data, list):
            print("ERROR: Invalid JSON structure in file. Missing 'topic' or 'lessons' list.")
            sys.exit(1)

        print(f"  - Found topic: '{topic_name}' with {len(lessons_data)} lessons.")

    # FileNotFoundError 已在上面处理
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON file '{json_file_path}'. Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred loading the JSON file: {e}")
        sys.exit(1)

    # 4. 迭代并保存 Lessons (不变)
    saved_count = 0
    error_count = 0
    print(f"\n--- Starting to save lessons to database ---")
    for i, lesson_dict in enumerate(lessons_data):
        lesson_name = lesson_dict.get("lesson_name", f"Lesson {i+1}")
        print(f"  - Processing lesson '{lesson_name}'...")
        try:
            # 调用保存函数 (不变)
            save_lesson_output(
                topic_name=topic_name,
                lesson_data=lesson_dict,
                topic_hsk_level=topic_hsk_level_for_test
            )
            saved_count += 1
        except Exception as e:
            error_count += 1
            print(f"  - FAILED to save lesson '{lesson_name}'. Error: {e}")
            import traceback
            traceback.print_exc() # 打印详细错误以供调试

    print("\n--- Database Save Test Complete ---")
    print(f"  - Processed: {len(lessons_data)} lessons")
    print(f"  - Saved/Attempted: {saved_count}")
    print(f"  - Errors encountered: {error_count}")


# (核心修改) __main__ 块不再需要参数解析
if __name__ == "__main__":
    # 直接调用 main 函数
    main()