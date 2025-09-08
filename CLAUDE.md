# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ergonomic Analysis application for detecting trunk bend angles in videos using MediaPipe 3D pose estimation. Provides both CLI (`main.py`) and Flask web application (`web_app.py`) interfaces with authentication and file upload capabilities.

## Common Commands

### Running the Application

**CLI Mode:**
```bash
python main.py input_video.mp4 output_video.mp4
python main.py input.mp4 output.mp4 --threshold 45 --csv-export
python main.py input.mp4 output.mp4 --model-complexity 2 --confidence 0.7
```

**Web Application:**
```bash
python web_app.py
```

**Running Tests:**
```bash
python test_simple.py
python test_web_app.py
python test_robustness.py
python test_csv_export.py
python test_chunked_upload.py
```

### Environment Setup

```bash
conda create -n trunk_analysis python=3.9 -y
conda activate trunk_analysis
pip install -r requirements.txt
```

### Deployment

**Heroku/Render (via Procfile):**
```bash
gunicorn web_app:app --timeout 3600 --workers 2 --worker-class sync --bind 0.0.0.0:$PORT
```

## Architecture

### Core Processing Pipeline (`src/`)

- **trunk_analyzer.py**: Main processing orchestrator coordinating all components
- **pose_detector.py**: MediaPipe pose detection wrapper (33 3D landmarks)
- **angle_calculator.py**: 3D trunk angle calculations using shoulder (11,12) and hip (23,24) landmarks
- **visualizer.py**: Skeleton rendering and angle display on video frames
- **video_processor.py**: Video I/O handling with frame-by-frame processing
- **csv_exporter.py**: Export angle data to CSV/Excel format with openpyxl

### Web Application (`web_app.py`)

- Flask 3.0.0 with Werkzeug 3.0.1
- Session-based authentication with hardcoded whitelist users
- Asynchronous video processing using threading
- Server-Sent Events (SSE) for real-time progress updates
- Chunked file upload for large videos (up to 5GB)
- Inline HTML templates with Tailwind CSS + DaisyUI (no separate template files)
- Admin logs viewer at `/admin/logs` endpoint

### Key Processing Parameters

- **Default Threshold**: 60° for bend detection
- **Temporal Smoothing**: 5-frame window for angle stability
- **MediaPipe Model Complexity**: 0 (lite), 1 (full), 2 (heavy)
- **Default Confidence**: 0.5 minimum detection confidence
- **Video Output**: MP4 with H264 codec, skeleton overlay + angle meter

## Important File Paths

- **Uploads**: `uploads/` - temporary storage for uploaded videos
- **Outputs**: `outputs/` - processed videos and analysis reports
- **Logs**: `logs/app.log`, `logs/user_actions.txt`
- **Test Data**: `data/input/`, `data/output/`

## Authentication Users (Web App)

Hardcoded in `web_app.py` WHITELIST_USERS dict:
- admin/admin123
- user1/user123
- demo/demo123
- Additional whitelist users can be added to the dict

## Key Technologies & Requirements

- **Python 3.9** (required - MediaPipe incompatible with 3.10+)
- **MediaPipe 0.10.8** for 3D pose detection
- **OpenCV 4.8.1.78** for video processing
- **NumPy 1.24.3** for numerical computations
- **Flask 3.0.0** for web application
- **openpyxl 3.1.2** for Excel export

## Email Notification System

**Email Features:**
- Automatic email notifications when processing completes
- Secure token-based download links (7-day expiry)
- HTML and text email templates
- Async email worker with retry mechanism
- Per-user email preferences in WHITELIST_USERS

**Email Configuration:**
```bash
# Required environment variables for production
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
```

**Testing:**
```bash
python test_email_functionality.py
```

## Error Handling & Edge Cases

- Missing pose detections logged but don't crash processing
- CSV export includes frame numbers for missing detections
- Session cleanup for incomplete uploads
- Chunked upload mechanism prevents timeout on large files
- Graceful handling of corrupted video files
- Email failures with exponential backoff retry (3 attempts)
- Token-based downloads with signature verification