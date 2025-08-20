import cv2
import mediapipe as mp
import numpy as np
from typing import List, Optional, Tuple
import math


class SkeletonVisualizer:
    """Vizualizér pro vykreslování 3D skeletu a pose landmarks"""
    
    def __init__(self):
        """Inicializace vizualizéru"""
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Konfigurace stylů pro vykreslování
        self.landmark_drawing_spec = mp.solutions.drawing_utils.DrawingSpec(
            color=(0, 255, 0),  # Zelená pro landmarks
            thickness=3,
            circle_radius=3
        )
        
        self.connection_drawing_spec = mp.solutions.drawing_utils.DrawingSpec(
            color=(255, 100, 0),  # Oranžová pro connections
            thickness=2
        )
        
        # Speciální styl pro trunk landmarks
        self.trunk_landmark_spec = mp.solutions.drawing_utils.DrawingSpec(
            color=(0, 0, 255),  # Červená pro klíčové body trupu
            thickness=4,
            circle_radius=5
        )
        
        # Trunk landmark indexy
        self.TRUNK_LANDMARKS = {11, 12, 23, 24}  # Ramena a boky
        
        # Definice barev pro depth visualization
        self.depth_colors = [
            (255, 0, 0),    # Červená - nejblíže
            (255, 127, 0),  # Oranžová
            (255, 255, 0),  # Žlutá
            (127, 255, 0),  # Světle zelená
            (0, 255, 0),    # Zelená
            (0, 255, 127),  # Tyrkysová
            (0, 255, 255),  # Cyan
            (0, 127, 255),  # Světle modrá
            (0, 0, 255),    # Modrá - nejdále
        ]
    
    def draw_skeleton(self, frame: np.ndarray, 
                     pose_landmarks, 
                     pose_world_landmarks: Optional[List[List[float]]] = None,
                     highlight_trunk: bool = True) -> np.ndarray:
        """
        Vykreslí skeleton na daný frame
        
        Args:
            frame: Vstupní obrázek
            pose_landmarks: MediaPipe 2D landmarks
            pose_world_landmarks: 3D world landmarks pro depth visualization
            highlight_trunk: Zda zvýraznit trunk landmarks
            
        Returns:
            Frame s vykresleným skeletonem
        """
        if not pose_landmarks:
            return frame
        
        frame_copy = frame.copy()
        
        # Základní skeleton
        self.mp_drawing.draw_landmarks(
            frame_copy,
            pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            self.landmark_drawing_spec,
            self.connection_drawing_spec
        )
        
        # Zvýraznění trunk landmarks
        if highlight_trunk:
            self._highlight_trunk_landmarks(frame_copy, pose_landmarks)
        
        # 3D depth visualization
        if pose_world_landmarks:
            self._add_depth_visualization(frame_copy, pose_landmarks, pose_world_landmarks)
        
        return frame_copy
    
    def _highlight_trunk_landmarks(self, frame: np.ndarray, pose_landmarks):
        """
        Zvýrazní klíčové landmarks pro trunk analysis
        
        Args:
            frame: Frame pro vykreslení
            pose_landmarks: MediaPipe landmarks
        """
        h, w = frame.shape[:2]
        
        for idx in self.TRUNK_LANDMARKS:
            if idx < len(pose_landmarks.landmark):
                landmark = pose_landmarks.landmark[idx]
                
                # Konverze na pixel koordináty
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                
                # Vykreslení většího kruhu pro trunk landmarks
                cv2.circle(frame, (x, y), 8, (0, 0, 255), -1)
                cv2.circle(frame, (x, y), 10, (255, 255, 255), 2)
    
    def _add_depth_visualization(self, frame: np.ndarray, 
                                pose_landmarks, 
                                pose_world_landmarks: List[List[float]]):
        """
        Přidá indikátory hloubky pomocí barev
        
        Args:
            frame: Frame pro vykreslení
            pose_landmarks: 2D landmarks
            pose_world_landmarks: 3D world landmarks
        """
        if len(pose_world_landmarks) != len(pose_landmarks.landmark):
            return
        
        # Normalizace Z koordinát pro color mapping
        z_coords = [landmark[2] for landmark in pose_world_landmarks]
        z_min, z_max = min(z_coords), max(z_coords)
        z_range = z_max - z_min if z_max != z_min else 1
        
        h, w = frame.shape[:2]
        
        for i, (landmark_2d, landmark_3d) in enumerate(zip(pose_landmarks.landmark, pose_world_landmarks)):
            # Normalizace Z hodnoty na 0-1
            z_normalized = (landmark_3d[2] - z_min) / z_range
            
            # Mapování na barvy
            color_idx = int(z_normalized * (len(self.depth_colors) - 1))
            color = self.depth_colors[color_idx]
            
            # Vykreslení malého indikátoru hloubky
            x = int(landmark_2d.x * w)
            y = int(landmark_2d.y * h)
            
            cv2.circle(frame, (x + 15, y - 15), 3, color, -1)
    
    def draw_trunk_vector(self, frame: np.ndarray, 
                         pose_landmarks,
                         pose_world_landmarks: List[List[float]],
                         trunk_angle: float) -> np.ndarray:
        """
        Vykreslí vektor trupu a jeho úhel
        
        Args:
            frame: Vstupní frame
            pose_landmarks: 2D landmarks
            pose_world_landmarks: 3D landmarks
            trunk_angle: Úhel trupu ve stupních
            
        Returns:
            Frame s vykresleným trunk vektorem
        """
        if not pose_landmarks or not pose_world_landmarks:
            return frame
        
        frame_copy = frame.copy()
        h, w = frame.shape[:2]
        
        try:
            # Získání 2D koordinátů pro trunk landmarks
            left_shoulder = pose_landmarks.landmark[11]
            right_shoulder = pose_landmarks.landmark[12]
            left_hip = pose_landmarks.landmark[23]
            right_hip = pose_landmarks.landmark[24]
            
            # Výpočet středních bodů v 2D
            shoulder_mid_x = int((left_shoulder.x + right_shoulder.x) / 2 * w)
            shoulder_mid_y = int((left_shoulder.y + right_shoulder.y) / 2 * h)
            
            hip_mid_x = int((left_hip.x + right_hip.x) / 2 * w)
            hip_mid_y = int((left_hip.y + right_hip.y) / 2 * h)
            
            # Vykreslení trunk vektoru
            cv2.line(frame_copy, (hip_mid_x, hip_mid_y), 
                    (shoulder_mid_x, shoulder_mid_y), (255, 0, 255), 4)
            
            # Vykreslení referenční vertikální čáry
            ref_start_y = hip_mid_y
            ref_end_y = ref_start_y - 100
            cv2.line(frame_copy, (hip_mid_x, ref_start_y), 
                    (hip_mid_x, ref_end_y), (0, 255, 255), 2)
            
            # Vykreslení úhlu
            self._draw_angle_arc(frame_copy, (hip_mid_x, hip_mid_y), 
                               (hip_mid_x, ref_end_y), 
                               (shoulder_mid_x, shoulder_mid_y), 
                               trunk_angle)
            
        except (IndexError, AttributeError):
            pass
        
        return frame_copy
    
    def _draw_angle_arc(self, frame: np.ndarray, 
                       center: Tuple[int, int],
                       ref_point: Tuple[int, int],
                       trunk_point: Tuple[int, int],
                       angle: float):
        """
        Vykreslí oblouk znázorňující úhel
        
        Args:
            frame: Frame pro vykreslení
            center: Střed oblouku
            ref_point: Referenční bod (vertikála)
            trunk_point: Koncový bod trunk vektoru
            angle: Úhel ve stupních
        """
        # Výpočet úhlů pro oblouk
        ref_angle = math.degrees(math.atan2(ref_point[1] - center[1], 
                                          ref_point[0] - center[0]))
        trunk_angle_rad = math.degrees(math.atan2(trunk_point[1] - center[1], 
                                                trunk_point[0] - center[0]))
        
        # Normalizace úhlů
        if ref_angle < 0:
            ref_angle += 360
        if trunk_angle_rad < 0:
            trunk_angle_rad += 360
        
        # Vykreslení oblouku
        radius = 50
        start_angle = int(min(ref_angle, trunk_angle_rad))
        end_angle = int(max(ref_angle, trunk_angle_rad))
        
        # Elipse pro oblouk
        cv2.ellipse(frame, center, (radius, radius), 0, 
                   start_angle, end_angle, (255, 255, 0), 2)


