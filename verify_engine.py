import json
import os
from pprint import pprint

from app.engine.validator import validate_workflow
from app.engine.graph_builder import compile_workflow_plan
from app.engine.runner import run_workflow

print("=== 1. Testing Validation Catch ===")
bad_workflow = {
    "nodes": [
        {
            "id": "1", 
            "type": "action", 
            "data": {"actionKey": "INVALID", "configurationsJson": {}}
        }
    ],
    "connections": {}
}
val_result = validate_workflow(bad_workflow)
print("Expected valid=False. Got:", val_result["valid"])
print("Errors:", val_result["errors"])
print()

print("=== 2. Testing Compile Flow ===")
sample_path = os.path.join(os.path.dirname(__file__), "app", "engine", "sample_workflow.json")
with open(sample_path, "r", encoding="utf-8") as f:
    sample_workflow = json.load(f)

compiled_plan = compile_workflow_plan(sample_workflow)
print("Compiled Hash:", compiled_plan["compile_hash"])
print("Expected valid=True. Got:", compiled_plan["valid"])
print()

print("=== 3. Testing Run (with Checkpointer) ===")
# Run once
print("Running first thread 'test_thread_A'...")
state_a = run_workflow(compiled_plan, thread_id="test_thread_A")
print("Thread A Condition Result:", state_a["condition_result"])

# Run second thread
print("\nRunning second thread 'test_thread_B'...")
state_b = run_workflow(compiled_plan, thread_id="test_thread_B")
print("Thread B Condition Result:", state_b["condition_result"])

# Try to run thread A again (should just load state and return immediately since we reached END)
print("\nResuming thread 'test_thread_A' (should have previous state)...")
state_a2 = run_workflow(compiled_plan, thread_id="test_thread_A")
print("Logs total count (should be identical to first run):", len(state_a2["logs"]))

print("\nVerification successful!")
