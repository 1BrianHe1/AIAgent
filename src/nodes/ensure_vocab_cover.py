# src/nodes/ensure_vocab_cover.py
# (修复) 导入 Dict, Any
from typing import Dict, Any
from src.llm_client import llm
from src.prompts import FIX_APPEND_PROMPT
# (需要导入 LessonInput 以便在 state 中访问)
from models import AgentState, LessonInput
from src.utils.text_utils import clean_word

# (修复) 返回 dict, 正确处理错误
def ensure_vocab_cover(state: AgentState) -> Dict[str, Any]:
    print("---NODE: ensure_vocab_cover ---")
    errors = list(state.errors) # 操作副本
    # state.current_lesson 现在是 LessonInput 对象
    current_lesson: LessonInput = state.current_lesson
    text_content = state.current_content_text

    # 检查 generate_content 是否成功传递了数据
    if not current_lesson or not text_content:
        # 如果上一步失败，这里可能没有数据，直接返回错误，避免进一步处理
        if not state.errors: # 避免重复添加相似错误
             errors.append("ensure_vocab_cover: Missing lesson or text content in state (likely upstream error).")
        return {"errors": errors}

    # --- 开始逻辑 ---
    required_words_set = {v.word for v in current_lesson.related_vocabulary}
    missing_words_obj = [v for v in current_lesson.related_vocabulary if clean_word(v.word) not in text_content]

    if not missing_words_obj:
        print("  - All vocabulary covered. No action needed.")
        return {"errors": errors} # 如果无需更改，则返回当前错误列表

    cleaned_missing_words = [clean_word(v.word) for v in missing_words_obj]
    print(f"  - Missing {len(cleaned_missing_words)} words: {', '.join(cleaned_missing_words)}")

    missing_vocab_list_str = "、".join(cleaned_missing_words)
    prompt = FIX_APPEND_PROMPT.format(text=text_content, missing_vocab_list=missing_vocab_list_str)

    try:
        fixed_text = llm(prompt)
        if "API_ERROR" in fixed_text: # 对 LLM 错误的基本检查
             raise Exception(f"LLM call failed: {fixed_text}")

        # 最终检查
        final_missing = [word for word in cleaned_missing_words if word not in fixed_text]
        if final_missing:
            warning_msg = f"ensure_vocab_cover: Failed to fix missing words: {', '.join(final_missing)}"
            print(f"  - WARNING: {warning_msg}")
            errors.append(warning_msg) # 将警告添加为错误
        else:
            print("  - Repair successful. Context text for downstream nodes is updated.")

        # (修复) 返回包含更新后文本和错误的 dict
        return {
            "current_content_text": fixed_text, # str
            "errors": errors # List[str]
        }
    except Exception as e:
        import traceback
        print(f"ERROR in ensure_vocab_cover LLM call: {e}\n{traceback.format_exc()}")
        errors.append(f"ensure_vocab_cover: LLM call failed. Error: {e}")
        return {"errors": errors} # 仅返回错误字典