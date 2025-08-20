#!/usr/bin/env python3
"""
Test script pro CSV export funkcionalitu
"""

import sys
import os
from pathlib import Path

# Přidání src do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.csv_exporter import TrunkAngleCSVExporter, create_csv_path_from_video_path, export_angle_history_to_csv


def test_csv_exporter_basic():
    """Test základní funkcionalita CSV exportéru"""
    print("Test 1: Základní CSV export...")
    
    test_csv_path = "test_output.csv"
    
    try:
        # Test s context managerem
        with TrunkAngleCSVExporter(test_csv_path, video_fps=25.0) as exporter:
            # Export testovacích dat
            test_data = [
                (1, 25.5),
                (2, 30.2),
                (3, 45.8),
                (4, 60.1),
                (5, 75.3)
            ]
            
            for frame, angle in test_data:
                exporter.export_frame_data(frame, angle)
        
        # Ověření vytvoření souboru
        if os.path.exists(test_csv_path):
            print(f"OK CSV soubor vytvoren: {test_csv_path}")
            
            # Čtení a ověření obsahu
            with open(test_csv_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Obsah CSV:\n{content}")
            
            # Úklid
            os.remove(test_csv_path)
            print("OK Test 1 prosel uspesne")
        else:
            print("CHYBA CSV soubor nebyl vytvoren")
            
    except Exception as e:
        print(f"CHYBA Test 1 selhal: {e}")


def test_csv_path_generation():
    """Test generování CSV cesty z video cesty"""
    print("\nTest 2: Generování CSV cesty...")
    
    test_cases = [
        ("video.mp4", "video.csv"),
        ("C:/path/to/video.mp4", "C:/path/to/video.csv"),
        ("/unix/path/video.avi", "/unix/path/video.csv"),
        ("video_no_extension", "video_no_extension.csv")
    ]
    
    for video_path, expected_csv in test_cases:
        result = create_csv_path_from_video_path(video_path)
        if result == expected_csv:
            print(f"OK {video_path} -> {result}")
        else:
            print(f"CHYBA {video_path} -> {result} (ocekavano: {expected_csv})")
    
    print("OK Test 2 dokoncen")


def test_export_angle_history():
    """Test exportu historie úhlů"""
    print("\nTest 3: Export historie úhlů...")
    
    test_csv_path = "test_history.csv"
    test_angles = [23.4, 25.1, 30.5, 45.2, 60.8, 75.1, 42.3, 28.9, 15.2]
    
    try:
        export_angle_history_to_csv(test_angles, test_csv_path, video_fps=30.0)
        
        if os.path.exists(test_csv_path):
            print(f"OK Historie exportovana do: {test_csv_path}")
            
            # Ověření obsahu
            with open(test_csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"Pocet radku: {len(lines)} (vcetne hlavicky)")
                print(f"Prvni radky:\n{''.join(lines[:4])}")
            
            # Úklid
            os.remove(test_csv_path)
            print("OK Test 3 prosel uspesne")
        else:
            print("CHYBA CSV soubor s historii nebyl vytvoren")
            
    except Exception as e:
        print(f"CHYBA Test 3 selhal: {e}")


def test_csv_with_time():
    """Test CSV exportu s časovými údaji"""
    print("\nTest 4: CSV export s časem...")
    
    test_csv_path = "test_with_time.csv"
    
    try:
        with TrunkAngleCSVExporter(test_csv_path, video_fps=25.0) as exporter:
            # Test s časovými údaji
            test_data = [
                (1, 25.5),   # 0.04s při 25 FPS
                (25, 30.2),  # 1.00s při 25 FPS
                (50, 45.8),  # 2.00s při 25 FPS
            ]
            
            for frame, angle in test_data:
                exporter.export_frame_data_with_time(frame, angle)
        
        if os.path.exists(test_csv_path):
            print(f"OK CSV s casem vytvoren: {test_csv_path}")
            
            with open(test_csv_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Obsah CSV s casem:\n{content}")
            
            # Úklid
            os.remove(test_csv_path)
            print("OK Test 4 prosel uspesne")
        else:
            print("CHYBA CSV soubor s casem nebyl vytvoren")
            
    except Exception as e:
        print(f"CHYBA Test 4 selhal: {e}")


def main():
    """Spuštění všech testů"""
    print("=== CSV Export Tests ===\n")
    
    test_csv_exporter_basic()
    test_csv_path_generation()
    test_export_angle_history()
    test_csv_with_time()
    
    print("\n=== Vsechny testy dokonceny ===")
    print("\nPro otestování kompletní integrace spusťte:")
    print("python main.py input_video.mp4 output_video.mp4 --csv-export")


if __name__ == "__main__":
    main()