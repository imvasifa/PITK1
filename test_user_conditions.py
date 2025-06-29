#!/usr/bin/env python3
"""
Test script to check user conditions functionality
"""

import requests
import json

def test_user_conditions_api():
    """Test the user conditions API endpoints"""
    
    # Base URL
    base_url = "http://localhost:5000"
    
    # Test data
    test_condition = {
        "name": "Test Condition",
        "scan_clause": "latest close > latest ema(latest close, 20)",
        "link": "https://example.com"
    }
    
    print("🧪 Testing User Conditions API...")
    
    # Test 1: Get user conditions
    print("\n1. Testing GET /api/user-conditions")
    try:
        response = requests.get(f"{base_url}/api/user-conditions")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            conditions = response.json()
            print(f"   Found {len(conditions)} conditions")
            for condition in conditions:
                print(f"   - {condition.get('name', 'Unknown')} (ID: {condition.get('id', 'Unknown')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Add a test condition
    print("\n2. Testing POST /api/user-conditions")
    try:
        response = requests.post(
            f"{base_url}/api/user-conditions",
            json=test_condition,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   Success: {result.get('message', 'Condition added')}")
            condition_id = result.get('id')
        else:
            print(f"   Error: {response.text}")
            condition_id = None
    except Exception as e:
        print(f"   Error: {e}")
        condition_id = None
    
    # Test 3: Get conditions again to verify
    print("\n3. Testing GET /api/user-conditions (after adding)")
    try:
        response = requests.get(f"{base_url}/api/user-conditions")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            conditions = response.json()
            print(f"   Found {len(conditions)} conditions")
            for condition in conditions:
                print(f"   - {condition.get('name', 'Unknown')} (ID: {condition.get('id', 'Unknown')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Delete the test condition if it was created
    if condition_id:
        print(f"\n4. Testing DELETE /api/user-conditions/{condition_id}")
        try:
            response = requests.delete(f"{base_url}/api/user-conditions/{condition_id}")
            print(f"   Status: {response.status_code}")
            if response.status_code in [200, 204]:
                print("   Success: Test condition deleted")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n✅ User Conditions API test completed!")

if __name__ == "__main__":
    test_user_conditions_api() 