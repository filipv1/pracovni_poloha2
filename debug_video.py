# -*- coding: utf-8 -*-
"""
Debug script pro zjištění problému s pomalým zpracováním
"""

import sys
import os
import cv2
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_video_info():
    """Zkontroluj základní info o videu"""
    video_path = "../MVI_8745.MP4"
    
    print("=== VIDEO DIAGNOSTIKA ===")
    
    if not os.path.exists(video_path):
        print(f"CHYBA: Video neexistuje: {video_path}")
        return False
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("CHYBA: Nelze otevřít video")
        return False
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Rozlišení: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Celkem snímků: {frame_count}")
    print(f"Délka: {frame_count/fps:.1f} sekund")
    print(f"Velikost souboru: {os.path.getsize(video_path)/1024/1024:.1f} MB")
    
    cap.release()
    
    # Odhad času zpracování
    estimated_time_minutes = frame_count / (5 * 60)  # ~5 FPS processing
    print(f"Odhadovaný čas zpracování: {estimated_time_minutes:.1f} minut")
    
    return True

def test_frame_processing_speed():
    """Test rychlosti zpracování jednotlivých snímků"""
    video_path = "../MVI_8745.MP4"
    
    print("\n=== TEST RYCHLOSTI ZPRACOVÁNÍ ===")
    
    from src.pose_detector import PoseDetector
    from src.angle_calculator import TrunkAngleCalculator
    
    # Inicializace
    pose_detector = PoseDetector(model_complexity=2, min_detection_confidence=0.7)
    angle_calculator = TrunkAngleCalculator()
    
    cap = cv2.VideoCapture(video_path)
    
    print("Testování prvních 10 snímků...")
    
    total_time = 0
    successful_frames = 0
    
    for i in range(10):
        ret, frame = cap.read()
        if not ret:
            break
        
        start_time = time.time()
        
        # Pose detection
        pose_results = pose_detector.detect_pose(frame)
        
        if pose_detector.is_pose_valid(pose_results):
            # Angle calculation
            trunk_angle = angle_calculator.calculate_trunk_angle(pose_results.pose_world_landmarks)
            if trunk_angle is not None:
                successful_frames += 1
        
        frame_time = time.time() - start_time
        total_time += frame_time
        
        print(f"Snímek {i+1}: {frame_time:.3f}s, Úhel: {trunk_angle:.1f}° if trunk_angle else 'N/A'")
    
    cap.release()
    
    if successful_frames > 0:
        avg_time = total_time / 10
        fps = 1.0 / avg_time
        print(f"\nPrůměrný čas na snímek: {avg_time:.3f}s")
        print(f"Průměrné FPS: {fps:.1f}")
        print(f"Úspěšné detekce: {successful_frames}/10")
        
        # Odhad celkového času
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        estimated_total_time = total_frames * avg_time / 60
        print(f"Odhadovaný celkový čas: {estimated_total_time:.1f} minut")
        
        return True
    else:
        print("CHYBA: Žádné úspěšné detekce!")
        return False

def test_quick_analysis():
    """Rychlá analýza pouze prvních 50 snímků"""
    print("\n=== RYCHLÁ ANALÝZA (50 snímků) ===")
    
    try:
        from src.trunk_analyzer import TrunkAnalysisProcessor
        
        # Vytvoříme modifikovanou verzi pro test
        class QuickTrunkAnalyzer(TrunkAnalysisProcessor):
            def process_video(self):
                print("Zpracovávám prvních 50 snímků...")
                
                frame_number = 0
                max_frames = 50
                
                start_time = time.time()
                
                while frame_number < max_frames:
                    ret, frame = self.cap.read()
                    if not ret:
                        break
                    
                    frame_number += 1
                    
                    # Zpracování snímku
                    processed_frame = self._process_frame(frame, frame_number)
                    
                    # Progress každých 10 snímků
                    if frame_number % 10 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_number / elapsed
                        print(f"Zpracováno {frame_number}/50 snímků, {fps:.1f} FPS")
                
                total_time = time.time() - start_time
                final_fps = frame_number / total_time
                
                print(f"Celkem: {frame_number} snímků za {total_time:.1f}s")
                print(f"Finální FPS: {final_fps:.1f}")
                
                # Statistiky
                return self._generate_final_report()
        
        # Test
        processor = QuickTrunkAnalyzer(
            input_path="../MVI_8745.MP4",
            output_path="data/output/test_quick.mp4",
            model_complexity=2,
            min_detection_confidence=0.7,
            bend_threshold=60.0,
            smoothing_window=5
        )
        
        results = processor.process_video()
        
        print("RYCHLÁ ANALÝZA DOKONČENA!")
        return True
        
    except Exception as e:
        print(f"CHYBA při rychlé analýze: {e}")
        return False

def main():
    """Hlavní diagnostická funkce"""
    print("TRUNK ANALYSIS - DIAGNOSTIKA VÝKONU")
    print("=" * 50)
    
    # 1. Kontrola videa
    if not check_video_info():
        return
    
    # 2. Test rychlosti
    if not test_frame_processing_speed():
        return
    
    # 3. Rychlá analýza
    test_quick_analysis()

if __name__ == "__main__":
    main()