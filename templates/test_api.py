"""
Test script to verify CodeGenie API endpoints
Run this after starting the Flask server
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_signup():
    """Test user signup"""
    print("\n=== Testing Signup ===")
    
    data = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "TestPass123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/signup",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✓ Signup successful!")
            return True
        else:
            print("✗ Signup failed")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_login(email, password):
    """Test user login"""
    print("\n=== Testing Login ===")
    
    data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/login",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✓ Login successful!")
            return True
        else:
            print("✗ Login failed")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_duplicate_signup():
    """Test duplicate email signup"""
    print("\n=== Testing Duplicate Signup ===")
    
    data = {
        "name": "Test User 2",
        "email": "test@example.com",  # Same email
        "password": "TestPass456"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/signup",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✓ Duplicate email correctly rejected!")
            return True
        else:
            print("✗ Duplicate email not handled properly")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_short_password():
    """Test password length validation"""
    print("\n=== Testing Short Password ===")
    
    data = {
        "name": "Test User 3",
        "email": "test3@example.com",
        "password": "short"  # Less than 8 characters
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/signup",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✓ Short password correctly rejected!")
            return True
        else:
            print("✗ Short password validation not working")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("CodeGenie API Test Suite")
    print("=" * 50)
    print("Make sure Flask server is running on port 5000!")
    
    # Run tests
    results = []
    
    results.append(("Signup", test_signup()))
    results.append(("Login", test_login("test@example.com", "TestPass123")))
    results.append(("Duplicate Email", test_duplicate_signup()))
    results.append(("Short Password", test_short_password()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
