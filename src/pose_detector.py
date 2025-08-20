import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, List, NamedTuple


class PoseResults(NamedTuple):
    """Struktura pro výsledky pose detection"""
    pose_landmarks: Optional[object]  # MediaPipe landmarks
    pose_world_landmarks: Optional[List]
    confidence: float


class PoseDetector:
    """Wrapper pro MediaPipe Pose detection s 3D koordinátami"""
    
    def __init__(self, 
                 model_complexity: int = 1,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 enable_segmentation: bool = False):
        """
        Inicializace MediaPipe Pose detectoru
        
        Args:
            model_complexity: 0 (lite), 1 (full), 2 (heavy)
            min_detection_confidence: Minimální confidence pro detekci
            min_tracking_confidence: Minimální confidence pro tracking
            enable_segmentation: Zapnout segmentaci pozadí
        """
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=enable_segmentation,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Důležité landmark indexy pro trunk analysis
        self.TRUNK_LANDMARKS = {
            'LEFT_SHOULDER': 11,
            'RIGHT_SHOULDER': 12,
            'LEFT_HIP': 23,
            'RIGHT_HIP': 24,
            'LEFT_ELBOW': 13,
            'RIGHT_ELBOW': 14,
            'LEFT_KNEE': 25,
            'RIGHT_KNEE': 26
        }
    
    def detect_pose(self, frame: np.ndarray) -> PoseResults:
        """
        Detekuje pózu v daném snímku
        
        Args:
            frame: RGB snímek
            
        Returns:
            PoseResults s detekovanými landmarks
        """
        # Konverze BGR na RGB pro MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detekce pózy
        results = self.pose.process(rgb_frame)
        
        # Extrakce 3D world landmarks
        world_landmarks = None
        confidence = 0.0
        
        if results.pose_world_landmarks:
            world_landmarks = self.extract_3d_landmarks(results.pose_world_landmarks)
            confidence = self.calculate_overall_confidence(results.pose_landmarks)
        
        return PoseResults(
            pose_landmarks=results.pose_landmarks,
            pose_world_landmarks=world_landmarks,
            confidence=confidence
        )
    
    def extract_3d_landmarks(self, pose_world_landmarks) -> List[List[float]]:
        """
        Extrahuje 3D world coordinates z MediaPipe results
        
        Args:
            pose_world_landmarks: MediaPipe world landmarks
            
        Returns:
            List 3D koordinátů [x, y, z] pro každý landmark
        """
        landmarks_3d = []
        
        for landmark in pose_world_landmarks.landmark:
            # MediaPipe world coordinates jsou v metrech
            landmarks_3d.append([landmark.x, landmark.y, landmark.z])
        
        return landmarks_3d
    
    def calculate_overall_confidence(self, pose_landmarks) -> float:
        """
        Vypočítá celkový confidence score pro detekci
        
        Args:
            pose_landmarks: MediaPipe pose landmarks
            
        Returns:
            Průměrný confidence score pro klíčové body trupu
        """
        if not pose_landmarks:
            return 0.0
        
        trunk_confidences = []
        
        for landmark_name in self.TRUNK_LANDMARKS:
            idx = self.TRUNK_LANDMARKS[landmark_name]
            if idx < len(pose_landmarks.landmark):
                landmark = pose_landmarks.landmark[idx]
                trunk_confidences.append(landmark.visibility)
        
        return np.mean(trunk_confidences) if trunk_confidences else 0.0
    
    def is_pose_valid(self, pose_results: PoseResults, 
                     min_confidence: float = 0.3) -> bool:
        """
        Kontroluje zda je detekovaná póza validní pro analýzu
        
        Args:
            pose_results: Výsledky pose detection
            min_confidence: Minimální required confidence
            
        Returns:
            True pokud je póza validní
        """
        if not pose_results.pose_world_landmarks:
            return False
        
        if pose_results.confidence < min_confidence:
            return False
        
        # Kontrola zda máme všechny klíčové body pro trunk analysis
        trunk_landmarks = [
            pose_results.pose_world_landmarks[self.TRUNK_LANDMARKS['LEFT_SHOULDER']],
            pose_results.pose_world_landmarks[self.TRUNK_LANDMARKS['RIGHT_SHOULDER']],
            pose_results.pose_world_landmarks[self.TRUNK_LANDMARKS['LEFT_HIP']],
            pose_results.pose_world_landmarks[self.TRUNK_LANDMARKS['RIGHT_HIP']]
        ]
        
        # Kontrola zda nejsou koordináty NaN nebo nekonečné
        for landmark in trunk_landmarks:
            if any(np.isnan(coord) or np.isinf(coord) for coord in landmark):
                return False
        
        return True
    
    def get_trunk_landmarks(self, pose_results: PoseResults) -> dict:
        """
        Extrahuje pouze klíčové landmarks pro trunk analysis
        
        Args:
            pose_results: Výsledky pose detection
            
        Returns:
            Dictionary s klíčovými 3D koordinátami
        """
        if not pose_results.pose_world_landmarks:
            return {}
        
        trunk_coords = {}
        
        for landmark_name, idx in self.TRUNK_LANDMARKS.items():
            if idx < len(pose_results.pose_world_landmarks):
                trunk_coords[landmark_name] = pose_results.pose_world_landmarks[idx]
        
        return trunk_coords
    
    def __del__(self):
        """Cleanup při destrukci objektu"""
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()