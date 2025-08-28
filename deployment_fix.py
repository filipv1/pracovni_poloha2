#!/usr/bin/env python3
"""
Storage path fix pro cloud deployment
Přidejte tento kód na začátek web_app.py po imports
"""

import os
from pathlib import Path

# Cloud storage setup
def setup_storage_paths():
    """
    Nastavení storage paths pro cloud deployment
    Detekuje cloud environment a nastavuje správné cesty
    """
    
    # Detekce cloud platformy
    is_railway = os.environ.get('RAILWAY_ENVIRONMENT') is not None
    is_render = os.path.exists('/opt/render')
    is_heroku = os.environ.get('DYNO') is not None
    
    if is_railway:
        # Railway - použije mounted volume
        base_storage = '/app/data'
        if not os.path.exists(base_storage):
            base_storage = './data'  # fallback pro local testing
    elif is_render:
        # Render - opravené storage paths
        base_storage = '/opt/render/project/src/storage'
        if not os.path.exists(base_storage):
            base_storage = './data'
    else:
        # Local development
        base_storage = './data'
    
    # Vytvoření adresářů
    upload_folder = os.path.join(base_storage, 'uploads')
    output_folder = os.path.join(base_storage, 'outputs')  
    log_folder = os.path.join(base_storage, 'logs')
    
    # Ensure directories exist
    for folder in [base_storage, upload_folder, output_folder, log_folder]:
        os.makedirs(folder, exist_ok=True)
        
    return upload_folder, output_folder, log_folder

# Použití v web_app.py - nahradí řádky 30-37:
UPLOAD_FOLDER, OUTPUT_FOLDER, LOG_FOLDER = setup_storage_paths()

print(f"Storage paths configured:")
print(f"  Uploads: {UPLOAD_FOLDER}")
print(f"  Outputs: {OUTPUT_FOLDER}")  
print(f"  Logs: {LOG_FOLDER}")