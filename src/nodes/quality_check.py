# src/nodes/quality_check.py
import re
# (修复) 导入 Dict, Any
from typing import Dict, Any
from llm_client import llm
# (需要导入 LessonOutput 以便在 state 中访问)
from models import AgentState, Question, LessonOutput, VocabPackage
from prompts import QUALITY_CHECK_PROMPT
from config import ALL_EXERCISE_TYPES
import json
from pydantic import BaseModel, ValidationError
from src.utils.text_utils import clean_word

class QualityCheckResult(BaseModel):
    is_valid: bool
    reason: str

# (修复) 返回 dump 后的 dict, 正确处理错误
def check_questions(state: AgentState) -> Dict[str, Any]:
    print("---NODE: quality_check ---")
    errors = list(state.errors) # 操作副本

    lesson_package = state.current_output_lesson.model_copy(deep=True) if state.current_output_lesson else None

    # 检查上游节点是否成功传递了数据
    if not lesson_package:
        if not state.errors: # 避免重复添加相似错误
            print("  - No current_output_lesson found to check (likely upstream error). Skipping.")
        return {"errors": errors}

    # --- 开始逻辑 ---
    hsk_level_int = state.stage2_input.hsk_level
    total_questions_checked = 0
    failed_questions_count = 0

    try:
        for vocab_pkg in lesson_package.vocab_packages: # vocab_pkg 是 VocabPackage 对象
            valid_questions = [] # 将包含 Question Pydantic 对象
            current_pkg_question_count = len(vocab_pkg.questions)
            total_questions_checked += current_pkg_question_count # 累加检查的总数

            if current_pkg_question_count == 0:
                continue # 如果这个包是空的，跳过

            target_word_original = vocab_pkg.word
            target_word_cleaned = clean_word(target_word_original)

            for q_idx, q in enumerate(vocab_pkg.questions): # q 是 Question 对象
                is_valid_rule = True
                is_valid_llm = True
                q_identifier = f"Word '{target_word_original}' Q_idx {q_idx} (Type: {q.type})" # 用于日志

                # --- (V6/V7 规则检查 - 无需更改) ---
                if q.type not in ALL_EXERCISE_TYPES:
                    print(f"  - FAILED (Rule): Invalid type. {q_identifier}")
                    is_valid_rule = False
                else: # 只有类型有效才检查相关性
                    in_stimuli = q.stimuli and q.stimuli.text and (target_word_original in q.stimuli.text or target_word_cleaned in q.stimuli.text)
                    in_stem = q.stem and (target_word_original in q.stem or target_word_cleaned in q.stem)
                    if not in_stimuli and not in_stem and q.type not in ["write_word", "speak_follow", "translate_c2e", "translate_e2c"]:
                        print(f"  - FAILED (Rule): Target word not in stimuli or stem. {q_identifier}")
                        is_valid_rule = False

                # --- (V6/V7 LLM 检查 - 无需更改, 但添加错误检查) ---
                if is_valid_rule:
                    try:
                        check_prompt = QUALITY_CHECK_PROMPT.format(
                            hsk_level=hsk_level_int,
                            target_word=target_word_cleaned,
                            question_json=q.model_dump_json(indent=2)
                        )
                        judge_output = llm(check_prompt)
                        if "API_ERROR" in judge_output:
                            raise Exception(f"LLM Judge API Error: {judge_output}")

                        # 尝试去除可能的 Markdown 代码块标记
                        if judge_output.strip().startswith("```json"):
                             judge_output = judge_output.strip()[7:-3].strip()
                        elif judge_output.strip().startswith("```"):
                             judge_output = judge_output.strip()[3:-3].strip()

                        result = QualityCheckResult.model_validate_json(judge_output)

                        if not result.is_valid:
                            is_valid_llm = False
                            print(f"  - FAILED (LLM): {q_identifier}. Reason: {result.reason}")

                    except (json.JSONDecodeError, ValidationError) as e:
                        print(f"  - WARNING: LLM-Judge failed to parse result for {q_identifier}. Error: {e}. Output was: {judge_output}")
                        # 默认放行以保证健壮性
                    except Exception as e: # 捕获 API 错误或其他错误
                        print(f"  - WARNING: LLM-Judge call failed for {q_identifier}. Error: {e}")
                        # 默认放行

                if is_valid_rule and is_valid_llm:
                    valid_questions.append(q) 
                else:
                    failed_questions_count += 1
            vocab_pkg.questions = valid_questions 

        print(f"  - Quality check complete. {failed_questions_count}/{total_questions_checked} questions failed and were removed.")

        # (修复) 返回包含 dump 后对象和错误的 dict
        return {
            "current_output_lesson": lesson_package.model_dump(), #
            "errors": errors
        }

    except Exception as e:
        import traceback
        print(f"ERROR in quality_check loop: {e}\n{traceback.format_exc()}")
        errors.append(f"quality_check: Failed during loop. Error: {e}")
        return {"errors": errors} # 仅返回错误字典