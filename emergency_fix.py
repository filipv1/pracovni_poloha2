#!/usr/bin/env python3
"""
EMERGENCY FIX - okamžitě sníží náklady
Přidej tento import do web_app.py: import emergency_fix
"""

import os
import gc
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

print("EMERGENCY FIX: Activated")

# 1. AGRESIVNÍ GARBAGE COLLECTION
gc.set_threshold(100, 5, 5)
gc.collect(2)

# 2. OKAMŽITÉ VYČIŠTĚNÍ STARÝCH SOUBORŮ
def emergency_cleanup():
    """Vymaž všechny soubory starší než 6 hodin"""
    cutoff = datetime.now() - timedelta(hours=6)
    total_freed = 0
    
    for folder in ['uploads', 'outputs', 'jobs']:
        if not os.path.exists(folder):
            continue
        for file in Path(folder).glob('*'):
            try:
                if file.is_file():
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    if mtime < cutoff:
                        size = file.stat().st_size
                        file.unlink()
                        total_freed += size
            except:
                pass
    
    mb_freed = total_freed / 1024 / 1024
    print(f"EMERGENCY CLEANUP: Freed {mb_freed:.2f} MB")
    return mb_freed

# 3. PERIODICKÉ ČIŠTĚNÍ KAŽDOU HODINU
def periodic_emergency_cleanup():
    while True:
        time.sleep(3600)  # každou hodinu
        emergency_cleanup()
        gc.collect(2)

# Spusť okamžitě
emergency_cleanup()

# Spusť periodické čištění
cleanup_thread = threading.Thread(target=periodic_emergency_cleanup, daemon=True)
cleanup_thread.start()

print("EMERGENCY FIX: Running - cleanup every hour")