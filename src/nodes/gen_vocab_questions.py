# src/nodes/gen_vocab_questions.py
import json
import uuid
import random
from collections import Counter
# (修复) 导入 Dict, Any
from typing import Dict, Any
from llm_client import llm
from prompts import VOCAB_QUESTIONS_PROMPT, JSON_ONLY_SUFFIX
# (需要导入 LessonInput 和 LessonOutput 以便在 state 中访问)
from models import (
    AgentState, VocabPackage, LessonOutput, Question,
    OptionItem, Stimuli, LessonInput
)
from pydantic import ValidationError
import re
from utils.text_utils import clean_word
from config import LISTENING_EXERCISE_TYPES, SKILL_TO_EXERCISE_MAP
from tools.tts import generate_audio_placeholder

# (无需更改) V6/V7 解析器
def parse_llm_json_output(llm_output: str, hsk_level: int) -> list[Question]:
    """
    (V6/V7) 解析器: 解析 LLM 输出的 V6/V7 格式 JSON。
    """
    try:
        if llm_output.strip().startswith("```json"):
            cleaned_output = llm_output.strip()[7:-3].strip()
        else:
            cleaned_output = llm_output

        data = json.loads(cleaned_output)
        questions_data = data.get("questions", [])

        parsed_questions = []
        for item in questions_data:
            # (V6/V7) 使用 Pydantic V6/V7 模型自动验证
            q = Question(
                level=hsk_level,
                type=item.get("type", "UNKNOWN"),
                stimuli=Stimuli.model_validate(item.get("stimuli", {})),
                stem=item.get("stem"),
                stem_en=item.get("stem_en"),
                options=[OptionItem.model_validate(opt) for opt in item.get("options")] if item.get("options") else None,
                answer=item.get("answer")
            )
            parsed_questions.append(q)

        return parsed_questions
    except (json.JSONDecodeError, ValidationError, TypeError, IndexError) as e:
        print(f"  - ERROR: Failed to parse or validate V6 JSON. Error: {e}")
        print(f"  - Raw LLM output was:\n{llm_output}")
        return [] # 返回空列表表示失败
    except Exception as e: # 捕获其他可能的错误
        print(f"  - UNEXPECTED ERROR during parsing V6 JSON. Error: {e}")
        print(f"  - Raw LLM output was:\n{llm_output}")
        return []


