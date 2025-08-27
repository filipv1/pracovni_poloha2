#!/usr/bin/env python3
"""
Quick test to verify processing speed
"""

import requests
import time
import json

BASE_URL = "http://localhost:5000"
LOGIN_DATA = {"username": "admin", "password": "admin123"}

def quick_test():
    session = requests.Session()
    
    # Login
    print("Logging in...")
    response = session.post(f"{BASE_URL}/login", data=LOGIN_DATA)
    if response.status_code != 200 or "login" in response.url:
        print("Login failed")
        return False
    
    # Upload
    print("Uploading file...")
    job_id = f"speed-test-{int(time.time())}"
    
    with open('test.mp4', 'rb') as f:
        files = {'file': ('test.mp4', f, 'video/mp4')}
        data = {'job_id': job_id}
        response = session.post(f"{BASE_URL}/upload", files=files, data=data)
    
    if response.status_code != 200:
        print(f"Upload failed: {response.status_code}")
        return False
    
    # Start processing
    print("Starting processing...")
    start_time = time.time()
    
    response = session.post(f"{BASE_URL}/process", 
                          json={"job_id": job_id},
                          headers={'Content-Type': 'application/json'})
    
    if response.status_code != 200:
        print("Processing start failed")
        return False
    
    # Monitor for completion
    print("Monitoring progress...")
    while True:
        # Check if files are available for download
        video_response = session.get(f"{BASE_URL}/download/{job_id}/video")
        excel_response = session.get(f"{BASE_URL}/download/{job_id}/excel")
        
        if video_response.status_code == 200 and excel_response.status_code == 200:
            elapsed = time.time() - start_time
            print(f"SUCCESS! Processing completed in {elapsed:.1f} seconds")
            print(f"Video size: {len(video_response.content)} bytes")
            print(f"Excel size: {len(excel_response.content)} bytes")
            return True
        elif video_response.status_code == 400:
            # Still processing
            elapsed = time.time() - start_time
            print(f"Still processing... ({elapsed:.1f}s)")
            
            if elapsed > 120:  # 2 minute timeout
                print("TIMEOUT - processing too slow")
                return False
                
            time.sleep(3)
        else:
            print(f"Error: video={video_response.status_code}, excel={excel_response.status_code}")
            return False

if __name__ == "__main__":
    print("Running quick processing speed test...")
    success = quick_test()
    if success:
        print("Test PASSED - processing is working fast!")
    else:
        print("Test FAILED - processing is still slow")