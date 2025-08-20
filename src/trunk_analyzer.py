import cv2
import numpy as np
from typing import Optional, Dict, List
import os
from tqdm import tqdm
import logging

from .video_processor import VideoInputHandler, VideoOutputHandler
from .pose_detector import PoseDetector, PoseResults
from .angle_calculator import TrunkAngleCalculator, TrunkBendAnalyzer
from .visualizer import SkeletonVisualizer, AngleDisplay
from .csv_exporter import TrunkAngleCSVExporter, create_csv_path_from_video_path


class TrunkAnalysisProcessor:
    """Hlavní procesor pro analýzu ohnutí trupu ve videu"""
    
    def __init__(self, 
                 input_path: str, 
                 output_path: str,
                 model_complexity: int = 1,
                 min_detection_confidence: float = 0.5,
                 bend_threshold: float = 60.0,
                 smoothing_window: int = 5,
                 export_csv: bool = False):
        """
        Inicializace procesoru
        
        Args:
            input_path: Cesta ke vstupnímu MP4 souboru
            output_path: Cesta k výstupnímu MP4 souboru
            model_complexity: Složitost MediaPipe modelu (0-2)
            min_detection_confidence: Minimální confidence pro detekci
            bend_threshold: Práh pro detekci ohnutí ve stupních
            smoothing_window: Velikost okna pro temporal smoothing
            export_csv: Zda exportovat data do CSV souboru
        """
        self.input_path = input_path
        self.output_path = output_path
        self.bend_threshold = bend_threshold
        self.export_csv = export_csv
        
        # Validace vstupního souboru
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Vstupní soubor neexistuje: {input_path}")
        
        # Vytvoření výstupního adresáře pokud neexistuje
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Inicializace komponent
        self.input_handler = VideoInputHandler(input_path)
        self.pose_detector = PoseDetector(
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence
        )
        self.angle_calculator = TrunkAngleCalculator(smoothing_window=smoothing_window)
        self.bend_analyzer = TrunkBendAnalyzer(bend_threshold=bend_threshold)
        self.visualizer = SkeletonVisualizer()
        self.angle_display = AngleDisplay()
        
        # Získání video info
        self.video_info = self.input_handler.get_frame_info()
        
        # Inicializace output handleru
        self.output_handler = VideoOutputHandler(
            output_path,
            self.video_info['fps'],
            self.video_info['width'],
            self.video_info['height']
        )
        
        # Statistiky
        self.processing_stats = {
            'total_frames': 0,
            'processed_frames': 0,
            'failed_detections': 0,
            'angles_history': [],
            'bend_frames': 0
        }
        
        # CSV Exporter inicializace
        self.csv_exporter = None
        if self.export_csv:
            csv_path = create_csv_path_from_video_path(output_path)
            self.csv_exporter = TrunkAngleCSVExporter(csv_path, self.video_info['fps'])
            self.logger = logging.getLogger('TrunkAnalyzer')
            self.logger.info(f"CSV export povolen: {csv_path}")
        
        # Logging setup
        if not hasattr(self, 'logger'):
            self.logger = self._setup_logger()
    
    def process_video(self, show_progress: bool = True) -> Dict:
        """
        Zpracuje celé video a vytvoří výstup s analýzou
        
        Args:
            show_progress: Zda zobrazit progress bar
            
        Returns:
            Dictionary s výsledky analýzy
        """
        self.logger.info(f"Spoustim analyzu videa: {self.input_path}")
        self.logger.info(f"Video info: {self.video_info}")
        
        # Diagnostika výkonu
        estimated_time = self.video_info['frame_count'] / (5 * 60)  # ~5 FPS odhad
        print(f"Video: {self.video_info['width']}x{self.video_info['height']}, {self.video_info['frame_count']} snimku")
        print(f"Odhadovany cas: {estimated_time:.1f} minut")
        
        frame_number = 0
        total_frames = self.video_info['frame_count']
        
        # Console progress tracking (místo tqdm)
        print(f"Zpracovavam {total_frames} snimku...")
        print("Progress: [", end="", flush=True)
        progress_step = max(1, total_frames // 50)  # 50 teček pro progress
        next_progress = progress_step
        
        try:
            for frame in self.input_handler.read_frames():
                frame_number += 1
                self.processing_stats['total_frames'] = frame_number
                
                # Zpracování snímku
                processed_frame = self._process_frame(frame, frame_number)
                
                # Zápis do výstupního videa
                self.output_handler.write_frame(processed_frame)
                
                # Console progress
                if frame_number >= next_progress:
                    print(".", end="", flush=True)
                    next_progress += progress_step
                
                # Periodické logování s procentem
                if frame_number % 100 == 0:
                    percent = (frame_number / total_frames) * 100
                    print(f"\n{frame_number}/{total_frames} ({percent:.1f}%)", end=" ", flush=True)
        
        except Exception as e:
            self.logger.error(f"Chyba během zpracování: {e}")
            raise
        
        finally:
            # Cleanup
            print("] DOKONCENO!", flush=True)
            
            self.output_handler.finalize()
            
            # Finalizace CSV exportu
            if self.csv_exporter is not None:
                self.csv_exporter.finalize()
                csv_stats = self.csv_exporter.get_export_statistics()
                self.logger.info(f"CSV export dokončen: {csv_stats['exported_records']} záznamů")
            
            self.logger.info("Zpracování dokončeno")
        
        # Generování finálního reportu
        final_report = self._generate_final_report()
        self.logger.info("Finální report vygenerován")
        
        return final_report
    
    def _process_frame(self, frame: np.ndarray, frame_number: int) -> np.ndarray:
        """
        Zpracuje jeden snímek
        
        Args:
            frame: Vstupní snímek
            frame_number: Číslo snímku
            
        Returns:
            Zpracovaný snímek s vizualizací
        """
        processed_frame = frame.copy()
        trunk_angle = None  # Inicializace pro CSV export
        
        # Pose detection
        pose_results = self.pose_detector.detect_pose(frame)
        
        if self.pose_detector.is_pose_valid(pose_results):
            self.processing_stats['processed_frames'] += 1
            
            # Výpočet úhlu trupu
            trunk_angle = self.angle_calculator.calculate_trunk_angle(
                pose_results.pose_world_landmarks
            )
            
            if trunk_angle is not None:
                # Analýza ohnutí
                bend_analysis = self.bend_analyzer.analyze_bend(trunk_angle)
                self.processing_stats['angles_history'].append(trunk_angle)
                
                if bend_analysis['is_bent']:
                    self.processing_stats['bend_frames'] += 1
                
                # Vizualizace
                processed_frame = self._add_visualizations(
                    processed_frame, 
                    pose_results, 
                    trunk_angle, 
                    frame_number,
                    bend_analysis
                )
                
                # Logování významných událostí
                if bend_analysis['severity'] in ["Výrazné ohnutí", "Extrémní ohnutí"]:
                    self.logger.warning(
                        f"Frame {frame_number}: {bend_analysis['severity']} "
                        f"- {trunk_angle:.1f}°"
                    )
            
            else:
                self.logger.debug(f"Frame {frame_number}: Nepodařilo se vypočítat úhel trupu")
                processed_frame = self._add_error_visualization(processed_frame, frame_number)
        
        else:
            self.processing_stats['failed_detections'] += 1
            self.logger.debug(f"Frame {frame_number}: Pose detection selhala")
            processed_frame = self._add_error_visualization(processed_frame, frame_number)
        
        # CSV export dat - vždy exportujeme, trunk_angle může být None
        if self.csv_exporter is not None:
            self.csv_exporter.export_frame_data(frame_number, trunk_angle)
        
        return processed_frame
    
    def _add_visualizations(self, 
                           frame: np.ndarray, 
                           pose_results: PoseResults,
                           trunk_angle: float, 
                           frame_number: int,
                           bend_analysis: Dict) -> np.ndarray:
        """
        Přidá všechny vizualizace na snímek
        
        Args:
            frame: Vstupní snímek
            pose_results: Výsledky pose detection
            trunk_angle: Úhel trupu
            frame_number: Číslo snímku
            bend_analysis: Výsledky analýzy ohnutí
            
        Returns:
            Snímek s vizualizacemi
        """
        # Skeleton a landmarks
        frame = self.visualizer.draw_skeleton(
            frame, 
            pose_results.pose_landmarks,
            pose_results.pose_world_landmarks,
            highlight_trunk=True
        )
        
        # Trunk vector
        frame = self.visualizer.draw_trunk_vector(
            frame,
            pose_results.pose_landmarks,
            pose_results.pose_world_landmarks,
            trunk_angle
        )
        
        # Informace o úhlu a statistiky
        frame = self.angle_display.draw_angle_info(
            frame,
            trunk_angle,
            frame_number,
            self.bend_threshold,
            additional_stats=bend_analysis
        )
        
        return frame
    
    def _add_error_visualization(self, frame: np.ndarray, frame_number: int) -> np.ndarray:
        """
        Přidá vizualizaci pro případ chyby detekce
        
        Args:
            frame: Vstupní snímek
            frame_number: Číslo snímku
            
        Returns:
            Snímek s error vizualizací
        """
        cv2.putText(frame, "POSE DETECTION FAILED", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.putText(frame, f"Frame: {frame_number}", (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
    
    def _generate_final_report(self) -> Dict:
        """
        Generuje finální report z analýzy
        
        Returns:
            Dictionary s finálními statistikami
        """
        bend_stats = self.bend_analyzer.get_statistics()
        
        report = {
            'input_file': self.input_path,
            'output_file': self.output_path,
            'video_info': self.video_info,
            'processing_stats': self.processing_stats,
            'bend_analysis': bend_stats,
            'configuration': {
                'bend_threshold': self.bend_threshold,
                'model_complexity': 1,  # Default value
                'min_detection_confidence': 0.5  # Default value
            }
        }
        
        # Přidání výkonových metrik
        if self.processing_stats['total_frames'] > 0:
            success_rate = (self.processing_stats['processed_frames'] / 
                          self.processing_stats['total_frames']) * 100
            report['success_rate'] = success_rate
        
        # Tisk reportu
        self._print_report(report)
        
        return report
    
    def _print_report(self, report: Dict):
        """
        Vytiskne textovy report
        
        Args:
            report: Dictionary s reportem
        """
        print("\n" + "="*60)
        print("FINALNI REPORT - ANALYZA OHNUTI TRUPU")
        print("="*60)
        
        print(f"\nVstupni soubor: {report['input_file']}")
        print(f"Vystupni soubor: {report['output_file']}")
        
        print(f"\nVideo informace:")
        print(f"  Rozliseni: {report['video_info']['width']}x{report['video_info']['height']}")
        print(f"  FPS: {report['video_info']['fps']:.1f}")
        print(f"  Delka: {report['video_info']['duration']:.1f}s")
        print(f"  Celkem snimku: {report['video_info']['frame_count']}")
        
        print(f"\nZpracovani:")
        print(f"  Zpracovane snimky: {report['processing_stats']['processed_frames']}")
        print(f"  Neuspesne detekce: {report['processing_stats']['failed_detections']}")
        print(f"  Uspesnost: {report.get('success_rate', 0):.1f}%")
        
        if 'bend_analysis' in report and report['bend_analysis']:
            bend_stats = report['bend_analysis']
            print(f"\nAnalyza ohnuti:")
            print(f"  Snimky s ohnutim >60 stupnu: {bend_stats['bend_frames']}")
            print(f"  Procento ohnuti: {bend_stats['bend_percentage']:.2f}%")
            print(f"  Prumerny uhel: {bend_stats['average_angle']:.2f} stupnu")
            print(f"  Maximalni uhel: {bend_stats['max_angle']:.2f} stupnu")
            print(f"  Minimalni uhel: {bend_stats['min_angle']:.2f} stupnu")
        
        print("\n" + "="*60)
    
    def _setup_logger(self) -> logging.Logger:
        """
        Nastavení loggeru
        
        Returns:
            Konfigurovaný logger
        """
        logger = logging.getLogger('TrunkAnalyzer')
        logger.setLevel(logging.INFO)
        
        # Console handler
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
        
        return logger
    
    def __del__(self):
        """Cleanup při destrukci objektu"""
        if hasattr(self, 'csv_exporter') and self.csv_exporter is not None:
            self.csv_exporter.finalize()
        if hasattr(self, 'input_handler'):
            del self.input_handler
        if hasattr(self, 'output_handler'):
            del self.output_handler
        if hasattr(self, 'pose_detector'):
            del self.pose_detector