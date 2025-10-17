
import json
import sys
from pathlib import Path
from datetime import datetime 
import time

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root / "src"))

from models import AgentState
from graph import build_graph

def main(input_path: str = "data/stage2_example.json"):
    """
    主执行函数
    """
    print("--- Starting Learning Agent ---")
    start_time=time.time()
    
    print(f"  - Loading input data from: {input_path}")
    try:
        input_data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"  - ERROR: Input file not found at '{input_path}'. Please create it.")
        return
    except json.JSONDecodeError as e:
        print(f"  - ERROR: Failed to parse JSON file. Error: {e}")
        return

    print("  - Building and compiling the graph...")
    app = build_graph()

    initial_state = {
        "stage2_input": input_data
    }

    print("  - Invoking the agent... This may take a few moments.")
    final_state = app.invoke(initial_state)
    end_time = time.time()
    total_duration = end_time - start_time
    print(f"\n--- Agent execution finished in {total_duration:.2f} seconds ---\n")
    print("\n--- Agent execution finished ---\n")
    if final_state.get("errors"):
        print("--- ERRORS ---")
        for error in final_state["errors"]:
            print(f"- {error}")

    output_dir = project_root / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"output_{timestamp}.json"
    output_path = output_dir / output_filename
    
    final_output_structure = {
        "execution_time_seconds": round(total_duration, 2),
        "results": final_state.get("outputs", [])
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output_structure, f, ensure_ascii=False, indent=2)
        
        print(f"--- FINAL OUTPUT ---")
        print(f"Successfully saved results to: {output_path}")

    except IOError as e:
        print(f"--- FAILED TO WRITE OUTPUT ---")
        print(f"  - ERROR: Could not write to file '{output_path}'. Reason: {e}")

    print("\n--- Run complete. ---")


if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "data/stage2_example.json"
    main(file_path)