# (修复) 返回 dump 后的 dict, 正确处理错误
def gen_vocab_questions(state: AgentState) -> Dict[str, Any]:
    print("---NODE: gen_vocab_questions (V8 Randomizing) ---")
    errors = list(state.errors) # 操作副本
    # state.current_lesson 现在是 LessonInput 对象
    current_lesson: LessonInput = state.current_lesson
    # state.current_output_lesson 现在是 LessonOutput 对象
    # 如果要修改它，请操作副本
    output_lesson = state.current_output_lesson.model_copy(deep=True) if state.current_output_lesson else None
    context_text = state.current_content_text

    # 检查上游节点是否成功传递了数据
    if not current_lesson or not output_lesson or not context_text:
        if not state.errors: # 避免重复添加相似错误
            errors.append("gen_vocab_questions: Missing V7 lesson data in state (likely upstream error).")
        return {"errors": errors}

    # --- 开始逻辑 ---
    hsk_level_int = state.stage2_input.hsk_level
    all_vocab_packages = [] # 将包含 VocabPackage Pydantic 对象
    vocab_list = current_lesson.related_vocabulary # 这是 VocabItem 对象列表

    print(f"  - Generating question packages for {len(vocab_list)} vocabulary items...")

    try:
        for i, vocab_item in enumerate(vocab_list): # vocab_item 是 VocabItem 对象
            original_word = vocab_item.word
            cleaned_word = clean_word(original_word)
            print(f"    - ({i+1}/{len(vocab_list)}) Processing word: '{original_word}'")

            # --- (V8 随机化逻辑 - 无需更改) ---
            specific_exercise_requests = []
            for skill, count in vocab_item.skill_distribution.items():
                if count > 0:
                    available_types = SKILL_TO_EXERCISE_MAP.get(skill)
                    if available_types:
                        chosen_types = random.choices(available_types, k=count)
                        specific_exercise_requests.extend(chosen_types)
                    else:
                        print(f"  - WARNING: Skill '{skill}' for word '{original_word}' has no types in SKILL_TO_EXERCISE_MAP.")

            exercise_counts = Counter(specific_exercise_requests)

            # --- (V7 Prompt 构建逻辑 - 无需更改) ---
            exercise_requests = []
            for ex_type, count in exercise_counts.items():
                if count > 0:
                    exercise_requests.append(f"- 生成 {count} 道 `{ex_type}` 类型的题目")

            if not exercise_requests:
                print(f"      - No exercises requested for this word. Skipping.")
                package = VocabPackage(word_id=str(vocab_item.word_id), word=original_word, questions=[])
                all_vocab_packages.append(package) # 添加空的 VocabPackage 对象
                continue
            exercise_requests_str = "\n".join(exercise_requests)

            # --- (V7 LLM 调用 & 解析 & TTS - 无需更改, 但添加错误检查) ---
            prompt = VOCAB_QUESTIONS_PROMPT.format(
                 word=cleaned_word,
                 passage_text=context_text,
                 exercise_requests_list=exercise_requests_str
            ) + JSON_ONLY_SUFFIX
            questions = [] # 将包含 Question Pydantic 对象
            llm_failed_for_word = False
            for attempt in range(2):
                llm_output = llm(prompt)
                if "API_ERROR" in llm_output:
                     print(f"    - LLM API Error on attempt {attempt+1} for word '{original_word}'. Retrying...")
                     if attempt == 1: # 最后一次尝试失败
                         llm_failed_for_word = True
                         errors.append(f"LLM failed after 2 attempts for {original_word}: {llm_output}")
                         print(f"    - ERROR: LLM failed after 2 attempts for word '{original_word}'.")
                     continue # 重试循环

                parsed_q_list = parse_llm_json_output(llm_output, hsk_level_int)
                if parsed_q_list: # 检查解析是否成功返回列表
                    questions = parsed_q_list
                    llm_failed_for_word = False # 成功了
                    break
                else: # 解析返回了空列表
                    print(f"    - Attempt {attempt + 1} failed parsing LLM output for word '{original_word}'. Retrying...")
                    if attempt == 1: # 最后一次尝试失败
                        llm_failed_for_word = True
                        # 不再添加重复的错误信息，因为 parse_llm_json_output 内部已经打印并添加
                        # errors.append(f"Failed to generate/parse questions for word '{original_word}' after 2 attempts.")
                        # print(f"    - ERROR: Failed to generate/parse questions for word '{original_word}' after 2 attempts.")

            if llm_failed_for_word:
                # 如果这个单词的所有尝试都失败了，创建一个空的包并继续
                 print(f"      - Creating empty package for word '{original_word}' due to generation/parsing failures.")
                 package = VocabPackage(word_id=str(vocab_item.word_id), word=original_word, questions=[])
                 all_vocab_packages.append(package)
                 continue # 处理下一个单词

            # TTS 逻辑无需更改
            for q in questions: # q 是 Question Pydantic 对象
                 if q.type in LISTENING_EXERCISE_TYPES:
                    text_to_synthesize = ""
                    if q.type in ["listen_choice", "listen_tf"]:
                         if q.stimuli and q.stimuli.text: text_to_synthesize = q.stimuli.text
                    elif q.type == "speak_follow":
                         text_to_synthesize = q.stem
                    if text_to_synthesize:
                         q.stimuli.audio_url = generate_audio_placeholder(text_to_synthesize)

            package = VocabPackage(
                word_id=str(vocab_item.word_id),
                word=original_word,
                questions=questions # Question 对象列表
            )
            all_vocab_packages.append(package) # 添加 VocabPackage 对象

        # 更新复制的 Pydantic 对象
        output_lesson.vocab_packages = all_vocab_packages # VocabPackage 对象列表
        print(f"  - Successfully attached VocabPackages to LessonOutput: '{current_lesson.lesson_name}'")

        # (修复) 返回包含 dump 后对象和错误的 dict
        return {
            "current_output_lesson": output_lesson.model_dump(), #
            "errors": errors
        }

    except Exception as e:
        import traceback
        print(f"ERROR in gen_vocab_questions loop: {e}\n{traceback.format_exc()}")
        errors.append(f"gen_vocab_questions: Failed during loop. Error: {e}")
        return {"errors": errors} # 仅返回错误字典