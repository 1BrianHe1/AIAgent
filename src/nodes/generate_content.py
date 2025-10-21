# src/nodes/generate_content.py
import json
# (修复) 导入 Dict, Any
from typing import Dict, Any
from src.llm_client import llm
from src.prompts import PASSAGE_PROMPT, DIALOGUE_PROMPT
# (需要导入 LessonInput 以便在 state 中访问)
from models import AgentState, LessonOutput, PassageOutput, DialogueLine, Role, LessonInput
from src.utils.text_utils import clean_word
from pydantic import ValidationError

def estimate_chars(minutes: int) -> tuple[int, int]:
    minutes = max(1, minutes)
    base_chars = minutes * 120
    min_chars = int(base_chars * 0.7)
    max_chars = int(base_chars * 1.3)
    return max(100, min_chars), min(800, max_chars)

# (修复) 返回 dump 后的 dict, 正确处理错误
def generate_content(state: AgentState) -> Dict[str, Any]:
    print("---NODE: generate_content ---")
    errors = list(state.errors) # 操作副本
    # state.current_lesson 现在是 LessonInput 对象
    current_lesson: LessonInput = state.current_lesson
    if not current_lesson:
        errors.append("generate_content: No current_lesson in state.")
        return {"errors": errors}

    # --- 开始逻辑 ---
    hsk_level = state.stage2_input.hsk_level
    content_type = current_lesson.type
    roles = current_lesson.roles

    reading_minutes = current_lesson.skill_distribution.get("reading", 0)
    if reading_minutes <= 0: reading_minutes = current_lesson.duration / 2
    cmin, cmax = estimate_chars(reading_minutes)

    cleaned_vocab_list = [clean_word(v.word) for v in current_lesson.related_vocabulary]
    vocab_list_str = "、".join(cleaned_vocab_list)

    # 在本地初始化 LessonOutput Pydantic 对象
    output_lesson = LessonOutput(
        lesson_id=str(current_lesson.lesson_id),
        lesson_name=current_lesson.lesson_name,
        type=current_lesson.type
    )
    generated_text_for_context = ""

    try:
        if content_type == "dialogue" and roles:
            print(f"  - Generating: DIALOGUE (JSON)")
            roles_str = " 和 ".join([role.roleName for role in roles])
            prompt = DIALOGUE_PROMPT.format(
                hsk_level=hsk_level,
                lesson_name=current_lesson.lesson_name,
                lesson_desc=current_lesson.description,
                roles_str=roles_str,
                vocab_list=vocab_list_str
                # 注意：如果 DIALOGUE_PROMPT 需要 cmin/cmax，请在这里添加
            )
            llm_output = llm(prompt)
            # 在尝试解析 JSON 之前检查 API 错误
            if "API_ERROR" in llm_output:
                 raise Exception(f"LLM API Error: {llm_output}")
            dialogue_data = json.loads(llm_output)
            # 更新本地 Pydantic 对象
            output_lesson.roles = roles
            output_lesson.dialogues = [DialogueLine.model_validate(line) for line in dialogue_data]
            generated_text_for_context = "\n".join([line.text for line in output_lesson.dialogues if line.text]) # 添加 if line.text 健壮性
        else:
            print(f"  - Generating: PASSAGE (JSON)")
            prompt = PASSAGE_PROMPT.format(
                hsk_level=hsk_level,
                lesson_name=current_lesson.lesson_name,
                lesson_desc=current_lesson.description,
                vocab_list=vocab_list_str,
                chars_min=cmin,
                chars_max=cmax
            )
            llm_output = llm(prompt)
            # 在尝试解析 JSON 之前检查 API 错误
            if "API_ERROR" in llm_output:
                 raise Exception(f"LLM API Error: {llm_output}")
            passage_data = json.loads(llm_output)
            # 更新本地 Pydantic 对象
            output_lesson.passage = PassageOutput.model_validate(passage_data)
            generated_text_for_context = output_lesson.passage.text if output_lesson.passage else "" # 添加 if 健壮性

    except (json.JSONDecodeError, ValidationError) as e:
        import traceback
        print(f"ERROR in generate_content: {e}\n{traceback.format_exc()}")
        errors.append(f"generate_content: Failed to parse LLM JSON. Error: {e}")
        return {"errors": errors} # 仅返回错误字典
    except Exception as e: # 捕获 LLM 调用或其他意外错误
        import traceback
        print(f"ERROR in generate_content (other): {e}\n{traceback.format_exc()}")
        errors.append(f"generate_content: Unexpected error. Error: {e}")
        return {"errors": errors}

    # (修复) 返回包含 dump 后对象和字符串的 dict
    return {
        "current_output_lesson": output_lesson.model_dump(), #
        "current_content_text": generated_text_for_context,
        "errors": errors # 返回当前错误列表
    }