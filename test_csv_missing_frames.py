#!/usr/bin/env python3
"""
Test script pro ověření správného zpracování chybějících framů v CSV exportu
"""

import sys
import os
from pathlib import Path

# Přidání src do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.csv_exporter import TrunkAngleCSVExporter


def test_missing_frames_handling():
    """Test zpracování chybějících framů"""
    print("Test: Zpracovani chybejicich framu...")
    
    test_csv_path = "test_missing_frames.csv"
    
    try:
        with TrunkAngleCSVExporter(test_csv_path, video_fps=25.0) as exporter:
            # Simulace situace s chybějícími framy
            test_data = [
                (1, 25.5),
                (2, 30.2),
                # Framy 3, 4 chybí
                (5, 45.8),
                (6, None),  # Frame 6 - detection failed
                # Frame 7 chybí
                (8, 60.1),
                (9, None),  # Frame 9 - detection failed
                (10, 75.3),
                # Framy 11-14 chybí
                (15, 20.1)
            ]
            
            for frame, angle in test_data:
                exporter.export_frame_data(frame, angle)
        
        # Ověření výsledku
        if os.path.exists(test_csv_path):
            print(f"OK CSV soubor vytvoren: {test_csv_path}")
            
            with open(test_csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            print(f"Pocet radku: {len(lines)} (vcetne hlavicky)")
            print("Obsah CSV:")
            for i, line in enumerate(lines):
                print(f"{i+1:2d}: {line.strip()}")
            
            # Kontrola, že jsou všechny framy 1-15 přítomny
            expected_frames = set(range(1, 16))
            actual_frames = set()
            
            for line in lines[1:]:  # Přeskočíme hlavičku
                if line.strip():
                    frame_num = int(line.split(',')[0])
                    actual_frames.add(frame_num)
            
            if expected_frames == actual_frames:
                print("OK Vsechny framy 1-15 jsou pritomny v CSV")
            else:
                missing = expected_frames - actual_frames
                print(f"CHYBA Chybejici framy: {missing}")
            
            # Kontrola FALSE hodnot
            false_count = 0
            for line in lines[1:]:
                if 'FALSE' in line:
                    false_count += 1
            
            print(f"Pocet FALSE zaznamu: {false_count}")
            
            # Úklid
            os.remove(test_csv_path)
            print("OK Test dokoncen uspesne")
        else:
            print("CHYBA CSV soubor nebyl vytvoren")
            
    except Exception as e:
        print(f"CHYBA Test selhal: {e}")


def test_continuous_frames():
    """Test kontinuálních framů bez chybějících"""
    print("\nTest: Kontinualni framy...")
    
    test_csv_path = "test_continuous.csv"
    
    try:
        with TrunkAngleCSVExporter(test_csv_path, video_fps=25.0) as exporter:
            # Kontinuální sekvence framů
            for frame in range(1, 11):
                angle = 20.0 + frame * 2.5  # Simulovaný úhel
                exporter.export_frame_data(frame, angle)
        
        if os.path.exists(test_csv_path):
            with open(test_csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print(f"Kontinualni sekvence: {len(lines)-1} zaznamu")
            
            # Kontrola, že nejsou žádné FALSE hodnoty
            false_found = any('FALSE' in line for line in lines)
            if not false_found:
                print("OK Zadne FALSE hodnoty v kontinualni sekvenci")
            else:
                print("CHYBA Nalezeny FALSE hodnoty v kontinualni sekvenci")
            
            os.remove(test_csv_path)
            print("OK Test kontinualnich framu prosel")
        
    except Exception as e:
        print(f"CHYBA Test kontinualnich framu selhal: {e}")


def main():
    """Spuštění všech testů"""
    print("=== Test CSV Export - Chybejici framy ===\n")
    
    test_missing_frames_handling()
    test_continuous_frames()
    
    print("\n=== Vsechny testy dokonceny ===")
    print("\nPro otestovani kompletni integrace spustte:")
    print("python main.py input_video.mp4 output_video.mp4 --csv-export")
    print("Pak zkontrolujte, ze output_video.csv ma stejny pocet radku jako framu ve videu.")


if __name__ == "__main__":
    main()