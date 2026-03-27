import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from main import application
from fastapi.testclient import TestClient

client = TestClient(application)

def test_claims_api():
    print("Testing Dummy Claims API...")
    
    # 1. GET ALL
    resp = client.get("/api/claims")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ GET /api/claims: Found {data['data']['total']} items")
    else:
        print(f"❌ GET /api/claims failed: {resp.status_code}")

    # 2. GET BY ID
    claim_id = "C001"
    resp = client.get(f"/api/claims/{claim_id}")
    if resp.status_code == 200:
        print(f"✅ GET /api/claims/{claim_id}: Success")
    else:
        print(f"❌ GET /api/claims/{claim_id} failed")

    # 3. POST
    new_claim = {"claim_id": "C003", "patient_name": "Test Patient", "status": "New"}
    resp = client.post("/api/claims", json=new_claim)
    if resp.status_code == 200:
        print("✅ POST /api/claims: Success")
    else:
        print(f"❌ POST /api/claims failed: {resp.text}")

if __name__ == "__main__":
    test_claims_api()
