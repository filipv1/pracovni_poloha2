"""
Utility funkce pro Trunk Analysis projekt
"""

import cv2
import numpy as np
import os
from typing import Tuple, List, Optional
import math


def create_sample_video(output_path: str, 
                       duration_seconds: int = 10,
                       fps: int = 30,
                       width: int = 640,
                       height: int = 480) -> bool:
    """
    Vytvoří ukázkové video pro testování
    
    Args:
        output_path: Cesta k výstupnímu MP4 souboru
        duration_seconds: Délka videa v sekundách
        fps: Snímková frekvence
        width: Šířka videa
        height: Výška videa
        
    Returns:
        True pokud bylo video úspěšně vytvořeno
    """
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        total_frames = duration_seconds * fps
        
        for frame_num in range(total_frames):
            # Vytvoření prázdného snímku
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Simulace pohybující se postavy
            progress = frame_num / total_frames
            
            # Pozice hlavy (pohybuje se zleva doprava)
            head_x = int(width * 0.2 + (width * 0.6) * progress)
            head_y = int(height * 0.2)
            
            # Simulace ohnutí - úhel se mění podle času
            bend_angle = abs(math.sin(progress * math.pi * 4)) * 60  # 0-60 stupňů
            
            # Výpočet pozic těla
            shoulder_y = head_y + 50
            hip_y = shoulder_y + 100
            
            # Ohnutí - posun ramene
            bend_offset = int(math.sin(math.radians(bend_angle)) * 30)
            shoulder_x = head_x + bend_offset
            
            # Vykreslení jednoduché postavy
            # Hlava
            cv2.circle(frame, (head_x, head_y), 20, (255, 255, 255), -1)
            
            # Tělo
            cv2.line(frame, (head_x, head_y + 20), (shoulder_x, shoulder_y), (255, 255, 255), 3)
            cv2.line(frame, (shoulder_x, shoulder_y), (head_x, hip_y), (255, 255, 255), 3)
            
            # Ramena
            cv2.line(frame, (shoulder_x - 30, shoulder_y), (shoulder_x + 30, shoulder_y), (255, 255, 255), 3)
            
            # Boky
            cv2.line(frame, (head_x - 20, hip_y), (head_x + 20, hip_y), (255, 255, 255), 3)
            
            # Nohy
            cv2.line(frame, (head_x - 10, hip_y), (head_x - 10, hip_y + 80), (255, 255, 255), 3)
            cv2.line(frame, (head_x + 10, hip_y), (head_x + 10, hip_y + 80), (255, 255, 255), 3)
            
            # Informace o úhlu
            cv2.putText(frame, f"Bend Angle: {bend_angle:.1f}°", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.putText(frame, f"Frame: {frame_num}", (10, height - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            writer.write(frame)
        
        writer.release()
        return True
        
    except Exception as e:
        print(f"Chyba při vytváření ukázkového videa: {e}")
        return False


def validate_video_file(video_path: str) -> Tuple[bool, str]:
    """
    Validuje video soubor
    
    Args:
        video_path: Cesta k video souboru
        
    Returns:
        Tuple (is_valid, error_message)
    """
    if not os.path.exists(video_path):
        return False, f"Soubor neexistuje: {video_path}"
    
    if not os.path.isfile(video_path):
        return False, f"Cesta není soubor: {video_path}"
    
    # Pokus o otevření videa
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return False, f"Nelze otevřít video soubor: {video_path}"
    
    # Kontrola základních parametrů
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    cap.release()
    
    if frame_count <= 0:
        return False, "Video neobsahuje žádné snímky"
    
    if fps <= 0:
        return False, "Neplatná snímková frekvence"
    
    if width <= 0 or height <= 0:
        return False, "Neplatné rozlišení videa"
    
    return True, "Video je validní"


def get_video_info(video_path: str) -> Optional[dict]:
    """
    Získá informace o video souboru
    
    Args:
        video_path: Cesta k video souboru
        
    Returns:
        Dictionary s informacemi o videu nebo None
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return None
        
        info = {
            'path': video_path,
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': 0,
            'size_mb': 0
        }
        
        # Výpočet délky
        if info['fps'] > 0:
            info['duration'] = info['frame_count'] / info['fps']
        
        # Velikost souboru
        if os.path.exists(video_path):
            info['size_mb'] = os.path.getsize(video_path) / (1024 * 1024)
        
        cap.release()
        return info
        
    except Exception:
        return None


def ensure_directory_exists(file_path: str):
    """
    Zajistí, že adresář pro daný soubor existuje
    
    Args:
        file_path: Cesta k souboru
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def calculate_distance_3d(point1: List[float], point2: List[float]) -> float:
    """
    Vypočítá 3D vzdálenost mezi dvěma body
    
    Args:
        point1: První bod [x, y, z]
        point2: Druhý bod [x, y, z]
        
    Returns:
        Vzdálenost
    """
    return math.sqrt(
        (point2[0] - point1[0])**2 + 
        (point2[1] - point1[1])**2 + 
        (point2[2] - point1[2])**2
    )


def normalize_vector(vector: List[float]) -> List[float]:
    """
    Normalizuje vektor na jednotkovou délku
    
    Args:
        vector: Vstupní vektor
        
    Returns:
        Normalizovaný vektor
    """
    magnitude = math.sqrt(sum(x**2 for x in vector))
    if magnitude == 0:
        return vector
    return [x / magnitude for x in vector]


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Omezí hodnotu na daný rozsah
    
    Args:
        value: Hodnota k omezení
        min_val: Minimální hodnota
        max_val: Maximální hodnota
        
    Returns:
        Omezená hodnota
    """
    return max(min_val, min(value, max_val))


def format_duration(seconds: float) -> str:
    """
    Formátuje délku v sekundách na čitelný formát
    
    Args:
        seconds: Délka v sekundách
        
    Returns:
        Formátovaný string (např. "1:23.45")
    """
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:06.3f}"


def save_frame_as_image(frame: np.ndarray, output_path: str) -> bool:
    """
    Uloží snímek jako obrázek
    
    Args:
        frame: Snímek k uložení
        output_path: Cesta k výstupnímu obrázku
        
    Returns:
        True pokud bylo uložení úspěšné
    """
    try:
        ensure_directory_exists(output_path)
        return cv2.imwrite(output_path, frame)
    except Exception:
        return False


class PerformanceMonitor:
    """Třída pro monitorování výkonu zpracování"""
    
    def __init__(self):
        """Inicializace monitoru"""
        self.start_time = None
        self.frame_times = []
        self.processed_frames = 0
    
    def start(self):
        """Spustí monitoring"""
        import time
        self.start_time = time.time()
        self.frame_times = []
        self.processed_frames = 0
    
    def log_frame(self):
        """Zaloguje zpracování jednoho snímku"""
        import time
        if self.start_time:
            current_time = time.time()
            self.frame_times.append(current_time)
            self.processed_frames += 1
    
    def get_stats(self) -> dict:
        """
        Získá statistiky výkonu
        
        Returns:
            Dictionary se statistikami
        """
        if not self.start_time or not self.frame_times:
            return {}
        
        import time
        total_time = time.time() - self.start_time
        
        stats = {
            'total_time': total_time,
            'processed_frames': self.processed_frames,
            'fps': self.processed_frames / total_time if total_time > 0 else 0,
            'avg_frame_time': total_time / self.processed_frames if self.processed_frames > 0 else 0
        }
        
        return stats