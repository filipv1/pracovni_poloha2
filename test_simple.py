# -*- coding: utf-8 -*-
"""
Jednoduchy test
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.trunk_analyzer import TrunkAnalysisProcessor


def main():
    """Jednoduchy test s realnym videem"""
    print("TRUNK ANALYSIS - TEST")
    print("=" * 30)
    
    input_path = "../input_video.mp4"
    output_path = "data/output/result.mp4"
    
    # Zajisteni adresare
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
        
        print("Procesor vytvoren - spoustim analyzu...")
        
        # Spusteni analyzy BEZ progress baru
        results = processor.process_video(show_progress=False)
        
        print("\nANALYZA DOKONCENA!")
        print(f"Vystupni video: {output_path}")
        
        # Jednoduche statistiky
        if 'processing_stats' in results:
            stats = results['processing_stats']
            print(f"Zpracovano snimku: {stats['processed_frames']}/{stats['total_frames']}")
            
        if 'bend_analysis' in results and results['bend_analysis']:
            bend = results['bend_analysis']
            print(f"Procento ohnuti: {bend['bend_percentage']:.1f}%")
            print(f"Prumerne ohnuti: {bend['average_angle']:.1f} stupnu")
            print(f"Maximalni ohnuti: {bend['max_angle']:.1f} stupnu")
        
        return True
        
    except Exception as e:
        print(f"CHYBA: {e}")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n+ USPECH!")
    else:
        print("\n- CHYBA!")