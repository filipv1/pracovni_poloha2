import csv
import os
from pathlib import Path
from typing import Optional, TextIO
import logging


class TrunkAngleCSVExporter:
    """Třída pro export dat o úhlech trupu do CSV formátu"""
    
    def __init__(self, csv_path: str, video_fps: float = 25.0):
        """
        Inicializace CSV exportéru
        
        Args:
            csv_path: Cesta k CSV souboru
            video_fps: FPS videa pro výpočet času
        """
        self.csv_path = csv_path
        self.video_fps = video_fps
        self.csv_file: Optional[TextIO] = None
        self.csv_writer: Optional[csv.writer] = None
        self.is_initialized = False
        self.exported_count = 0
        self.last_frame_number = 0  # Sledování posledního zpracovaného framu
        
        # Nastavení loggeru
        self.logger = logging.getLogger('CSVExporter')
        
        # Vytvoření výstupního adresáře pokud neexistuje
        csv_dir = os.path.dirname(csv_path)
        if csv_dir:  # Pouze pokud adresář není prázdný (relativní cesta)
            os.makedirs(csv_dir, exist_ok=True)
    
    def initialize(self):
        """
        Inicializuje CSV soubor a zapíše hlavičku
        
        Raises:
            IOError: Při chybě vytváření souboru
        """
        try:
            self.csv_file = open(self.csv_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Zápis hlavičky
            self.csv_writer.writerow(['frame', 'úhel_trupu'])
            self.csv_file.flush()
            
            self.is_initialized = True
            self.logger.info(f"CSV export inicializován: {self.csv_path}")
            
        except Exception as e:
            self.logger.error(f"Chyba při inicializaci CSV souboru: {e}")
            raise IOError(f"Nelze vytvořit CSV soubor: {self.csv_path}") from e
    
    def export_frame_data(self, frame_number: int, trunk_angle: Optional[float]):
        """
        Exportuje data jednoho snímku do CSV
        
        Args:
            frame_number: Číslo snímku
            trunk_angle: Úhel trupu ve stupních nebo None pokud nebyl detekován
        """
        if not self.is_initialized:
            self.initialize()
        
        if self.csv_writer is None:
            self.logger.error("CSV writer není inicializován")
            return
        
        try:
            # Vyplnění chybějících framů s FALSE
            self._fill_missing_frames(frame_number)
            
            # Zápis aktuálního framu
            if trunk_angle is not None:
                self.csv_writer.writerow([frame_number, f"{trunk_angle:.2f}"])
            else:
                self.csv_writer.writerow([frame_number, "FALSE"])
            
            self.last_frame_number = frame_number
            self.exported_count += 1
            
            # Periodické flush pro zajištění zápisu na disk
            if self.exported_count % 100 == 0:
                self.csv_file.flush()
                
        except Exception as e:
            self.logger.error(f"Chyba při zápisu dat snímku {frame_number}: {e}")
    
    def _fill_missing_frames(self, current_frame: int):
        """
        Vyplní chybějící framy mezi posledním a aktuálním framem hodnotou FALSE
        
        Args:
            current_frame: Číslo aktuálního framu
        """
        if self.csv_writer is None:
            return
            
        # Vyplnění chybějících framů
        for missing_frame in range(self.last_frame_number + 1, current_frame):
            self.csv_writer.writerow([missing_frame, "FALSE"])
            self.exported_count += 1
    
    def export_frame_data_with_time(self, frame_number: int, trunk_angle: float):
        """
        Exportuje data jednoho snímku s časovým údajem do CSV
        
        Args:
            frame_number: Číslo snímku
            trunk_angle: Úhel trupu ve stupních
        """
        if not self.is_initialized:
            # Pro verzi s časem použijeme jinou hlavičku
            self._initialize_with_time()
        
        if self.csv_writer is None:
            self.logger.error("CSV writer není inicializován")
            return
        
        try:
            # Výpočet času v sekundách
            time_seconds = frame_number / self.video_fps if self.video_fps > 0 else 0
            
            # Zápis dat včetně času
            self.csv_writer.writerow([
                frame_number, 
                f"{time_seconds:.2f}", 
                f"{trunk_angle:.2f}"
            ])
            self.exported_count += 1
            
            # Periodické flush
            if self.exported_count % 100 == 0:
                self.csv_file.flush()
                
        except Exception as e:
            self.logger.error(f"Chyba při zápisu dat snímku {frame_number}: {e}")
    
    def _initialize_with_time(self):
        """
        Inicializuje CSV soubor s rozšířenou hlavičkou obsahující čas
        
        Raises:
            IOError: Při chybě vytváření souboru
        """
        try:
            self.csv_file = open(self.csv_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Zápis rozšířené hlavičky
            self.csv_writer.writerow(['frame', 'čas_s', 'úhel_trupu'])
            self.csv_file.flush()
            
            self.is_initialized = True
            self.logger.info(f"CSV export s časem inicializován: {self.csv_path}")
            
        except Exception as e:
            self.logger.error(f"Chyba při inicializaci CSV souboru s časem: {e}")
            raise IOError(f"Nelze vytvořit CSV soubor: {self.csv_path}") from e
    
    def finalize(self):
        """
        Dokončí export a uzavře soubor
        """
        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
                
                self.logger.info(f"CSV export dokončen. Exportováno {self.exported_count} záznamů do {self.csv_path}")
                
            except Exception as e:
                self.logger.error(f"Chyba při dokončování CSV souboru: {e}")
            
            finally:
                self.csv_file = None
                self.csv_writer = None
                self.is_initialized = False
    
    def get_export_statistics(self) -> dict:
        """
        Vrací statistiky exportu
        
        Returns:
            Dictionary se statistikami
        """
        return {
            'csv_path': self.csv_path,
            'exported_records': self.exported_count,
            'is_active': self.is_initialized,
            'video_fps': self.video_fps
        }
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.finalize()
    
    def __del__(self):
        """Cleanup při destrukci objektu"""
        if self.csv_file and not self.csv_file.closed:
            self.finalize()


def create_csv_path_from_video_path(video_path: str) -> str:
    """
    Vytvoří cestu k CSV souboru ze cesty k video souboru
    
    Args:
        video_path: Cesta k video souboru
        
    Returns:
        Cesta k CSV souboru se stejným názvem
    """
    video_path_obj = Path(video_path)
    return str(video_path_obj.with_suffix('.csv'))


def export_angle_history_to_csv(angles_history: list, csv_path: str, video_fps: float = 25.0):
    """
    Exportuje celou historii úhlů do CSV souboru
    
    Args:
        angles_history: Seznam úhlů trupu
        csv_path: Cesta k CSV souboru
        video_fps: FPS videa
    """
    with TrunkAngleCSVExporter(csv_path, video_fps) as exporter:
        for frame_number, angle in enumerate(angles_history, start=1):
            if angle is not None:
                exporter.export_frame_data(frame_number, angle)