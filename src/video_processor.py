import cv2
import numpy as np
from typing import Generator, Tuple, Optional


class VideoInputHandler:
    """Handler pro načítání a zpracování MP4 souborů"""
    
    def __init__(self, video_path: str):
        """
        Inicializace handleru pro vstupní video
        
        Args:
            video_path: Cesta k MP4 souboru
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Nelze otevřít video soubor: {video_path}")
    
    def get_frame_info(self) -> dict:
        """
        Získání metadat o videu
        
        Returns:
            Dictionary s informacemi o videu
        """
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        return {
            'fps': fps,
            'width': width,
            'height': height,
            'frame_count': frame_count,
            'duration': frame_count / fps if fps > 0 else 0
        }
    
    def read_frames(self) -> Generator[np.ndarray, None, None]:
        """
        Generator pro čtení snímků frame-by-frame
        
        Yields:
            numpy array reprezentující snímek
        """
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            yield frame
    
    def read_frame_at_position(self, frame_number: int) -> Optional[np.ndarray]:
        """
        Načte konkrétní snímek na dané pozici
        
        Args:
            frame_number: Číslo snímku
            
        Returns:
            numpy array reprezentující snímek nebo None pokud se nepodařilo načíst
        """
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        return frame if ret else None
    
    def reset(self):
        """Reset video na začátek"""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    def __del__(self):
        """Cleanup při destrukci objektu"""
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()


class VideoOutputHandler:
    """Handler pro vytváření výstupního MP4 souboru"""
    
    def __init__(self, output_path: str, fps: float, width: int, height: int, 
                 fourcc: str = 'mp4v'):
        """
        Inicializace handleru pro výstupní video
        
        Args:
            output_path: Cesta k výstupnímu MP4 souboru
            fps: Snímková frekvence
            width: Šířka videa
            height: Výška videa
            fourcc: Kodek (výchozí mp4v)
        """
        self.output_path = output_path
        self.fps = fps
        self.width = width
        self.height = height
        
        # Nastavení kodeku
        fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
        
        # Vytvoření VideoWriter objektu
        self.writer = cv2.VideoWriter(
            output_path, 
            fourcc_code, 
            fps, 
            (width, height)
        )
        
        if not self.writer.isOpened():
            raise ValueError(f"Nelze vytvořit výstupní video soubor: {output_path}")
    
    def write_frame(self, frame: np.ndarray):
        """
        Zapíše jeden snímek do výstupního videa
        
        Args:
            frame: numpy array reprezentující snímek
        """
        # Ujistíme se, že má frame správné rozměry
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        
        self.writer.write(frame)
    
    def finalize(self):
        """Dokončí a uzavře video soubor"""
        if self.writer:
            self.writer.release()
    
    def __del__(self):
        """Cleanup při destrukci objektu"""
        if hasattr(self, 'writer') and self.writer:
            self.writer.release()