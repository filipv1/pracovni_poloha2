# -*- coding: utf-8 -*-
"""
Jednoducha diagnostika
"""

import sys
import os
import cv2
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    video_path = "../MVI_8745.MP4"
    
    print("DIAGNOSTIKA VIDEA:")
    print("=" * 30)
    
    if not os.path.exists(video_path):
        print("Video neexistuje!")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Nelze otevrit video")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Rozliseni: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Snimky: {frame_count}")
    print(f"Delka: {frame_count/fps:.1f} sekund")
    print(f"Velikost: {os.path.getsize(video_path)/1024/1024:.1f} MB")
    
    cap.release()
    
    # Odhad času - model complexity 2 je VELMI pomalý
    estimated_time = frame_count / (2 * 60)  # ~2 FPS s heavy modelem
    print(f"Odhadovany cas: {estimated_time:.1f} minut")
    
    if estimated_time > 30:
        print("\nVAROVANI: Video je moc dlouhe pro heavy model!")
        print("Doporučeni:")
        print("1. Pouzijte --model-complexity 1 (rychlejsi)")
        print("2. Nebo zkratte video")
        print("3. Nebo snizit rozliseni")

if __name__ == "__main__":
    main()