import numpy as np
from collections import deque
from typing import List, Optional, Tuple
import math


class TrunkAngleCalculator:
    """Kalkulátor pro výpočet úhlu ohnutí trupu z 3D pose landmarks"""
    
    def __init__(self, smoothing_window: int = 5):
        """
        Inicializace kalkulátoru
        
        Args:
            smoothing_window: Velikost okna pro temporal smoothing
        """
        self.smoothing_window = smoothing_window
        self.angle_smoother = AngleSmoothing(smoothing_window)
        
        # Landmark indexy
        self.LEFT_SHOULDER = 11
        self.RIGHT_SHOULDER = 12
        self.LEFT_HIP = 23
        self.RIGHT_HIP = 24
    
    def calculate_trunk_angle(self, landmarks_3d: List[List[float]], 
                            smooth: bool = True) -> Optional[float]:
        """
        Vypočítá úhel ohnutí trupu z 3D landmarks
        
        Args:
            landmarks_3d: List 3D koordinátů [x, y, z] pro všechny landmarks
            smooth: Zda použít temporal smoothing
            
        Returns:
            Úhel ohnutí trupu ve stupních nebo None při chybě
        """
        try:
            # Kontrola validity dat
            if not self._validate_landmarks(landmarks_3d):
                return None
            
            # Získání klíčových bodů
            left_shoulder = landmarks_3d[self.LEFT_SHOULDER]
            right_shoulder = landmarks_3d[self.RIGHT_SHOULDER]
            left_hip = landmarks_3d[self.LEFT_HIP]
            right_hip = landmarks_3d[self.RIGHT_HIP]
            
            # Výpočet středních bodů
            shoulder_midpoint = self.calculate_midpoint(left_shoulder, right_shoulder)
            hip_midpoint = self.calculate_midpoint(left_hip, right_hip)
            
            # Definice vektorů
            trunk_vector = self.calculate_vector(hip_midpoint, shoulder_midpoint)
            vertical_reference = [0, -1, 0]  # Směr vzhůru v MediaPipe souřadnicích
            
            # Výpočet úhlu
            angle = self.calculate_angle_between_vectors(trunk_vector, vertical_reference)
            
            # Temporal smoothing
            if smooth:
                angle = self.angle_smoother.smooth_angle(angle)
            
            return angle
            
        except Exception as e:
            print(f"Chyba při výpočtu úhlu trupu: {e}")
            return None
    
    def _validate_landmarks(self, landmarks_3d: List[List[float]]) -> bool:
        """
        Validuje vstupní landmark data
        
        Args:
            landmarks_3d: List 3D koordinátů
            
        Returns:
            True pokud jsou data validní
        """
        required_indices = [self.LEFT_SHOULDER, self.RIGHT_SHOULDER, 
                          self.LEFT_HIP, self.RIGHT_HIP]
        
        if len(landmarks_3d) <= max(required_indices):
            return False
        
        for idx in required_indices:
            landmark = landmarks_3d[idx]
            if len(landmark) != 3:
                return False
            if any(np.isnan(coord) or np.isinf(coord) for coord in landmark):
                return False
        
        return True
    
    def calculate_midpoint(self, point1: List[float], point2: List[float]) -> List[float]:
        """
        Vypočítá střední bod mezi dvěma 3D body
        
        Args:
            point1: První 3D bod [x, y, z]
            point2: Druhý 3D bod [x, y, z]
            
        Returns:
            Střední bod [x, y, z]
        """
        return [(point1[0] + point2[0]) / 2,
                (point1[1] + point2[1]) / 2,
                (point1[2] + point2[2]) / 2]
    
    def calculate_vector(self, point1: List[float], point2: List[float]) -> List[float]:
        """
        Vypočítá vektor od point1 k point2
        
        Args:
            point1: Výchozí bod [x, y, z]
            point2: Cílový bod [x, y, z]
            
        Returns:
            Vektor [dx, dy, dz]
        """
        return [point2[0] - point1[0], 
                point2[1] - point1[1], 
                point2[2] - point1[2]]
    
    def calculate_angle_between_vectors(self, v1: List[float], v2: List[float]) -> float:
        """
        Vypočítá úhel mezi dvěma vektory pomocí dot product
        
        Args:
            v1: První vektor [x, y, z]
            v2: Druhý vektor [x, y, z]
            
        Returns:
            Úhel ve stupních
        """
        # Normalizace vektorů
        v1_norm = np.array(v1) / np.linalg.norm(v1)
        v2_norm = np.array(v2) / np.linalg.norm(v2)
        
        # Dot product
        dot_product = np.dot(v1_norm, v2_norm)
        
        # Ošetření numerických chyb
        dot_product = np.clip(dot_product, -1.0, 1.0)
        
        # Výpočet úhlu
        angle_radians = np.arccos(dot_product)
        angle_degrees = np.degrees(angle_radians)
        
        return angle_degrees
    
    def calculate_lateral_bend_angle(self, landmarks_3d: List[List[float]]) -> Optional[float]:
        """
        Vypočítá úhel bočního ohnutí trupu (ve frontální rovině)
        
        Args:
            landmarks_3d: List 3D koordinátů
            
        Returns:
            Úhel bočního ohnutí ve stupních
        """
        try:
            if not self._validate_landmarks(landmarks_3d):
                return None
            
            left_shoulder = landmarks_3d[self.LEFT_SHOULDER]
            right_shoulder = landmarks_3d[self.RIGHT_SHOULDER]
            left_hip = landmarks_3d[self.LEFT_HIP]
            right_hip = landmarks_3d[self.RIGHT_HIP]
            
            # Vektor ramen
            shoulder_vector = self.calculate_vector(left_shoulder, right_shoulder)
            # Vektor boků
            hip_vector = self.calculate_vector(left_hip, right_hip)
            
            # Projekce do frontální roviny (ignorujeme Z souřadnici)
            shoulder_2d = [shoulder_vector[0], shoulder_vector[1]]
            hip_2d = [hip_vector[0], hip_vector[1]]
            
            # Referenční horizontální vektor
            horizontal_ref = [1, 0]
            
            # Úhly k horizontále
            shoulder_angle = self.calculate_2d_angle(shoulder_2d, horizontal_ref)
            hip_angle = self.calculate_2d_angle(hip_2d, horizontal_ref)
            
            # Rozdíl úhlů = míra bočního ohnutí
            lateral_bend = abs(shoulder_angle - hip_angle)
            
            return lateral_bend
            
        except Exception:
            return None
    
    def calculate_2d_angle(self, vector: List[float], reference: List[float]) -> float:
        """
        Vypočítá úhel 2D vektoru vůči referenčnímu vektoru
        
        Args:
            vector: 2D vektor [x, y]
            reference: Referenční 2D vektor [x, y]
            
        Returns:
            Úhel ve stupních
        """
        dot_product = np.dot(vector, reference)
        norms = np.linalg.norm(vector) * np.linalg.norm(reference)
        
        if norms == 0:
            return 0.0
        
        cos_angle = dot_product / norms
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        return np.degrees(np.arccos(cos_angle))
    
    def reset_smoothing(self):
        """Reset temporal smoothing"""
        self.angle_smoother = AngleSmoothing(self.smoothing_window)