class AngleDisplay:
    """Třída pro zobrazování úhlů a statistik na obrazovce"""
    
    def __init__(self):
        """Inicializace display komponenty"""
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.8
        self.thickness = 2
        
        # Barvy pro různé úrovně ohnutí
        self.colors = {
            'normal': (0, 255, 0),      # Zelená
            'warning': (0, 255, 255),   # Žlutá
            'danger': (0, 0, 255)       # Červená
        }
    
    def draw_angle_info(self, frame: np.ndarray, 
                       trunk_angle: float,
                       frame_number: int,
                       bend_threshold: float = 60.0,
                       additional_stats: dict = None) -> np.ndarray:
        """
        Vykreslí informace o úhlu na frame
        
        Args:
            frame: Vstupní frame
            trunk_angle: Úhel trupu ve stupních
            frame_number: Číslo aktuálního snímku
            bend_threshold: Práh pro detekci ohnutí
            additional_stats: Dodatečné statistiky k zobrazení
            
        Returns:
            Frame s informacemi o úhlu
        """
        frame_copy = frame.copy()
        
        # Určení barvy podle závažnosti ohnutí
        if trunk_angle < 30:
            color = self.colors['normal']
            status = "VZPŘÍMENÝ"
        elif trunk_angle < bend_threshold:
            color = self.colors['warning']
            status = "OHNUTÍ"
        else:
            color = self.colors['danger']
            status = "VYSOKÉ OHNUTÍ!"
        
        # Hlavní informace o úhlu
        angle_text = f"Úhel trupu: {trunk_angle:.1f}°"
        cv2.putText(frame_copy, angle_text, (10, 30), 
                   self.font, self.font_scale, color, self.thickness)
        
        # Status text
        cv2.putText(frame_copy, status, (10, 60), 
                   self.font, self.font_scale * 0.8, color, self.thickness)
        
        # Frame number
        frame_text = f"Snímek: {frame_number}"
        cv2.putText(frame_copy, frame_text, (10, frame.shape[0] - 50), 
                   self.font, 0.6, (255, 255, 255), 1)
        
        # Threshold indikátor
        threshold_text = f"Práh: {bend_threshold}°"
        cv2.putText(frame_copy, threshold_text, (10, frame.shape[0] - 25), 
                   self.font, 0.6, (200, 200, 200), 1)
        
        # Dodatečné statistiky
        if additional_stats:
            self._draw_statistics(frame_copy, additional_stats)
        
        # Úhloměr
        self._draw_angle_meter(frame_copy, trunk_angle, bend_threshold)
        
        return frame_copy
    
    def _draw_statistics(self, frame: np.ndarray, stats: dict):
        """
        Vykreslí dodatečné statistiky
        
        Args:
            frame: Frame pro vykreslení
            stats: Dictionary se statistikami
        """
        start_y = 100
        line_height = 25
        
        if 'bend_percentage' in stats:
            text = f"Ohnutí: {stats['bend_percentage']:.1f}%"
            cv2.putText(frame, text, (10, start_y), 
                       self.font, 0.6, (255, 255, 255), 1)
            start_y += line_height
        
        if 'severity' in stats:
            text = f"Závažnost: {stats['severity']}"
            cv2.putText(frame, text, (10, start_y), 
                       self.font, 0.6, (255, 255, 255), 1)
    
    def _draw_angle_meter(self, frame: np.ndarray, 
                         current_angle: float, 
                         threshold: float):
        """
        Vykreslí vizuální úhloměr
        
        Args:
            frame: Frame pro vykreslení
            current_angle: Aktuální úhel
            threshold: Práh pro ohnutí
        """
        # Pozice úhloměru
        center_x = frame.shape[1] - 120
        center_y = 80
        radius = 50
        
        # Pozadí úhloměru
        cv2.circle(frame, (center_x, center_y), radius + 5, (50, 50, 50), -1)
        cv2.circle(frame, (center_x, center_y), radius, (0, 0, 0), -1)
        
        # Škála úhloměru (0-90 stupňů)
        max_angle = 90
        angle_range = max_angle
        
        # Threshold indikátor
        threshold_angle_pos = int((threshold / angle_range) * 180)
        threshold_x = center_x + int(radius * 0.8 * math.cos(math.radians(180 - threshold_angle_pos)))
        threshold_y = center_y - int(radius * 0.8 * math.sin(math.radians(180 - threshold_angle_pos)))
        cv2.line(frame, (center_x, center_y), (threshold_x, threshold_y), (0, 255, 255), 2)
        
        # Aktuální úhel indikátor
        current_angle_clamped = min(current_angle, max_angle)
        current_angle_pos = int((current_angle_clamped / angle_range) * 180)
        current_x = center_x + int(radius * 0.9 * math.cos(math.radians(180 - current_angle_pos)))
        current_y = center_y - int(radius * 0.9 * math.sin(math.radians(180 - current_angle_pos)))
        
        # Barva podle závažnosti
        if current_angle < threshold:
            meter_color = (0, 255, 0)
        else:
            meter_color = (0, 0, 255)
        
        cv2.line(frame, (center_x, center_y), (current_x, current_y), meter_color, 3)
        
        # Stupnice
        for angle in [0, 30, 60, 90]:
            angle_pos = int((angle / angle_range) * 180)
            tick_x = center_x + int(radius * math.cos(math.radians(180 - angle_pos)))
            tick_y = center_y - int(radius * math.sin(math.radians(180 - angle_pos)))
            tick_end_x = center_x + int((radius - 10) * math.cos(math.radians(180 - angle_pos)))
            tick_end_y = center_y - int((radius - 10) * math.sin(math.radians(180 - angle_pos)))
            cv2.line(frame, (tick_x, tick_y), (tick_end_x, tick_end_y), (255, 255, 255), 1)
        
        # Hodnota úhlu ve středu
        angle_text = f"{current_angle:.0f}°"
        text_size = cv2.getTextSize(angle_text, self.font, 0.5, 1)[0]
        text_x = center_x - text_size[0] // 2
        text_y = center_y + text_size[1] // 2
        cv2.putText(frame, angle_text, (text_x, text_y), self.font, 0.5, (255, 255, 255), 1)