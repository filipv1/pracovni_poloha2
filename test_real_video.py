# -*- coding: utf-8 -*-
"""
Test s realnym videem
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.trunk_analyzer import TrunkAnalysisProcessor
from src.utils import get_video_info, validate_video_file


def test_with_real_video():
    """Test s realnym nahranym videem"""
    print("=== Test s realnym videem ===")
    
    input_path = "../input_video.mp4"
    output_path = "data/output/analyzed_real_video.mp4"
    
    # Kontrola existence vstupniho videa
    if not os.path.exists(input_path):
        print(f"- Vstupni video neexistuje: {input_path}")
        return False
    
    print(f"+ Nalezeno vstupni video: {input_path}")
    
    # Validace vstupniho videa
    is_valid, message = validate_video_file(input_path)
    if not is_valid:
        print(f"- Video neni validni: {message}")
        return False
    
    print(f"+ Video je validni")
    
    # Info o videu
    info = get_video_info(input_path)
    if info:
        print(f"Video informace:")
        print(f"  - Rozliseni: {info['width']}x{info['height']}")
        print(f"  - FPS: {info['fps']}")
        print(f"  - Delka: {info['duration']:.1f}s")
        print(f"  - Snimky: {info['frame_count']}")
        print(f"  - Velikost: {info['size_mb']:.1f} MB")
    
    # Zajisteni existence vystupniho adresare
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Vytvoreni procesoru
        processor = TrunkAnalysisProcessor(
            input_path=input_path,
            output_path=output_path,
            model_complexity=1,
            min_detection_confidence=0.5,
            bend_threshold=60.0,
            smoothing_window=5
        )
        
        print(f"+ Procesor inicializovan")
        print(f"  - Vstup: {input_path}")
        print(f"  - Vystup: {output_path}")
        
        # Spusteni analyzy
        print("\nSpoustim analyzu...")
        results = processor.process_video(show_progress=True)
        
        # Kontrola vysledku
        if os.path.exists(output_path):
            print(f"\n+ Vystupni video vytvoreno: {output_path}")
            
            # Validace vystupniho videa
            is_valid, message = validate_video_file(output_path)
            if is_valid:
                print(f"+ Vystupni video je validni")
            else:
                print(f"- Vystupni video neni validni: {message}")
                return False
        else:
            print(f"- Vystupni video nebylo vytvoreno")
            return False
        
        # Kontrola statistik
        if 'processing_stats' in results:
            stats = results['processing_stats']
            print(f"\n+ Statistiky zpracovani:")
            print(f"  - Celkem snimku: {stats['total_frames']}")
            print(f"  - Zpracovane snimky: {stats['processed_frames']}")
            print(f"  - Neuspesne detekce: {stats['failed_detections']}")
            
            if 'success_rate' in results:
                success_rate = results['success_rate']
                print(f"  - Uspesnost: {success_rate:.1f}%")
                
                if success_rate < 50:
                    print(f"  VAROVANI: Niska uspesnost detekce!")
        
        # Kontrola bend analyzy
        if 'bend_analysis' in results and results['bend_analysis']:
            bend_stats = results['bend_analysis']
            print(f"\n+ Analyza ohnuti:")
            print(f"  - Procento ohnuti: {bend_stats['bend_percentage']:.2f}%")
            print(f"  - Prumerne uhel: {bend_stats['average_angle']:.2f}°")
            print(f"  - Max uhel: {bend_stats['max_angle']:.2f}°")
            print(f"  - Min uhel: {bend_stats['min_angle']:.2f}°")
            
            # Vyhodnoceni vysledku
            if bend_stats['bend_percentage'] > 10:
                print(f"  POZORNOST: Vysoke procento ohnuti trupu!")
        else:
            print(f"- Nebyla vygenerovana analyza ohnuti")
        
        return True
        
    except Exception as e:
        print(f"- Chyba behem analyzy: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Hlavni testovaci funkce"""
    print("TRUNK ANALYSIS - TEST S REALNYM VIDEEM")
    print("=" * 50)
    
    success = test_with_real_video()
    
    print("\n" + "=" * 50)
    if success:
        print("+ ANALYZA USPESNE DOKONCENA!")
        print("\nVystupni soubory:")
        print("- data/output/analyzed_real_video.mp4 (video s analyzou)")
        print("- data/output/analyzed_real_video.txt (textovy report)")
    else:
        print("- ANALYZA SELHALA!")
    print("=" * 50)


if __name__ == "__main__":
    main()