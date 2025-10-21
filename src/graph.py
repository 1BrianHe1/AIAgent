# src/graph.py
from langgraph.graph import StateGraph, END
# (修复) 导入 Dict, Any 用于类型提示
from typing import Dict, Any
from models import AgentState, Stage2Input, LessonInput
from nodes.generate_content import generate_content
from nodes.gen_vocab_questions import gen_vocab_questions
from nodes.ensure_vocab_cover import ensure_vocab_cover
from nodes.quality_check import check_questions

# (修复) 返回 dict, 正确处理错误
def node_load_and_prepare(state: AgentState) -> Dict[str, Any]:
    print("---NODE: load_and_prepare ---")
    errors = list(state.errors) # 操作副本
    try:
        stage2_data = Stage2Input.model_validate(state.stage2_input)
        lesson_queue = list(stage2_data.lessons) # Pydantic 对象列表
        print(f"  - Loaded {len(lesson_queue)} lessons into the queue.")
        return {
            "stage2_input": stage2_data, # 返回 Pydantic 对象
            "lesson_queue": lesson_queue, # 返回 Pydantic 对象列表
            "errors": errors # 返回当前错误列表
        }
    except Exception as e:
        import traceback
        print(f"ERROR in load_and_prepare: {e}\n{traceback.format_exc()}")
        errors.append(f"Input validation failed: {e}")
        return {"errors": errors} # 仅返回错误字典

# (修复) 返回包含修改后队列和当前课程的 dict
def node_get_next_lesson(state: AgentState) -> Dict[str, Any]:
    print("---NODE: get_next_lesson ---")
    queue = list(state.lesson_queue) # 创建副本
    errors = list(state.errors)
    if not queue:
        errors.append("Lesson queue empty unexpectedly.")
        print("  - ERROR: Lesson queue empty unexpectedly.")
        return {"errors": errors}

    current_lesson = queue.pop(0) # 从副本中弹出
    print(f"  - Processing lesson: '{current_lesson.lesson_name}'")
    return {
        "current_lesson": current_lesson, # 返回 Pydantic 对象
        "lesson_queue": queue # 返回修改后的 Pydantic 对象列表
    }

# (修复) 返回包含更新后 outputs 和已清理字段的 dict
def node_finalize_lesson(state: AgentState) -> Dict[str, Any]:
    print("---NODE: finalize_lesson ---")
    outputs = list(state.outputs) # 创建副本
    lesson_name = state.current_lesson.lesson_name if state.current_lesson else "UNKNOWN"

    if state.current_output_lesson:
        outputs.append(state.current_output_lesson.model_dump()) # 将 dict 添加到列表
        print(f"  - Lesson '{state.current_output_lesson.lesson_name}' added to final outputs.")
    else:
        print(f"  - WARNING: No output lesson found for '{lesson_name}'.")

    return {
        "outputs": outputs, # 返回修改后的 dict 列表
        "current_lesson": None,
        "current_output_lesson": None,
        "current_content_text": ""
    }

# (无需更改) 路由函数是正确的
def router_should_continue(state: AgentState) -> str:
    print("---ROUTER: should_continue ---")
    if state.errors:
        print("  - Errors detected. Ending graph execution.")
        return "end"
    if state.lesson_queue:
        print(f"  - {len(state.lesson_queue)} lessons remaining. Continuing loop.")
        return "get_next_lesson"
    else:
        print("  - Lesson queue is empty. Ending graph execution.")
        return "end"

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("load_and_prepare", node_load_and_prepare)
    graph.add_node("get_next_lesson", node_get_next_lesson)
    graph.add_node("generate_content", generate_content)
    graph.add_node("ensure_vocab_cover", ensure_vocab_cover)
    graph.add_node("gen_vocab_questions", gen_vocab_questions)
    graph.add_node("quality_check", check_questions)
    graph.add_node("finalize_lesson", node_finalize_lesson)

    graph.set_entry_point("load_and_prepare")

    # (无需更改) 这个 lambda 修复是正确的
    graph.add_conditional_edges(
        "load_and_prepare",
        lambda s: "end" if s.errors else "get_next_lesson",
        {"get_next_lesson": "get_next_lesson", "end": END}
    )

    # (无需更改) 主要工作流程的边是正确的
    graph.add_edge("get_next_lesson", "generate_content")
    graph.add_edge("generate_content", "ensure_vocab_cover")
    graph.add_edge("ensure_vocab_cover", "gen_vocab_questions")
    graph.add_edge("gen_vocab_questions", "quality_check")
    graph.add_edge("quality_check", "finalize_lesson")

    # (无需更改) 循环条件边是正确的
    graph.add_conditional_edges(
        "finalize_lesson",
        router_should_continue,
        {"get_next_lesson": "get_next_lesson", "end": END}
    )

    app = graph.compile()
    return app