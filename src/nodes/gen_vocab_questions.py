# src/nodes/gen_vocab_questions.py (优化版)

import json
import uuid
from llm_client import llm # 假设你的 import 路径是这样
from prompts import VOCAB_QUESTIONS_PROMPT, JSON_ONLY_SUFFIX
from models import AgentState, VocabPackage, Question, LessonPackage
import re

def _clean_word(word: str) -> str:
    """一个辅助函数，用于清理和提取核心词汇。"""
    match = re.search(r'（(.*?)）|\((.*?)\)', word)
    if match:
        return match.group(1) or match.group(2)
    return re.sub(r'（.*?）|\(.*?\)', '', word).strip()

def parse_llm_json_output(llm_output: str, word: str) -> list[Question]:
    """
    一个健壮的解析器，用于处理 LLM 返回的 JSON 字符串。
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
            q = Question(
                qid=str(uuid.uuid4()),
                type=item.get("type", "UNKNOWN"),
                prompt=item.get("prompt", ""),
                options=item.get("options"),
                answer=item.get("answer"),
                explanation=item.get("explanation"),
                target_word=item.get("target_word", word)
            )
            parsed_questions.append(q)
        return parsed_questions
    except (json.JSONDecodeError, TypeError, IndexError) as e:
        print(f"  - ERROR: Failed to parse JSON for word '{word}'. Error: {e}")
        print(f"  - Raw LLM output was:{llm_output}")
        return []


def gen_vocab_questions(state: AgentState) -> AgentState:
    """
    LangGraph 节点：为当前课程单元中的每个词汇生成练习题包。
    """
    print("---NODE: gen_vocab_questions ---")

    current_lesson = state.current_lesson
    passage = state.current_passage

    if not current_lesson or not passage:
        state.errors.append("gen_vocab_questions: Missing lesson or passage in state.")
        return state

    all_vocab_packages = []
    vocab_list = current_lesson.related_vocabulary
    
    print(f"  - Generating question packages for {len(vocab_list)} vocabulary items...")

    for i, vocab_item in enumerate(vocab_list):
        original_word = vocab_item.word
        # --- 核心修改点 1: 调用 _clean_word ---
        cleaned_word = _clean_word(original_word)
        
        # 优化日志，让我们能看到清理过程
        print(f"    - ({i+1}/{len(vocab_list)}) Processing word: '{original_word}' -> Cleaned: '{cleaned_word}'")
        
        # --- 核心修改点 2: 使用清理后的词构建 prompt ---
        prompt = VOCAB_QUESTIONS_PROMPT.format(
            word=cleaned_word,
            passage_text=passage.text
        ) + JSON_ONLY_SUFFIX

        questions = []
        for attempt in range(2):
            llm_output = llm(prompt)
            # --- 核心修改点 3: 将清理后的词传递给解析器 ---
            questions = parse_llm_json_output(llm_output, cleaned_word)
            
            if questions:
                break
            else:
                print(f"    - Attempt {attempt + 1} failed. Parsing returned no questions. Retrying...")
        
        package = VocabPackage(
            word_id=str(vocab_item.word_id),
            # 我们在最终的包里仍然使用原始的、完整的词
            word=original_word, 
            questions=questions
        )
        all_vocab_packages.append(package)

    lesson_package = LessonPackage(
        lesson_id=str(current_lesson.lesson_id),
        lesson_name=current_lesson.lesson_name,
        passage=passage.model_dump(),
        vocab_packages=all_vocab_packages
    )

    state.outputs.append(lesson_package.model_dump())
    
    print(f"  - Successfully created LessonPackage for lesson: '{current_lesson.lesson_name}'")

    return state