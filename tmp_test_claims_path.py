import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from main import application
from fastapi.testclient import TestClient

client = TestClient(application)

def test_claims_path_filter():
    print("Testing Dummy Claims Path Status Filter...")
    
    # 1. Path Filter by Pending
    resp = client.get("/api/claims/status/Pending")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ GET /api/claims/status/Pending: Found {data['data']['total']} items")
    else:
        print(f"❌ Path filter failed")

if __name__ == "__main__":
    test_claims_path_filter()
