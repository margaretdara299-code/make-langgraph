import sys
import os
from pydantic import BaseModel
from typing import Any

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.engine.controller import generate_workflow_code, WorkflowPayload

def test_db_codegen():
    print("Testing DB-backed Code Generation...")
    sample_id = "8860eb26-09cc-4aec-a5d6-e476f2786894"
    db = SessionLocal()
    
    try:
        # Construct the payload
        payload = WorkflowPayload(skill_version_id=sample_id)
        
        # Call the controller function directly
        response = generate_workflow_code(payload, db)
        
        if response.get("status"):
            print("✅ ID-based code generation successful.")
            code = response["data"]["code"]
            print(f"Code Preview (first 10 lines):\n{'-'*20}")
            print("\n".join(code.splitlines()[:10]))
            print(f"{'-'*20}")
        else:
            print(f"❌ Generation failed: {response}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_db_codegen()
