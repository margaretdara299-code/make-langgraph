import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.engine.controller import generate_workflow_code_by_id

def test_get_codegen():
    print("Testing GET-based Code Generation...")
    sample_id = "8860eb26-09cc-4aec-a5d6-e476f2786894"
    db = SessionLocal()
    
    try:
        # Call the GET handler directly
        response = generate_workflow_code_by_id(sample_id, db)
        
        if response.get("status"):
            print("✅ GET-based code generation successful.")
            code = response["data"]["code"]
            print(f"Code Preview (first 5 lines):\n{'-'*20}")
            print("\n".join(code.splitlines()[:5]))
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
    test_get_codegen()
