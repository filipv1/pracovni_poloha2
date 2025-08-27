#!/usr/bin/env python3
"""
Hlavní entry point pro aplikaci Trunk Analysis
Analyzuje MP4 video a detekuje ohnutí trupu pomocí MediaPipe 3D pose estimation
"""

import argparse
import sys
import os
import traceback
from pathlib import Path

# Přidání src do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.trunk_analyzer import TrunkAnalysisProcessor


def parse_arguments():
    """
    Parsování command line argumentů
    
    Returns:
        Parsed arguments object
    """
    parser = argparse.ArgumentParser(
        description='Trunk Bend Analysis - Analyza ohnuti trupu pomoci MediaPipe',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Priklady pouziti:
  %(prog)s input.mp4 output.mp4
  %(prog)s video.mp4 result.mp4 --model-complexity 2 --threshold 45
  %(prog)s input.mp4 output.mp4 --confidence 0.7 --smoothing 10
  %(prog)s input.mp4 output.mp4 --csv-export
        """
    )
    
    # Povinné argumenty
    parser.add_argument(
        'input', 
        help='Cesta ke vstupnimu MP4 souboru'
    )
    
    parser.add_argument(
        'output', 
        help='Cesta k vystupnimu MP4 souboru s analyzou'
    )
    
    # Volitelné argumenty
    parser.add_argument(
        '--model-complexity', 
        type=int, 
        default=1, 
        choices=[0, 1, 2],
        help='Slozitost MediaPipe modelu: 0=lite, 1=full (vychozi), 2=heavy'
    )
    
    parser.add_argument(
        '--threshold', '--angle-threshold',
        dest='angle_threshold',
        type=float, 
        default=60.0,
        help='Prah uhlu pro detekci ohnuti trupu ve stupnich (vychozi: 60.0)'
    )
    
    parser.add_argument(
        '--confidence', '--min-detection-confidence',
        dest='min_detection_confidence',
        type=float, 
        default=0.5,
        help='Minimalni confidence pro pose detection (0.0-1.0, vychozi: 0.5)'
    )
    
    parser.add_argument(
        '--smoothing', '--smoothing-window',
        dest='smoothing_window',
        type=int, 
        default=5,
        help='Velikost okna pro temporal smoothing uhlu (vychozi: 5)'
    )
    
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Nezobrazovat progress bar behem zpracovani'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output (detailni logovani)'
    )
    
    parser.add_argument(
        '--csv-export',
        action='store_true',
        help='Export dat do CSV souboru (frame,úhel_trupu)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Trunk Analysis v1.0.0'
    )
    
    return parser.parse_args()


def validate_arguments(args):
    """
    Validace argumentů
    
    Args:
        args: Parsed arguments
        
    Raises:
        SystemExit: Při nevalidních argumentech
    """
    # Kontrola vstupního souboru
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"CHYBA: Vstupní soubor neexistuje: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    if not input_path.is_file():
        print(f"CHYBA: Vstupní cesta není soubor: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Kontrola přípony vstupního souboru
    if input_path.suffix.lower() not in ['.mp4', '.avi', '.mov', '.mkv']:
        print(f"VAROVÁNÍ: Nerozpoznaná přípona video souboru: {input_path.suffix}")
    
    # Kontrola výstupní cesty
    output_path = Path(args.output)
    output_dir = output_path.parent
    
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"CHYBA: Nelze vytvořit výstupní adresář {output_dir}: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Validace číselných argumentů
    if not 0.0 <= args.min_detection_confidence <= 1.0:
        print(f"CHYBA: confidence musí být mezi 0.0 a 1.0, zadáno: {args.min_detection_confidence}", 
              file=sys.stderr)
        sys.exit(1)
    
    if args.angle_threshold < 0 or args.angle_threshold > 180:
        print(f"CHYBA: threshold musí být mezi 0 a 180 stupni, zadáno: {args.angle_threshold}", 
              file=sys.stderr)
        sys.exit(1)
    
    if args.smoothing_window < 1:
        print(f"CHYBA: smoothing window musí být alespoň 1, zadáno: {args.smoothing_window}", 
              file=sys.stderr)
        sys.exit(1)


def setup_logging(verbose: bool):
    """
    Nastavení úrovně logování
    
    Args:
        verbose: Zda použít verbose logging
    """
    import logging
    
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def print_configuration(args):
    """
    Vytiskne konfiguraci před spuštěním
    
    Args:
        args: Parsed arguments
    """
    print("Trunk Analysis - Konfigurace:")
    print(f"  Vstupní soubor: {args.input}")
    print(f"  Výstupní soubor: {args.output}")
    print(f"  Model complexity: {args.model_complexity}")
    print(f"  Detection confidence: {args.min_detection_confidence}")
    print(f"  Angle threshold: {args.angle_threshold}°")
    print(f"  Smoothing window: {args.smoothing_window}")
    print(f"  CSV export: {'Povolen' if args.csv_export else 'Vypnut'}")
    print("-" * 50)


def main():
    """Hlavní funkce aplikace"""
    try:
        # Parsování argumentů
        args = parse_arguments()
        
        # Validace
        validate_arguments(args)
        
        # Setup
        setup_logging(args.verbose)
        
        # Výpis konfigurace
        print_configuration(args)
        
        # Vytvoření procesoru
        processor = TrunkAnalysisProcessor(
            input_path=args.input,
            output_path=args.output,
            model_complexity=args.model_complexity,
            min_detection_confidence=args.min_detection_confidence,
            bend_threshold=args.angle_threshold,
            smoothing_window=args.smoothing_window,
            export_csv=args.csv_export
        )
        
        # Zobrazení informací o videu
        video_info = processor.get_video_info()
        print("\nInformace o videu:")
        print(f"  Délka: {video_info['duration']:.2f} sekund")
        print(f"  Počet snímků: {video_info['frame_count']}")
        print(f"  FPS: {video_info['fps']:.2f}")
        print("-" * 50)
        
        # Spuštění analýzy
        print("Spouštím analýzu...")
        results = processor.process_video(show_progress=not args.no_progress)
        
        print(f"\nAnalýza dokončena úspěšně!")
        print(f"Výstupní video uloženo: {args.output}")
        
        # Uložení reportu
        report_path = Path(args.output).with_suffix('.txt')
        save_report(results, report_path)
        print(f"Report uložen: {report_path}")
        
        # Informace o CSV exportu
        if args.csv_export:
            csv_path = Path(args.output).with_suffix('.csv')
            print(f"CSV data exportována: {csv_path}")
        
    except KeyboardInterrupt:
        print("\nAnalýza přerušena uživatelem", file=sys.stderr)
        sys.exit(130)
    
    except Exception as e:
        print(f"\nCHYBA: {e}", file=sys.stderr)
        
        if args.verbose if 'args' in locals() else False:
            print("\nDetaily chyby:", file=sys.stderr)
            traceback.print_exc()
        
        sys.exit(1)


def save_report(results: dict, report_path: Path):
    """
    Uloží textový report do souboru
    
    Args:
        results: Výsledky analýzy
        report_path: Cesta k report souboru
    """
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("TRUNK ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Vstupní soubor: {results['input_file']}\n")
            f.write(f"Výstupní soubor: {results['output_file']}\n\n")
            
            # Video info
            video_info = results['video_info']
            f.write("Video informace:\n")
            f.write(f"  Rozlišení: {video_info['width']}x{video_info['height']}\n")
            f.write(f"  FPS: {video_info['fps']:.1f}\n")
            f.write(f"  Délka: {video_info['duration']:.1f}s\n")
            f.write(f"  Celkem snímků: {video_info['frame_count']}\n\n")
            
            # Processing stats
            proc_stats = results['processing_stats']
            f.write("Zpracování:\n")
            f.write(f"  Zpracované snímky: {proc_stats['processed_frames']}\n")
            f.write(f"  Neúspěšné detekce: {proc_stats['failed_detections']}\n")
            f.write(f"  Úspěšnost: {results.get('success_rate', 0):.1f}%\n\n")
            
            # Bend analysis
            if 'bend_analysis' in results and results['bend_analysis']:
                bend_stats = results['bend_analysis']
                f.write("Analýza ohnutí:\n")
                f.write(f"  Snímky s ohnutím >60°: {bend_stats['bend_frames']}\n")
                f.write(f"  Procento ohnutí: {bend_stats['bend_percentage']:.2f}%\n")
                f.write(f"  Průměrný úhel: {bend_stats['average_angle']:.2f}°\n")
                f.write(f"  Maximální úhel: {bend_stats['max_angle']:.2f}°\n")
                f.write(f"  Minimální úhel: {bend_stats['min_angle']:.2f}°\n")
                f.write(f"  Směrodatná odchylka: {bend_stats['std_angle']:.2f}°\n\n")
            
            # Configuration
            config = results['configuration']
            f.write("Konfigurace:\n")
            f.write(f"  Práh ohnutí: {config['bend_threshold']}°\n")
            f.write(f"  Model complexity: {config['model_complexity']}\n")
            f.write(f"  Min detection confidence: {config['min_detection_confidence']}\n")
            
    except Exception as e:
        print(f"VAROVÁNÍ: Nepodařilo se uložit report: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()