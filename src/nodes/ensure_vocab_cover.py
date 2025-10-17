# src/app/nodes/ensure_vocab_cover.py

from src.llm_client import llm
from src.prompts import FIX_APPEND_PROMPT
from src.models import AgentState
from src.utils.text_utils import clean_word
def ensure_vocab_cover(state: AgentState) -> AgentState:
    print("---NODE: ensure_vocab_cover ---")

    #  从 state 中获取当前 lesson 和 passage
    current_lesson = state.current_lesson
    passage = state.current_passage

    if not current_lesson or not passage:
        state.errors.append("ensure_vocab_cover: Missing lesson or passage in state.")
        return state

    required_words = {v.word for v in current_lesson.related_vocabulary}
    
    missing_words = [
        word for word in required_words if clean_word(word) not in passage.text
    ]

    if not missing_words:
        print("  - All vocabulary covered. No action needed.")
        return state

    cleaned_missing_words_for_llm = [clean_word(w) for w in missing_words]
    
    print(f"  - Missing {len(missing_words)} words: {', '.join(missing_words)}")
    print(f"  - Initiating repair with cleaned words: {', '.join(cleaned_missing_words_for_llm)}...")

    missing_vocab_list_str = "、".join(cleaned_missing_words_for_llm)
    prompt = FIX_APPEND_PROMPT.format(
        text=passage.text,
        missing_vocab_list=missing_vocab_list_str
    )

    fixed_text = llm(prompt)

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