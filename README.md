# Trunk Analysis - Analýza ohnutí trupu

Prototyp aplikace pro analýzu ohnutí trupu z MP4 videa pomocí MediaPipe 3D pose estimation.

## Funkcionalita

- **3D Pose Detection**: Detekce postavy pomocí MediaPipe
- **Analýza úhlů**: Výpočet úhlu ohnutí trupu ve 3D prostoru
- **Vizualizace**: Vykreslení 3D skeletu a úhloměru
- **Video export**: Vytvoření MP4 videa s analýzou
- **Statistiky**: Detailní report s procenty ohnutí

## Výsledky testování

Na testovacím videu (16.2s, 405 snímků) byly dosaženy tyto výsledky:

- **Úspěšnost detekce**: 100% (405/405 snímků)
- **Procento ohnutí**: 60.25% snímků s ohnutím >60°
- **Průměrný úhel**: 59.33°
- **Maximální úhel**: 80.84° (extrémní ohnutí)
- **Minimální úhel**: 13.83°

## Instalace

### 1. Conda prostředí
```bash
conda create -n trunk_analysis python=3.9 -y
conda activate trunk_analysis
```

### 2. Závislosti
```bash
pip install mediapipe==0.10.8 opencv-python==4.8.1.78 numpy==1.24.3 matplotlib==3.7.2 tqdm
```

## Použití

### Základní použití
```bash
python main.py input_video.mp4 output_video.mp4
```

### Pokročilé možnosti
```bash
python main.py input.mp4 output.mp4 --model-complexity 2 --threshold 45 --confidence 0.7
```

### Parametry
- `--model-complexity {0,1,2}`: Složitost modelu (0=lite, 1=full, 2=heavy)
- `--threshold ANGLE`: Práh pro detekci ohnutí (default: 60.0°)
- `--confidence FLOAT`: Minimální confidence (default: 0.5)
- `--smoothing INT`: Velikost okna pro vyhlazování (default: 5)
- `--no-progress`: Bez progress baru
- `--verbose`: Detailní logování

## Struktura projektu

```
trunk_analysis/
├── src/
│   ├── video_processor.py    # Video I/O
│   ├── pose_detector.py      # MediaPipe wrapper
│   ├── angle_calculator.py   # Výpočty úhlů
│   ├── visualizer.py         # 3D skeleton rendering
│   ├── trunk_analyzer.py     # Hlavní procesor
│   └── utils.py              # Pomocné funkce
├── data/
│   ├── input/                # Vstupní videa
│   └── output/               # Výstupní videa a reporty
├── main.py                   # CLI interface
└── requirements.txt          # Závislosti
```

## Výstupy

### Video
- MP4 soubor s vykresleným skeletonem
- Úhloměr v reálném čase
- Indikátory závažnosti ohnutí
- Frame-by-frame analýza

### Report
- Textový soubor s detailními statistikami
- Procenta ohnutí
- Průměrné, minimální a maximální úhly
- Úspěšnost detekce

## Technické detaily

### MediaPipe 3D Pose
- 33 3D landmarks v metrech
- Klíčové body: ramena (11,12) a boky (23,24)
- Confidence scoring a visibility

### Výpočet úhlů
- 3D vektorová matematika
- Dot product mezi trunk vektorem a vertikálou
- Temporal smoothing pro stabilitu

### Visualizace
- OpenCV rendering
- Barevné kódování podle hloubky
- Real-time úhloměr
- Indikátory závažnosti

## Přesnost

- Detekce postavy: 100% na testovacím videu
- Úhlová přesnost: ±2-3° (MediaPipe limitation)
- Temporal smoothing redukuje šum
- Funguje nejlépe ve vzdálenosti 2-4m od kamery

## Limitace

- Závislost na kvalitě MediaPipe detekce
- Nejlepší výsledky při frontálním pohledu
- Vyžaduje dobré osvětlení
- Python 3.9 (MediaPipe compatibility)

## Test

Pro otestování aplikace spusťte:
```bash
python test_simple.py
```

Test zpracuje ukázkové video a vytvoří analyzované výstupy.