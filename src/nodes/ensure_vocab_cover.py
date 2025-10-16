# src/app/nodes/ensure_vocab_cover.py

from src.llm_client import llm
from src.prompts import FIX_APPEND_PROMPT
from src.models import AgentState

def ensure_vocab_cover(state: AgentState) -> AgentState:
    """
    LangGraph 节点：检查并确保文章覆盖了所有必需的词汇。
    如果词汇没有被完全覆盖，则调用 LLM 进行修复。
    """
    print("---NODE: ensure_vocab_cover ---")

    # 1. 从 state 中获取当前 lesson 和 passage
    current_lesson = state.current_lesson
    passage = state.current_passage

    # 检查前置条件是否满足
    if not current_lesson or not passage:
        state.errors.append("ensure_vocab_cover: Missing lesson or passage in state.")
        return state

    # 2. 找出所有遗漏的词汇
    required_words = {v.word for v in current_lesson.related_vocabulary}
    # 直接在文本中检查，对于多义词或不同形态的词可能不完美，但对初级中文足够
    missing_words = [word for word in required_words if word not in passage.text]

    # 3. 决策：如果没有遗漏的词，直接返回
    if not missing_words:
        print("  - All vocabulary covered. No action needed.")
        return state

    print(f"  - Missing {len(missing_words)} words: {', '.join(missing_words)}")
    print("  - Initiating repair...")

    # 4. 准备修复 prompt
    missing_vocab_list_str = "、".join(missing_words)
    prompt = FIX_APPEND_PROMPT.format(
        text=passage.text,
        missing_vocab_list=missing_vocab_list_str
    )

    # 5. 调用 LLM 进行修复
    fixed_text = llm(prompt)

    # 6. 更新 state 中的 passage 对象
    # 重新检查覆盖情况
    new_covered_words = [
        word for word in required_words if word in fixed_text
    ]
    
    passage.text = fixed_text
    passage.covered_words = new_covered_words
    passage.tokens_est = len(fixed_text)
    
    state.current_passage = passage
    
    final_missing = [word for word in required_words if word not in fixed_text]
    if final_missing:
        print(f"  - WARNING: After repair, {len(final_missing)} words still missing: {', '.join(final_missing)}")
        state.errors.append(f"ensure_vocab_cover: Failed to fix missing words: {', '.join(final_missing)}")
    else:
        print("  - Repair successful. All vocabulary is now covered.")

    return state