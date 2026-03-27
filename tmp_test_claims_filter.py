import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from main import application
from fastapi.testclient import TestClient

client = TestClient(application)

def test_claims_filter():
    print("Testing Dummy Claims Status Filter...")
    
    # 1. Filter by Pending
    resp = client.get("/api/claims?status=Pending")
    if resp.status_code == 200:
        data = resp.json()
        items = data['data']['items']
        print(f"✅ status=Pending: Found {len(items)} items")
        for item in items:
            if item['status'] != 'Pending':
                print(f"❌ Filtering failed: Found item with status {item['status']}")
    else:
        print(f"❌ Filter request failed")

    # 2. Filter by Paid
    resp = client.get("/api/claims?status=Paid")
    if resp.status_code == 200:
        data = resp.json()
        items = data['data']['items']
        print(f"✅ status=Paid: Found {len(items)} items")
    
    # 3. Filter by non-existent
    resp = client.get("/api/claims?status=Invalid")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ status=Invalid: Found {data['data']['total']} items")

if __name__ == "__main__":
    test_claims_filter()
