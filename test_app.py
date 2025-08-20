#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testovaci script pro Trunk Analysis aplikaci
Vytvori ukazkove video a otestuje celou pipeline
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils import create_sample_video, get_video_info, validate_video_file
from src.trunk_analyzer import TrunkAnalysisProcessor


def test_sample_video_creation():
    """Test vytvoreni ukazkoveho videa"""
    print("=== Test: Vytvoreni ukazkoveho videa ===")
    
    sample_path = "data/input/sample_video.mp4"
    
    # Zajištění existence adresáře
    os.makedirs(os.path.dirname(sample_path), exist_ok=True)
    
    success = create_sample_video(
        output_path=sample_path,
        duration_seconds=10,
        fps=30,
        width=640,
        height=480
    )
    
    if success:
        print(f"+ Ukazkove video vytvoreno: {sample_path}")
        
        # Validace videa
        is_valid, message = validate_video_file(sample_path)
        if is_valid:
            print(f"+ Video je validni: {message}")
            
            # Info o videu
            info = get_video_info(sample_path)
            if info:
                print(f"  - Rozliseni: {info['width']}x{info['height']}")
                print(f"  - FPS: {info['fps']}")
                print(f"  - Delka: {info['duration']:.1f}s")
                print(f"  - Snimky: {info['frame_count']}")
                print(f"  - Velikost: {info['size_mb']:.1f} MB")
        else:
            print(f"- Video neni validni: {message}")
            return False
    else:
        print("- Nepodarilo se vytvorit ukazkove video")
        return False
    
    return True


def test_trunk_analysis():
    """Test analýzy trupu"""
    print("\n=== Test: Analýza ohnutí trupu ===")
    
    input_path = "data/input/sample_video.mp4"
    output_path = "data/output/analyzed_video.mp4"
    
    # Zajištění existence výstupního adresáře
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Vytvoření procesoru s testovací konfigurací
        processor = TrunkAnalysisProcessor(
            input_path=input_path,
            output_path=output_path,
            model_complexity=1,  # Full model pro lepší přesnost
            min_detection_confidence=0.3,  # Nižší threshold pro testovací video
            bend_threshold=45.0,  # Nižší threshold pro demo účely
            smoothing_window=3
        )
        
        print(f"✓ Procesor inicializován")
        print(f"  - Vstup: {input_path}")
        print(f"  - Výstup: {output_path}")
        
        # Spuštění analýzy
        results = processor.process_video(show_progress=True)
        
        # Kontrola výsledků
        if os.path.exists(output_path):
            print(f"✓ Výstupní video vytvořeno: {output_path}")
            
            # Validace výstupního videa
            is_valid, message = validate_video_file(output_path)
            if is_valid:
                print(f"✓ Výstupní video je validní")
            else:
                print(f"✗ Výstupní video není validní: {message}")
                return False
        else:
            print(f"✗ Výstupní video nebylo vytvořeno")
            return False
        
        # Kontrola statistik
        if 'processing_stats' in results:
            stats = results['processing_stats']
            print(f"✓ Statistiky zpracování:")
            print(f"  - Celkem snímků: {stats['total_frames']}")
            print(f"  - Zpracované snímky: {stats['processed_frames']}")
            print(f"  - Neúspěšné detekce: {stats['failed_detections']}")
            
            if 'success_rate' in results:
                print(f"  - Úspěšnost: {results['success_rate']:.1f}%")
        
        # Kontrola bend analýzy
        if 'bend_analysis' in results and results['bend_analysis']:
            bend_stats = results['bend_analysis']
            print(f"✓ Analýza ohnutí:")
            print(f"  - Procento ohnutí: {bend_stats['bend_percentage']:.2f}%")
            print(f"  - Průměrný úhel: {bend_stats['average_angle']:.2f}°")
            print(f"  - Max úhel: {bend_stats['max_angle']:.2f}°")
        
        return True
        
    except Exception as e:
        print(f"✗ Chyba během analýzy: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_command_line_interface():
    """Test command line interface"""
    print("\n=== Test: Command Line Interface ===")
    
    # Test help
    import subprocess
    import sys
    
    try:
        # Test --help
        result = subprocess.run([
            sys.executable, "main.py", "--help"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✓ --help funguje správně")
        else:
            print("✗ --help nefunguje")
            return False
        
        # Test --version
        result = subprocess.run([
            sys.executable, "main.py", "--version"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✓ --version funguje správně")
        else:
            print("✗ --version nefunguje")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Chyba při testování CLI: {e}")
        return False


def main():
    """Hlavní testovací funkce"""
    print("TRUNK ANALYSIS - TESTOVÁNÍ APLIKACE")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test 1: Vytvoření ukázkového videa
    if not test_sample_video_creation():
        all_tests_passed = False
    
    # Test 2: Analýza trupu
    if not test_trunk_analysis():
        all_tests_passed = False
    
    # Test 3: Command line interface
    if not test_command_line_interface():
        all_tests_passed = False
    
    # Výsledek
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("✅ VŠECHNY TESTY PROŠLY ÚSPĚŠNĚ!")
        print("\nAplikace je připravena k použití.")
        print("\nPříklad spuštění:")
        print("python main.py data/input/sample_video.mp4 data/output/result.mp4")
    else:
        print("❌ NĚKTERÉ TESTY SELHALY!")
        print("Prosím zkontrolujte chyby výše.")
    
    print("=" * 50)


if __name__ == "__main__":
    main()