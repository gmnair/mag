"""Test client for testing the transaction review system."""
import requests
import json
import time
import sys

API_BASE_URL = "http://localhost:8000"


def test_transaction_review(case_id: str, file_path: str):
    """Test the transaction review workflow."""
    print(f"\n=== Testing Transaction Review for Case: {case_id} ===\n")
    
    # Step 1: Trigger workflow
    print("1. Triggering transaction review workflow...")
    response = requests.post(
        f"{API_BASE_URL}/api/v1/transaction-review",
        json={
            "case_id": case_id,
            "file_path": file_path
        }
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return
    
    result = response.json()
    print(f"✓ Workflow initiated")
    print(f"  Conversation ID: {result.get('conversation_id')}")
    print(f"  Task ID: {result.get('task_id')}")
    
    # Step 2: Poll for status
    print("\n2. Polling for workflow status...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(2)
        attempt += 1
        
        status_response = requests.get(f"{API_BASE_URL}/api/v1/status/{case_id}")
        
        if status_response.status_code == 200:
            status = status_response.json()
            current_status = status.get("status")
            current_agent = status.get("current_agent")
            
            print(f"  Attempt {attempt}: Status={current_status}, Agent={current_agent}")
            
            if current_status == "completed":
                print(f"\n✓ Workflow completed!")
                print(f"  Summary: {status.get('summary', 'N/A')[:200]}...")
                break
            elif current_status in ["failed", "error"]:
                print(f"\n✗ Workflow failed with status: {current_status}")
                break
        else:
            print(f"  Attempt {attempt}: Status check failed ({status_response.status_code})")
    
    if attempt >= max_attempts:
        print(f"\n⚠ Timeout waiting for workflow completion")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_client.py <case_id> <file_path>")
        print("Example: python test_client.py CASE-001 example_transactions.csv")
        sys.exit(1)
    
    case_id = sys.argv[1]
    file_path = sys.argv[2]
    
    test_transaction_review(case_id, file_path)

