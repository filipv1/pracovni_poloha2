#!/usr/bin/env python3
"""
Test script for chunked upload functionality
"""

import os
import sys
import requests
import tempfile
import time
from pathlib import Path

def create_test_file(size_mb=10):
    """Create a test file of specified size"""
    test_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    
    # Write dummy data to create a file of specified size
    chunk_size = 1024 * 1024  # 1MB chunks
    data = b'x' * chunk_size
    
    for i in range(size_mb):
        test_file.write(data)
    
    test_file.close()
    return test_file.name

def test_chunked_upload(base_url, username, password):
    """Test the chunked upload functionality"""
    session = requests.Session()
    
    try:
        # Login first
        print("Logging in...")
        login_response = session.post(f"{base_url}/login", data={
            'username': username,
            'password': password
        })
        
        if login_response.status_code != 200 or 'login' in login_response.url:
            print("[FAIL] Login failed")
            return False
        
        print("[OK] Login successful")
        
        # Create test file
        print("Creating test file (10MB)...")
        test_file_path = create_test_file(10)  # 10MB file
        file_size = os.path.getsize(test_file_path)
        print(f"[OK] Test file created: {file_size} bytes")
        
        # Initialize upload
        print("Initializing chunked upload...")
        init_response = session.post(f"{base_url}/upload/init", json={
            'filename': 'test_video.mp4',
            'filesize': file_size,
            'chunk_size': 1024 * 1024  # 1MB chunks
        })
        
        if init_response.status_code != 200:
            print(f"[FAIL] Upload init failed: {init_response.status_code}")
            print(init_response.text)
            return False
        
        init_data = init_response.json()
        job_id = init_data['job_id']
        chunk_size = init_data['chunk_size']
        total_chunks = init_data['total_chunks']
        
        print(f"[OK] Upload initialized: job_id={job_id}, chunks={total_chunks}")
        
        # Upload chunks
        print("Uploading chunks...")
        with open(test_file_path, 'rb') as f:
            for chunk_index in range(total_chunks):
                chunk_data = f.read(chunk_size)
                
                chunk_response = session.post(
                    f"{base_url}/upload/chunk/{job_id}/{chunk_index}",
                    data=chunk_data,
                    headers={'Content-Type': 'application/octet-stream'}
                )
                
                if chunk_response.status_code != 200:
                    print(f"[FAIL] Chunk {chunk_index} upload failed: {chunk_response.status_code}")
                    print(chunk_response.text)
                    return False
                
                result = chunk_response.json()
                progress = result['progress']
                print(f"  Chunk {chunk_index+1}/{total_chunks} uploaded ({progress:.1f}%)")
        
        print("[OK] All chunks uploaded successfully")
        
        # Check upload status
        status_response = session.get(f"{base_url}/upload/status/{job_id}")
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"[OK] Upload status: {status['status']} ({status['progress']:.1f}%)")
        
        # Cleanup
        cleanup_response = session.delete(f"{base_url}/upload/cleanup/{job_id}")
        if cleanup_response.status_code == 200:
            print("[OK] Cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {str(e)}")
        return False
    
    finally:
        # Remove test file
        if 'test_file_path' in locals():
            try:
                os.unlink(test_file_path)
                print("[OK] Test file cleaned up")
            except:
                pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_chunked_upload.py <base_url> [username] [password]")
        print("Example: python test_chunked_upload.py http://localhost:5000")
        print("Example: python test_chunked_upload.py https://your-app.railway.app vaclavik password")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    username = sys.argv[2] if len(sys.argv) > 2 else 'vaclavik'
    password = sys.argv[3] if len(sys.argv) > 3 else 'A9xL4pK7Fn'
    
    print(f"Testing chunked upload at: {base_url}")
    print(f"Username: {username}")
    print("-" * 50)
    
    success = test_chunked_upload(base_url, username, password)
    
    if success:
        print("\n[OK] All tests passed!")
    else:
        print("\n[FAIL] Tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()