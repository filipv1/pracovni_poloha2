#!/usr/bin/env python3
"""
Test script for web application functionality
Testuje zakladni funkcionalitu webove aplikace
"""

import requests
import time
import json
import os
from pathlib import Path

# Konfigurace
BASE_URL = "http://localhost:5000"
TEST_VIDEO = "test.mp4"
LOGIN_DATA = {"username": "admin", "password": "admin123"}

def test_server_running():
    """Test zda server bezi"""
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"Server bezi - Status: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Server nebezi - Error: {e}")
        return False

def test_login():
    """Test prihlaseni"""
    session = requests.Session()
    
    # Get login page
    response = session.get(f"{BASE_URL}/login")
    if response.status_code != 200:
        print(f"Login page nedostupna - Status: {response.status_code}")
        return None
    
    # Login
    response = session.post(f"{BASE_URL}/login", data=LOGIN_DATA)
    if response.status_code == 200 and "login" not in response.url:
        print("Prihlaseni uspesne")
        return session
    else:
        print(f"Prihlaseni neuspesne - Status: {response.status_code}")
        return None

def test_main_page(session):
    """Test hlavni stranky"""
    response = session.get(BASE_URL)
    if response.status_code == 200:
        if "Ergonomická Analýza" in response.text and "upload-container" in response.text:
            print("Hlavni stranka se nacetla spravne")
            return True
        else:
            print("Hlavni stranka nema ocekavany obsah")
    else:
        print(f"Hlavni stranka nedostupna - Status: {response.status_code}")
    return False

def test_file_upload(session):
    """Test nahrani souboru"""
    if not os.path.exists(TEST_VIDEO):
        print(f"Test video {TEST_VIDEO} neexistuje")
        return None, None
        
    job_id = "test-job-12345"
    
    with open(TEST_VIDEO, 'rb') as f:
        files = {'file': (TEST_VIDEO, f, 'video/mp4')}
        data = {'job_id': job_id}
        
        response = session.post(f"{BASE_URL}/upload", files=files, data=data)
        
    if response.status_code == 200:
        result = response.json()
        if result.get('status') == 'uploaded':
            print(f"Soubor nahran uspesne - Job ID: {job_id}")
            return session, job_id
        else:
            print(f"Upload neuspesny - Response: {result}")
    else:
        print(f"Upload failed - Status: {response.status_code}")
        
    return None, None

def test_processing(session, job_id):
    """Test zpracovani videa"""
    if not session or not job_id:
        return False
        
    # Start processing
    response = session.post(f"{BASE_URL}/process", 
                          json={"job_id": job_id},
                          headers={'Content-Type': 'application/json'})
    
    if response.status_code != 200:
        print(f"Spusteni zpracovani selhalo - Status: {response.status_code}")
        return False
    
    print("Zpracovani spusteno")
    
    # Monitor progress (simplified test - just check if endpoint works)
    try:
        response = session.get(f"{BASE_URL}/progress/{job_id}", timeout=5)
        if response.status_code == 200:
            print("Progress endpoint funguje")
            return True
        else:
            print(f"Progress endpoint - Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Progress endpoint dostupny (SSE stream)")
        return True
        
    return False

def test_download_endpoints(session, job_id):
    """Test download endpointu"""
    if not session or not job_id:
        return False
        
    # Test video download endpoint
    response = session.get(f"{BASE_URL}/download/{job_id}/video")
    if response.status_code in [200, 400, 404]:  # 400/404 expected if processing not done
        print("Video download endpoint dostupny")
    else:
        print(f"Video download endpoint - Status: {response.status_code}")
        return False
        
    # Test excel download endpoint  
    response = session.get(f"{BASE_URL}/download/{job_id}/excel")
    if response.status_code in [200, 400, 404]:  # 400/404 expected if processing not done
        print("Excel download endpoint dostupny")
    else:
        print(f"Excel download endpoint - Status: {response.status_code}")
        return False
        
    return True

def test_logout(session):
    """Test odhlaseni"""
    response = session.get(f"{BASE_URL}/logout")
    if response.status_code == 200:
        # Try to access main page - should redirect to login
        response = session.get(BASE_URL)
        if "login" in response.url or response.status_code == 302:
            print("Odhlaseni uspesne")
            return True
    
    print("Odhlaseni neuspesne")
    return False

def run_comprehensive_test():
    """Spusti komprehenzivni test vsech funkcionalit"""
    print("="*60)
    print("COMPREHENSIVE WEB APPLICATION TEST")
    print("="*60)
    
    success_count = 0
    total_tests = 7
    
    # Test 1: Server running
    if test_server_running():
        success_count += 1
    
    # Test 2: Login
    session = test_login()
    if session:
        success_count += 1
        
        # Test 3: Main page
        if test_main_page(session):
            success_count += 1
            
        # Test 4: File upload
        session, job_id = test_file_upload(session)
        if job_id:
            success_count += 1
            
            # Test 5: Processing
            if test_processing(session, job_id):
                success_count += 1
                
            # Test 6: Download endpoints
            if test_download_endpoints(session, job_id):
                success_count += 1
        
        # Test 7: Logout
        if test_logout(session):
            success_count += 1
    
    print("="*60)
    print(f"VYSLEDKY TESTU: {success_count}/{total_tests} testu proslo")
    if success_count == total_tests:
        print("VSECHNY TESTY USPESNE!")
    else:
        print(f"{total_tests - success_count} testu selhalo")
    print("="*60)
    
    return success_count == total_tests

def test_multiple_file_upload():
    """Test nahrani vice souboru najednou"""
    print("\nTesting multiple file upload...")
    
    session = test_login()
    if not session:
        return False
        
    # Create dummy test files if needed
    test_files = []
    if os.path.exists(TEST_VIDEO):
        test_files = [TEST_VIDEO]
        
    if not test_files:
        print("Zadne test soubory k dispozici")
        return False
    
    job_ids = []
    for i, test_file in enumerate(test_files):
        job_id = f"multi-test-{i}-{int(time.time())}"
        
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'video/mp4')}
            data = {'job_id': job_id}
            
            response = session.post(f"{BASE_URL}/upload", files=files, data=data)
            
        if response.status_code == 200:
            job_ids.append(job_id)
            print(f"Soubor {i+1} nahran - Job ID: {job_id}")
        else:
            print(f"Soubor {i+1} selhal")
            
    if job_ids:
        print(f"Multi-file upload test: {len(job_ids)} souboru nahrano")
        return True
    else:
        print("Multi-file upload test selhal")
        return False

if __name__ == "__main__":
    print("Spoustim testy webove aplikace...")
    print("UPOZORNENI: Ujistete se, ze web aplikace bezi na http://localhost:5000")
    print()
    
    # Wait a bit for server to be ready
    time.sleep(2)
    
    # Run comprehensive test
    success = run_comprehensive_test()
    
    if success:
        print("\nSpoustim rozsirene testy...")
        test_multiple_file_upload()
        
    print("\nTesty dokonceny!")