class AngleSmoothing:
    """Třída pro temporal smoothing úhlů"""
    
    def __init__(self, window_size: int = 5):
        """
        Inicializace smoothingu
        
        Args:
            window_size: Velikost okna pro průměrování
        """
        self.window_size = window_size
        self.angle_history = deque(maxlen=window_size)
    
    def smooth_angle(self, new_angle: float) -> float:
        """
        Aplikuje temporal smoothing na nový úhel
        
        Args:
            new_angle: Nový úhel k vyhlazení
            
        Returns:
            Vyhlazený úhel
        """
        # Outlier detection - pokud je úhel příliš odlišný, nepoužijeme ho
        if len(self.angle_history) > 0:
            recent_mean = np.mean(list(self.angle_history))
            if abs(new_angle - recent_mean) > 30:  # Threshold pro outlier
                # Použijeme předchozí průměr místo outlier hodnoty
                new_angle = recent_mean
        
        self.angle_history.append(new_angle)
        
        # Vážený průměr - novější hodnoty mají větší váhu
        if len(self.angle_history) == 1:
            return new_angle
        
        weights = np.linspace(0.5, 1.0, len(self.angle_history))
        weighted_sum = np.sum(np.array(list(self.angle_history)) * weights)
        weight_sum = np.sum(weights)
        
        return weighted_sum / weight_sum
    
    def reset(self):
        """Reset historie úhlů"""
        self.angle_history.clear()


class TrunkBendAnalyzer:
    """Analyzér pro detekci a klasifikaci ohnutí trupu"""
    
    def __init__(self, bend_threshold: float = 60.0):
        """
        Inicializace analyzéru
        
        Args:
            bend_threshold: Práh pro detekci ohnutí ve stupních
        """
        self.bend_threshold = bend_threshold
        self.bend_history = []
        self.total_frames = 0
        self.bend_frames = 0
    
    def analyze_bend(self, trunk_angle: float) -> dict:
        """
        Analyzuje ohnutí trupu pro daný úhel
        
        Args:
            trunk_angle: Úhel trupu ve stupních
            
        Returns:
            Dictionary s výsledky analýzy
        """
        self.total_frames += 1
        self.bend_history.append(trunk_angle)
        
        is_bent = trunk_angle > self.bend_threshold
        if is_bent:
            self.bend_frames += 1
        
        bend_severity = self._classify_bend_severity(trunk_angle)
        
        return {
            'angle': trunk_angle,
            'is_bent': is_bent,
            'severity': bend_severity,
            'bend_percentage': (self.bend_frames / self.total_frames) * 100,
            'frame_number': self.total_frames
        }
    
    def _classify_bend_severity(self, angle: float) -> str:
        """
        Klasifikuje závažnost ohnutí
        
        Args:
            angle: Úhel trupu ve stupních
            
        Returns:
            Textová klasifikace závažnosti
        """
        if angle < 30:
            return "Vzpřímený"
        elif angle < 45:
            return "Mírné ohnutí"
        elif angle < 60:
            return "Střední ohnutí"
        elif angle < 75:
            return "Výrazné ohnutí"
        else:
            return "Extrémní ohnutí"
    
    def get_statistics(self) -> dict:
        """
        Vrací celkové statistiky analýzy
        
        Returns:
            Dictionary se statistikami
        """
        if not self.bend_history:
            return {}
        
        return {
            'total_frames': self.total_frames,
            'bend_frames': self.bend_frames,
            'bend_percentage': (self.bend_frames / self.total_frames) * 100,
            'average_angle': np.mean(self.bend_history),
            'max_angle': np.max(self.bend_history),
            'min_angle': np.min(self.bend_history),
            'std_angle': np.std(self.bend_history)
        }