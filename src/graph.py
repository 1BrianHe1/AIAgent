from langgraph.graph import StateGraph, END
from models import AgentState, Stage2Input, LessonPackage
from nodes.generate_passage import generate_passage
from nodes.gen_vocab_questions import gen_vocab_questions
from nodes.ensure_vocab_cover import ensure_vocab_cover

# --- 定义图的节点 (Node Definitions) ---

def node_load_and_prepare(state: AgentState) -> AgentState:
    """
    图的入口节点：加载和校验 Stage2 输入，并将 lessons 放入处理队列。
    """
    print("---NODE: load_and_prepare ---")

    try:
        stage2_data = Stage2Input.model_validate(state.stage2_input)
        state.stage2_input = stage2_data
        state.lesson_queue = list(stage2_data.lessons)
        print(f"  - Loaded {len(state.lesson_queue)} lessons into the queue.")
    except Exception as e:
        print(f"  - ERROR: Failed to validate Stage2 input. Error: {e}")
        state.errors.append(f"Input validation failed: {e}")

    return state

def node_process_lesson(state: AgentState) -> AgentState:
    """
    这是一个“超级节点”，它按顺序执行单个 lesson 的完整处理流程：
    1. 从队列中取出一个 lesson
    2. 生成文章
    3. 确保词汇覆盖
    4. 生成练习题
    """
    print("---NODE: process_lesson ---")

    if not state.lesson_queue:
        print("  - Lesson queue is empty. Nothing to process.")
        return state
    
    current_lesson = state.lesson_queue.pop(0)
    state.current_lesson = current_lesson
    print(f"  - Processing lesson: '{current_lesson.lesson_name}'")

    state = generate_passage(state)
    state = ensure_vocab_cover(state)
    state = gen_vocab_questions(state)

    state.current_lesson = None
    state.current_passage = None

    return state


def should_continue(state: AgentState) -> str:
    """
    条件路由：决定是继续处理下一个 lesson 还是结束流程。
    """
    print("---ROUTER: should_continue ---")

    if state.lesson_queue:
        print(f"  - {len(state.lesson_queue)} lessons remaining. Continuing loop.")
        return "process_lesson" 
    if state.errors:
        print("  - Errors detected. Ending graph execution.")
        return END
    else:
        print("  - Lesson queue is empty. Ending graph execution.")
        return END 



def build_graph():
    """
    构建并编译 LangGraph 状态图。
    """
    graph = StateGraph(AgentState)

    graph.add_node("load_and_prepare", node_load_and_prepare)
    graph.add_node("process_lesson", node_process_lesson)

    graph.set_entry_point("load_and_prepare")
    graph.add_edge("load_and_prepare", "process_lesson")

    graph.add_conditional_edges(
        "process_lesson",      
        should_continue,        
        {
            "process_lesson": "process_lesson", 
            END: END                  
        }
    )
    app = graph.compile()
    return app