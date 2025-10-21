# src/run_local.py
import json
import sys
from pathlib import Path
from datetime import datetime
import time

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from models import AgentState # V7/V8 AgentState
from graph import build_graph # V7/V8 Graph
# 导入数据库函数
from database import save_lesson_output

def main(input_path: str = "data/stage2_example.json"):
    print("--- Starting Learning Agent (Batch DB Save Mode) ---")
    start_time = time.time()

    try:
        input_data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        topic_name = input_data.get("topic", "Unknown Topic")
        topic_hsk_level = input_data.get("hsk_level")
    except FileNotFoundError:
        print(f"  - ERROR: Input file not found at '{input_path}'.")
        return
    except json.JSONDecodeError as e:
        print(f"  - ERROR: Failed to parse JSON file '{input_path}'. Error: {e}")
        return
    except Exception as load_e:
         print(f"  - ERROR loading or parsing JSON file '{input_path}'. Error: {load_e}")
         return

    print("  - Building and compiling the graph...")
    app = build_graph() #

    initial_state = {
        "stage2_input": input_data
    }

    print(f"  - Invoking agent execution for Topic: '{topic_name}'...")

    final_state_result = None 
    try:
        final_state_dict = app.invoke(initial_state, {"recursion_limit": 100})
        final_state = AgentState.model_validate(final_state_dict) #
        final_state_result = final_state # 保存最终状态

    except Exception as e:
         import traceback
         print(f"\n--- AGENT INVOCATION ERROR ---")
         print(f"An error occurred during graph execution: {e}")
         print(traceback.format_exc())

         return 

    end_time = time.time()
    total_duration = end_time - start_time
    print(f"\n--- Agent execution finished in {total_duration:.2f} seconds ---")


    if final_state_result and final_state_result.errors:
        print("\n--- Execution Errors ---")
        for error in final_state_result.errors:
            print(f"- {error}")



    if final_state_result and final_state_result.outputs:
        print(f"\n--- Saving {len(final_state_result.outputs)} completed lessons to database ---")

        for lesson_data_dict in final_state_result.outputs:
            lesson_name = lesson_data_dict.get("lesson_name", "Unknown Lesson")
            print(f"  - Saving lesson '{lesson_name}'...")
            # 调用保存函数，传入 topic 信息和 lesson 字典
            save_lesson_output(topic_name, lesson_data_dict, topic_hsk_level) #
        print("--- Database save complete ---")
    else:
        print("\n--- No lessons generated or found in final state. Nothing to save to database. ---")



    output_dir = project_root / "outputs"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"output_batch_{timestamp}.json"
    output_path = output_dir / output_filename

    final_output_structure = {
        "topic": topic_name,
        "lessons": final_state_result.outputs if final_state_result else [] 
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output_structure, f, ensure_ascii=False, indent=2)
        print(f"\n--- FINAL COMPLETE OUTPUT ---")
        print(f"Successfully saved complete results as backup to: {output_path}")
    except IOError as e:
        print(f"--- FAILED TO WRITE COMPLETE OUTPUT ---")
        print(f"  - ERROR: Could not write to file '{output_path}'. Reason: {e}")

    print("\n--- Run complete. ---")


if __name__ == "__main__":
        file_path = sys.argv[1] if len(sys.argv) > 1 else "data/stage2_example.json"
        main(file_path)