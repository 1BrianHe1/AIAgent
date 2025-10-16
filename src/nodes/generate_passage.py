# src/app/nodes/generate_passage.py

from src.llm_client import llm
from src.prompts import PASSAGE_PROMPT
from src.models import AgentState, Passage

def estimate_chars(minutes: int) -> tuple[int, int]:
    """
    根据分钟数估算文章的目标字数范围。
    """
    # 保证至少有1分钟的阅读量
    minutes = max(1, minutes) 
    base_chars = minutes * 120
    min_chars = int(base_chars * 0.7)
    max_chars = int(base_chars * 1.3)
    return max(100, min_chars), min(800, max_chars)


def generate_passage(state: AgentState) -> AgentState:
    """
    LangGraph 节点：为当前课程单元生成一篇学习文章。
    """
    print("---NODE: generate_passage ---")
    
    current_lesson = state.current_lesson
    if not current_lesson:
        state.errors.append("generate_passage: No current_lesson in state.")
        return state

    hsk_level = state.stage2_input.hsk_level
    
    # 修改点：优先使用 skill_distribution 中的 reading 时间，
    # 如果没有或为0，则使用总 duration 的一半作为备用估算值。
    reading_minutes = current_lesson.skill_distribution.get("reading", 0)
    if not reading_minutes:
        # 如果 reading 时间为0或未提供，则使用总时长的一半作为估算
        reading_minutes = current_lesson.duration / 2
        
    cmin, cmax = estimate_chars(reading_minutes)
    
    vocab_list_str = "、".join([v.word for v in current_lesson.related_vocabulary])

    prompt = PASSAGE_PROMPT.format(
        # hsk_level 是整数，但 .format() 会自动将其转为字符串
        hsk_level=hsk_level, 
        lesson_name=current_lesson.lesson_name,
        lesson_desc=current_lesson.description,
        vocab_list=vocab_list_str,
        chars_min=cmin,
        chars_max=cmax
    )
    
    generated_text = llm(prompt)
    
    covered_words = [
        v.word for v in current_lesson.related_vocabulary if v.word in generated_text
    ]
    print(f"  - Vocab coverage: {len(covered_words)}/{len(current_lesson.related_vocabulary)}")

    passage = Passage(
        lesson_id=str(current_lesson.lesson_id),
        text=generated_text,
        tokens_est=len(generated_text),
        covered_words=covered_words
    )

    state.current_passage = passage
    
    return state