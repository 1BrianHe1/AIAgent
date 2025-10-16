# src/app/graph.py

from langgraph.graph import StateGraph, END
from models import AgentState, Stage2Input, LessonPackage

# 导入我们之前创建的所有节点函数
# 注意：我们将把三个核心处理步骤包装在一个“超级节点”中，以简化图的结构
from nodes.generate_passage import generate_passage
from nodes.gen_vocab_questions import gen_vocab_questions
from nodes.ensure_vocab_cover import ensure_vocab_cover

# --- 定义图的节点 (Node Definitions) ---

def node_load_and_prepare(state: AgentState) -> AgentState:
    """
    图的入口节点：加载和校验 Stage2 输入，并将 lessons 放入处理队列。
    """
    print("---NODE: load_and_prepare ---")
    
    # 使用 Pydantic 模型进行输入数据的校验
    # 如果 state['stage2_input'] 是一个字典，Pydantic 会自动转换和校验
    try:
        stage2_data = Stage2Input.model_validate(state.stage2_input)
        state.stage2_input = stage2_data
        # 将所有 lessons 放入待处理队列
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

    # 1. 从队列中取出一个 lesson
    if not state.lesson_queue:
        print("  - Lesson queue is empty. Nothing to process.")
        return state
    
    current_lesson = state.lesson_queue.pop(0)
    state.current_lesson = current_lesson
    print(f"  - Processing lesson: '{current_lesson.lesson_name}'")

    # 2. 依次调用核心处理节点逻辑
    # 每个函数都会接收 state 并返回修改后的 state
    state = generate_passage(state)
    state = ensure_vocab_cover(state)
    state = gen_vocab_questions(state)
    
    # 清理当前 lesson 的临时状态，为下一个循环做准备
    state.current_lesson = None
    state.current_passage = None

    return state

# --- 定义图的路由逻辑 (Routing Logic) ---

def should_continue(state: AgentState) -> str:
    """
    条件路由：决定是继续处理下一个 lesson 还是结束流程。
    """
    print("---ROUTER: should_continue ---")

    if state.errors:
        print("  - Errors detected. Ending graph execution.")
        return END

    if state.lesson_queue:
        print(f"  - {len(state.lesson_queue)} lessons remaining. Continuing loop.")
        return "process_lesson" # 返回下一个要跳转的节点名
    else:
        print("  - Lesson queue is empty. Ending graph execution.")
        return END # 返回特殊的 END 字符串，表示流程结束


# --- 构建并编译图 (Graph Assembly) ---

def build_graph():
    """
    构建并编译 LangGraph 状态图。
    """
    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("load_and_prepare", node_load_and_prepare)
    graph.add_node("process_lesson", node_process_lesson)

    # 设置图的入口点
    graph.set_entry_point("load_and_prepare")

    # 添加边
    graph.add_edge("load_and_prepare", "process_lesson")

    # 添加条件边，实现循环
    graph.add_conditional_edges(
        "process_lesson",       # 从这个节点出发
        should_continue,        # 使用这个函数来做决策
        {
            "process_lesson": "process_lesson", # 如果决策函数返回 "process_lesson"，则跳回自己
            END: END                          # 如果决策函数返回 END，则结束
        }
    )

    # 编译图，生成可运行的应用
    app = graph.compile()
    return app