#!/usr/bin/env python3
"""
Deployment test script pro ověření funkčnosti na cloud platformě
"""

import requests
import sys
import time

def test_deployment(base_url):
    """Test základní funkčnosti deployed aplikace"""
    
    print(f"Testing deployment at: {base_url}")
    
    try:
        # Test 1: Health check
        print("1. Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ Health check OK")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
            
        # Test 2: Login page
        print("2. Testing login page...")
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200 and "login" in response.text.lower():
            print("   ✅ Login page loads")
        else:
            print(f"   ❌ Login page failed: {response.status_code}")
            return False
            
        # Test 3: Static resources
        print("3. Testing static resources...")
        # Test if CSS/JS loads (může být v inline v template)
        if "tailwind" in response.text or "daisyui" in response.text:
            print("   ✅ UI framework loaded")
        else:
            print("   ⚠️  UI framework check inconclusive")
            
        print("\n✅ Deployment test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Deployment test FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python deploy-test.py <BASE_URL>")
        print("Example: python deploy-test.py https://your-app.onrender.com")
        sys.exit(1)
        
    base_url = sys.argv[1].rstrip('/')
    success = test_deployment(base_url)
    sys.exit(0 if success else 1)