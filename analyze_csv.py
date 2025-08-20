#!/usr/bin/env python3
"""
Skript pro analýzu existujícího CSV souboru a identifikaci chybějících framů
"""

import sys
import csv
from pathlib import Path


def analyze_csv_file(csv_path: str):
    """
    Analyzuje CSV soubor a identifikuje chybějící framy
    
    Args:
        csv_path: Cesta k CSV souboru
    """
    if not Path(csv_path).exists():
        print(f"CHYBA: Soubor {csv_path} neexistuje")
        return
    
    print(f"Analyzuji CSV soubor: {csv_path}")
    print("=" * 50)
    
    frames_in_csv = []
    total_rows = 0
    false_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Přeskočíme hlavičku
            print(f"Hlavicka: {header}")
            
            for row in reader:
                if len(row) >= 2:
                    frame_num = int(row[0])
                    angle_value = row[1]
                    
                    frames_in_csv.append(frame_num)
                    total_rows += 1
                    
                    if angle_value == "FALSE":
                        false_count += 1
        
        # Analyza
        if frames_in_csv:
            min_frame = min(frames_in_csv)
            max_frame = max(frames_in_csv)
            expected_frames = set(range(min_frame, max_frame + 1))
            actual_frames = set(frames_in_csv)
            
            print(f"Rozsah framu: {min_frame} - {max_frame}")
            print(f"Ocekavany pocet framu: {len(expected_frames)}")
            print(f"Skutecny pocet radku: {total_rows}")
            print(f"Pocet FALSE hodnot: {false_count}")
            print(f"Pocet uspesnych detekci: {total_rows - false_count}")
            
            # Chybejici framy
            missing_frames = expected_frames - actual_frames
            if missing_frames:
                print(f"\nCHYBEJICI FRAMY ({len(missing_frames)}):")
                missing_list = sorted(list(missing_frames))
                
                # Seskupeni consecutive framu
                groups = []
                current_group = [missing_list[0]]
                
                for i in range(1, len(missing_list)):
                    if missing_list[i] == missing_list[i-1] + 1:
                        current_group.append(missing_list[i])
                    else:
                        groups.append(current_group)
                        current_group = [missing_list[i]]
                
                groups.append(current_group)
                
                for group in groups:
                    if len(group) == 1:
                        print(f"  Frame {group[0]}")
                    else:
                        print(f"  Framy {group[0]}-{group[-1]} ({len(group)} framu)")
            else:
                print("\nOK VSECHNY FRAMY JSOU PRITOMNY!")
            
            # Procenta uspesnosti
            success_rate = ((total_rows - false_count) / total_rows) * 100
            print(f"\nUspesnost detekce: {success_rate:.1f}%")
            
        else:
            print("CHYBA: Zadna data nebyla nalezena")
    
    except Exception as e:
        print(f"CHYBA pri cteni souboru: {e}")


def main():
    """Hlavní funkce"""
    if len(sys.argv) != 2:
        print("Použití: python analyze_csv.py <cesta_k_csv>")
        print("\nPříklad:")
        print("python analyze_csv.py data/output/final3.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    analyze_csv_file(csv_path)


if __name__ == "__main__":
    main()