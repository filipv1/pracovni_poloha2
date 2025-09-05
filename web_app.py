#!/usr/bin/env python3
"""
Flask Web Application for Ergonomic Trunk Analysis
Moderní, minimalistická webová aplikace pro analýzu pracovní polohy
"""

import os
import sys
import json
import uuid
import shutil
import logging
import tempfile
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from queue import Queue
import time

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for, flash, send_file, Response

# Přidání src do Python path pro import modulů
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'ergonomic-analysis-2025-ultra-secure-key-change-in-production')

# Konfigurace
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs' 
LOG_FOLDER = 'logs'
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.m4v', '.wmv', '.flv', '.webm'}

# Vytvoření potřebných složek
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, LOG_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Flask konfigurace pro velké soubory
max_size = int(os.environ.get('MAX_UPLOAD_SIZE', 5 * 1024 * 1024 * 1024))  # Default 5GB
app.config['MAX_CONTENT_LENGTH'] = max_size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Production settings
if os.environ.get('FLASK_ENV') == 'production':
    # Optimalizace pro cloud deployment
    import gc
    gc.set_threshold(700, 10, 10)  # Aggressive garbage collection

# Whitelist uživatelů
WHITELIST_USERS = {
    'korc': {'password': 'K7mN9xP2Qw', 'name': 'Korc'},
    'koska': {'password': 'R8vB3yT6Lm', 'name': 'Koška'},
    'licha': {'password': 'F5jH8wE9Xn', 'name': 'Licha'},
    'koutenska': {'password': 'M2nV7kR4Zs', 'name': 'Koutenská'},
    'kusinova': {'password': 'D9xC6tY3Bp', 'name': 'Kušinová'},
    'vagnerova': {'password': 'L4gW8fQ5Hm', 'name': 'Vágnerová'},
    'badrova': {'password': 'T7kN2vS9Rx', 'name': 'Badrová'},
    'henkova': {'password': 'P3mJ6wA8Qz', 'name': 'Henková'},
    'vaclavik': {'password': 'A9xL4pK7Fn', 'name': 'Václavík'}
}

# Queue pro zpracování videí
processing_queue = Queue()
active_jobs = {}

# Cleanup old upload sessions on startup
def cleanup_old_sessions():
    """Clean up old upload sessions and incomplete files"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=24)  # Remove sessions older than 24 hours
        to_remove = []
        
        for job_id, job in active_jobs.items():
            created_at = job.get('created_at')
            if created_at and created_at < cutoff_time:
                # Remove incomplete upload file
                if job.get('status') == 'uploading' and job.get('filepath'):
                    try:
                        if os.path.exists(job['filepath']):
                            os.remove(job['filepath'])
                            logger.info(f"Removed incomplete upload: {job['filepath']}")
                    except Exception as e:
                        logger.error(f"Failed to remove incomplete upload {job['filepath']}: {e}")
                
                to_remove.append(job_id)
        
        for job_id in to_remove:
            del active_jobs[job_id]
            logger.info(f"Cleaned up old session: {job_id}")
            
    except Exception as e:
        logger.error(f"Session cleanup error: {e}")


# Logging setup
def setup_logging():
    """Nastavení logování do souboru"""
    log_file = os.path.join(LOG_FOLDER, 'app.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()
cleanup_old_sessions()  # Clean up on startup

def log_user_action(username, action, details=""):
    """Logování uživatelských akcí"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - User: {username} - Action: {action} - Details: {details}\n"
    
    log_file = os.path.join(LOG_FOLDER, 'user_actions.txt')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# Base HTML Template
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Ergonomická Analýza{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.4.24/dist/full.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: '#2563eb',
                        'primary-hover': '#1d4ed8',
                        'surface': '#f9fafb',
                        'surface-dark': '#1e293b'
                    }
                }
            }
        }
    </script>
    <style>
        /* Custom animations */
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        @keyframes spin { to { transform: rotate(360deg); } }
        .fade-in { animation: fadeIn 0.5s ease-out; }
        .pulse-animation { animation: pulse 2s infinite; }
        .spin-animation { animation: spin 1s linear infinite; }
        
        /* Upload area hover effects */
        .upload-zone { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .upload-zone:hover { transform: translateY(-4px); }
        .upload-zone.dragover { 
            border-color: #2563eb; 
            background-color: rgba(37, 99, 235, 0.05);
            box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
        }
        
        /* Progress bar animations */
        .progress-bar { transition: width 0.5s ease-out; }
        
        /* Button hover effects */
        .btn-hover { transition: all 0.2s ease; }
        .btn-hover:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        
        /* Dark mode variables */
        :root { 
            --bg-primary: #ffffff;
            --bg-surface: #f9fafb;
            --text-primary: #111827;
            --text-secondary: #6b7280;
            --border-color: #e5e7eb;
        }
        
        .dark { 
            --bg-primary: #0f172a;
            --bg-surface: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #cbd5e1;
            --border-color: #334155;
        }
    </style>
</head>
<body class="h-full bg-base-100 transition-colors duration-300">
    {% block content %}{% endblock %}
    
    <script>
        // Dark mode toggle
        function initDarkMode() {
            const theme = localStorage.getItem('theme') || 'light';
            if (theme === 'dark') {
                document.documentElement.classList.add('dark');
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.classList.remove('dark');
                document.documentElement.setAttribute('data-theme', 'light');
            }
        }
        
        function toggleDarkMode() {
            const isDark = document.documentElement.classList.contains('dark');
            if (isDark) {
                document.documentElement.classList.remove('dark');
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.classList.add('dark');
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            }
        }
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', initDarkMode);
    </script>
</body>
</html>
"""

# Login Template
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Přihlášení - Ergonomická Analýza</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.4.24/dist/full.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: '#2563eb',
                        'primary-hover': '#1d4ed8',
                        'surface': '#f9fafb',
                        'surface-dark': '#1e293b'
                    }
                }
            }
        }
    </script>
    <style>
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.5s ease-out; }
    </style>
</head>
<body class="h-full bg-base-100 transition-colors duration-300">
<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800">
    <div class="max-w-md w-full mx-4">
        <!-- Dark mode toggle -->
        <div class="flex justify-end mb-6">
            <button onclick="toggleDarkMode()" class="btn btn-circle btn-ghost">
                <svg class="w-5 h-5 dark:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>
                </svg>
                <svg class="w-5 h-5 hidden dark:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>
                </svg>
            </button>
        </div>

        <div class="card bg-white dark:bg-slate-800 shadow-2xl fade-in">
            <div class="card-body">
                <div class="text-center mb-8">
                    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Ergonomická Analýza</h1>
                    <p class="text-gray-600 dark:text-gray-300 mt-2">Analýza pracovní polohy pomocí AI</p>
                </div>

                {% with messages = get_flashed_messages() %}
                    {% if messages %}
                        <div class="alert alert-error mb-4">
                            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            <span>{{ messages[0] }}</span>
                        </div>
                    {% endif %}
                {% endwith %}

                <form method="POST">
                    <div class="form-control">
                        <label class="label">
                            <span class="label-text dark:text-gray-300">Uživatelské jméno</span>
                        </label>
                        <input type="text" name="username" class="input input-bordered w-full" required autofocus>
                    </div>
                    
                    <div class="form-control mt-4">
                        <label class="label">
                            <span class="label-text dark:text-gray-300">Heslo</span>
                        </label>
                        <input type="password" name="password" class="input input-bordered w-full" required>
                    </div>
                    
                    <div class="form-control mt-6">
                        <button type="submit" class="btn btn-primary w-full btn-hover">
                            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                            </svg>
                            Přihlásit se
                        </button>
                    </div>
                </form>

                <div class="divider mt-8">Přihlášení</div>
                <div class="text-center text-sm text-gray-500 dark:text-gray-400">
                    <p>Pro přístup kontaktujte administrátora</p>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    // Dark mode toggle
    function initDarkMode() {
        const theme = localStorage.getItem('theme') || 'light';
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.setAttribute('data-theme', 'light');
        }
    }
    
    function toggleDarkMode() {
        const isDark = document.documentElement.classList.contains('dark');
        if (isDark) {
            document.documentElement.classList.remove('dark');
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.classList.add('dark');
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', initDarkMode);
</script>
</body>
</html>
"""

# Main Application Template
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ergonomická Analýza</title>
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.4.24/dist/full.css" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: '#2563eb',
                        'primary-hover': '#1d4ed8',
                        'surface': '#f9fafb',
                        'surface-dark': '#1e293b'
                    }
                }
            }
        }
    </script>
    <style>
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        @keyframes spin { to { transform: rotate(360deg); } }
        .fade-in { animation: fadeIn 0.5s ease-out; }
        .pulse-animation { animation: pulse 2s infinite; }
        .spin-animation { animation: spin 1s linear infinite; }
        
        .upload-zone { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
        .upload-zone:hover { transform: translateY(-4px); }
        .upload-zone.dragover { 
            border-color: #2563eb; 
            background-color: rgba(37, 99, 235, 0.05);
            box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
        }
        
        .progress-bar { transition: width 0.5s ease-out; }
        .btn-hover { transition: all 0.2s ease; }
        .btn-hover:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
    </style>
</head>
<body class="h-full bg-base-100 transition-colors duration-300">
<div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-900 dark:to-slate-800">
    <!-- Header -->
    <header class="bg-white dark:bg-slate-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <h1 class="text-xl font-semibold text-gray-900 dark:text-white">Ergonomická Analýza</h1>
                    <span class="ml-3 text-sm text-gray-500 dark:text-gray-400">Vítejte, {{ session.username }}!</span>
                </div>
                
                <div class="flex items-center space-x-4">
                    <!-- Dark mode toggle -->
                    <button onclick="toggleDarkMode()" class="btn btn-circle btn-ghost">
                        <svg class="w-5 h-5 dark:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>
                        </svg>
                        <svg class="w-5 h-5 hidden dark:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>
                        </svg>
                    </button>
                    
                    <a href="{{ url_for('logout') }}" class="btn btn-outline btn-sm">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
                        </svg>
                        Odhlásit
                    </a>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-4 py-8">
        <!-- Upload Section - Dominanta stránky -->
        <div class="text-center mb-12">
            <div id="upload-container" class="upload-zone bg-white dark:bg-slate-800 border-3 border-dashed border-gray-300 dark:border-gray-600 rounded-2xl p-12 mx-auto max-w-4xl cursor-pointer hover:border-primary hover:bg-blue-50 dark:hover:bg-slate-700 transition-all duration-300">
                <div class="flex flex-col items-center justify-center space-y-6">
                    <div class="w-20 h-20 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                        <svg class="w-10 h-10 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                        </svg>
                    </div>
                    <div>
                        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Nahrajte video pro analýzu</h2>
                        <p class="text-gray-600 dark:text-gray-300 mb-4">Přetáhněte soubory sem nebo klikněte pro výběr</p>
                        <p class="text-sm text-gray-500 dark:text-gray-400">Podporované formáty: MP4, AVI, MOV, MKV • Maximální velikost: 5GB</p>
                    </div>
                    <button class="btn btn-primary btn-lg btn-hover">
                        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                        </svg>
                        Vybrat soubory
                    </button>
                </div>
                
                <input type="file" id="file-input" multiple accept=".mp4,.avi,.mov,.mkv,.m4v,.wmv,.flv,.webm" class="hidden">
            </div>
        </div>

        <!-- Body Parts Selection -->
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6 mb-8">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Vyberte části těla pro analýzu</h3>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
                <label class="flex items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 cursor-pointer">
                    <input type="checkbox" id="trunk-checkbox" checked class="checkbox checkbox-primary mr-3">
                    <span class="text-gray-900 dark:text-white font-medium">Trup</span>
                </label>
                <label class="flex items-center p-3 rounded-lg opacity-50 cursor-not-allowed">
                    <input type="checkbox" disabled class="checkbox mr-3">
                    <span class="text-gray-500 dark:text-gray-400">Krk</span>
                    <span class="text-xs text-gray-400 ml-2">(připravuje se)</span>
                </label>
                <label class="flex items-center p-3 rounded-lg opacity-50 cursor-not-allowed">
                    <input type="checkbox" disabled class="checkbox mr-3">
                    <span class="text-gray-500 dark:text-gray-400">Pravá horní končetina</span>
                    <span class="text-xs text-gray-400 ml-2">(připravuje se)</span>
                </label>
                <label class="flex items-center p-3 rounded-lg opacity-50 cursor-not-allowed">
                    <input type="checkbox" disabled class="checkbox mr-3">
                    <span class="text-gray-500 dark:text-gray-400">Levá horní končetina</span>
                    <span class="text-xs text-gray-400 ml-2">(připravuje se)</span>
                </label>
                <label class="flex items-center p-3 rounded-lg opacity-50 cursor-not-allowed">
                    <input type="checkbox" disabled class="checkbox mr-3">
                    <span class="text-gray-500 dark:text-gray-400">Dolní končetiny</span>
                    <span class="text-xs text-gray-400 ml-2">(připravuje se)</span>
                </label>
                <label class="flex items-center p-3 rounded-lg opacity-50 cursor-not-allowed">
                    <input type="checkbox" disabled class="checkbox mr-3">
                    <span class="text-gray-500 dark:text-gray-400">Ostatní části</span>
                    <span class="text-xs text-gray-400 ml-2">(připravuje se)</span>
                </label>
            </div>
        </div>

        <!-- File List -->
        <div id="file-list" class="hidden bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6 mb-8">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Nahrané soubory</h3>
                <button id="start-processing" class="btn btn-primary btn-hover" disabled>
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M19 10a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Spustit analýzu
                </button>
            </div>
            <div id="files-container" class="space-y-3"></div>
        </div>

        <!-- Results Section -->
        <div id="results-section" class="hidden bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Výsledky analýzy</h3>
            <div id="results-container" class="space-y-4"></div>
        </div>
    </main>
    
    <!-- Progress Toast -->
    <div id="progress-toast" class="fixed bottom-20 right-4 hidden">
        <div class="alert alert-info relative">
            <button onclick="document.getElementById('progress-toast').classList.add('hidden')" class="absolute top-2 right-2 btn btn-ghost btn-xs">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
            <div class="flex items-center pr-6">
                <div class="spin-animation w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-3"></div>
                <div>
                    <div class="font-semibold" id="progress-title">Zpracovávám...</div>
                    <div class="text-sm" id="progress-detail">Prosím počkejte</div>
                </div>
            </div>
            <div class="w-full bg-base-300 rounded-full h-2 mt-2">
                <div id="progress-bar" class="bg-primary h-2 rounded-full progress-bar" style="width: 0%"></div>
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.getElementById('upload-container');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const filesContainer = document.getElementById('files-container');
    const startProcessing = document.getElementById('start-processing');
    const resultsSection = document.getElementById('results-section');
    const progressToast = document.getElementById('progress-toast');
    
    let selectedFiles = [];
    let activeJobs = {};

    // Click to upload
    uploadContainer.addEventListener('click', () => fileInput.click());

    // Drag and drop
    uploadContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadContainer.classList.add('dragover');
    });

    uploadContainer.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadContainer.classList.remove('dragover');
    });

    uploadContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadContainer.classList.remove('dragover');
        const files = Array.from(e.dataTransfer.files);
        handleFiles(files);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        handleFiles(files);
    });

    function handleFiles(files) {
        const validFiles = files.filter(file => {
            const ext = '.' + file.name.split('.').pop().toLowerCase();
            return ['.mp4', '.avi', '.mov', '.mkv', '.m4v', '.wmv', '.flv', '.webm'].includes(ext);
        });

        if (validFiles.length === 0) {
            alert('Prosím vyberte validní video soubory');
            return;
        }

        selectedFiles = [...selectedFiles, ...validFiles];
        updateFileList();
        fileList.classList.remove('hidden');
        startProcessing.disabled = false;
    }

    function updateFileList() {
        filesContainer.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-700 rounded-lg fade-in';
            fileItem.innerHTML = `
                <div class="flex items-center">
                    <div class="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center mr-4">
                        <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m-9 0h10m-10 0a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V6a2 2 0 00-2-2m-4 6h2m-2 4h2m-2 4h2"></path>
                        </svg>
                    </div>
                    <div>
                        <div class="font-medium text-gray-900 dark:text-white">${file.name}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${formatFileSize(file.size)}</div>
                    </div>
                </div>
                <button onclick="removeFile(${index})" class="btn btn-circle btn-ghost btn-sm">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            `;
            filesContainer.appendChild(fileItem);
        });
    }

    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        updateFileList();
        if (selectedFiles.length === 0) {
            fileList.classList.add('hidden');
            startProcessing.disabled = true;
        }
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Start processing
    startProcessing.addEventListener('click', function() {
        if (selectedFiles.length === 0) return;
        
        startProcessing.disabled = true;
        progressToast.classList.remove('hidden');
        resultsSection.classList.remove('hidden');
        
        selectedFiles.forEach(file => uploadAndProcess(file));
    });

    async function uploadAndProcess(file) {
        const jobId = await chunkedUpload(file);
        if (!jobId) return; // Upload failed
        
        try {
            updateProgress(`Zpracovávám ${file.name}`, 30);
            
            // Start processing
            const processResponse = await fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id: jobId })
            });
            
            if (!processResponse.ok) throw new Error('Processing failed');
            
            // Monitor progress
            monitorJob(jobId);
            
        } catch (error) {
            console.error('Error:', error);
            showError(`Chyba při zpracování ${file.name}: ${error.message}`);
        }
    }

    async function chunkedUpload(file) {
        const CHUNK_SIZE = 1024 * 1024; // 1MB chunks
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
        
        try {
            // Initialize upload
            const initResponse = await fetch('/upload/init', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: file.name,
                    filesize: file.size,
                    chunk_size: CHUNK_SIZE
                })
            });
            
            if (!initResponse.ok) {
                const error = await initResponse.json();
                throw new Error(error.error || 'Upload initialization failed');
            }
            
            const { job_id, chunk_size, total_chunks } = await initResponse.json();
            activeJobs[job_id] = { file: file.name, status: 'uploading', originalFile: file };
            
            // Upload chunks
            for (let chunkIndex = 0; chunkIndex < total_chunks; chunkIndex++) {
                const start = chunkIndex * chunk_size;
                const end = Math.min(start + chunk_size, file.size);
                const chunk = file.slice(start, end);
                
                const progress = Math.round((chunkIndex / total_chunks) * 25); // Upload is 0-25% of total progress
                updateProgress(`Nahrávám ${file.name}`, progress);
                
                // Upload chunk with retry logic
                let retryCount = 0;
                const maxRetries = 3;
                
                while (retryCount < maxRetries) {
                    try {
                        const chunkResponse = await fetch(`/upload/chunk/${job_id}/${chunkIndex}`, {
                            method: 'POST',
                            body: chunk
                        });
                        
                        if (!chunkResponse.ok) {
                            throw new Error(`Chunk ${chunkIndex} upload failed: HTTP ${chunkResponse.status}`);
                        }
                        
                        const result = await chunkResponse.json();
                        if (result.status === 'success' || result.status === 'already_uploaded') {
                            break; // Chunk uploaded successfully
                        }
                        
                        throw new Error(`Chunk ${chunkIndex} upload failed: ${result.error || 'Unknown error'}`);
                        
                    } catch (error) {
                        retryCount++;
                        console.warn(`Chunk ${chunkIndex} failed (attempt ${retryCount}/${maxRetries}):`, error);
                        
                        if (retryCount >= maxRetries) {
                            throw new Error(`Failed to upload chunk ${chunkIndex} after ${maxRetries} attempts: ${error.message}`);
                        }
                        
                        // Wait before retry (exponential backoff)
                        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retryCount - 1)));
                    }
                }
            }
            
            updateProgress(`Upload ${file.name} dokončen`, 25);
            return job_id;
            
        } catch (error) {
            console.error('Chunked upload failed:', error);
            showError(`Chyba při nahrávání ${file.name}: ${error.message}`);
            return null;
        }
    }

    function monitorJob(jobId) {
        let pollInterval;
        let pollCount = 0;
        const maxPolls = 14400; // 4 hours max (for very long videos)
        
        async function pollStatus() {
            try {
                const response = await fetch(`/status/${jobId}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                console.log(`Poll ${pollCount}: Job ${jobId}`, data);
                
                updateProgress(data.message, data.progress);
                
                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    addResult(jobId, data.results);
                    checkAllJobsCompleted();
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    showError(data.message);
                    checkAllJobsCompleted();
                } else if (pollCount >= maxPolls) {
                    clearInterval(pollInterval);
                    showError(`Timeout: Job ${jobId} exceeded 4 hours processing limit`);
                    checkAllJobsCompleted();
                }
                
                pollCount++;
                
                // Exponential backoff - after 5 minutes, poll every 5 seconds
                if (pollCount === 300) { // 5 minutes
                    clearInterval(pollInterval);
                    console.log('Switching to slower polling for long job...');
                    pollInterval = setInterval(pollStatus, 5000); // Every 5 seconds
                }
            } catch (error) {
                console.error('Poll error:', error);
                clearInterval(pollInterval);
                showError(`Connection error: ${error.message}`);
                checkAllJobsCompleted();
            }
        }
        
        // Start polling every 1 second
        pollInterval = setInterval(pollStatus, 1000);
        pollStatus(); // Initial poll
    }

    function addResult(jobId, results) {
        const resultItem = document.createElement('div');
        resultItem.className = 'p-4 bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 rounded-lg fade-in';
        resultItem.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex items-center">
                    <div class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center mr-3">
                        <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <div>
                        <div class="font-medium text-green-900 dark:text-green-100">${activeJobs[jobId].file}</div>
                        <div class="text-sm text-green-700 dark:text-green-300">Analýza dokončena úspěšně</div>
                    </div>
                </div>
                <div class="flex space-x-2">
                    <a href="/download/${jobId}/video" class="btn btn-sm btn-primary">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-4-4m4 4l4-4m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                        </svg>
                        Video
                    </a>
                    <a href="/download/${jobId}/excel" class="btn btn-sm btn-success">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-4-4m4 4l4-4m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                        </svg>
                        Excel
                    </a>
                </div>
            </div>
        `;
        document.getElementById('results-container').appendChild(resultItem);
    }

    function checkAllJobsCompleted() {
        const allCompleted = Object.values(activeJobs).every(job => 
            job.status === 'completed' || job.status === 'error'
        );
        
        if (allCompleted) {
            // Hide progress toast after a brief delay to show completion
            setTimeout(() => {
                progressToast.classList.add('hidden');
            }, 3000); // Hide after 3 seconds
            startProcessing.disabled = false;
        }
    }

    function updateProgress(message, percent) {
        document.getElementById('progress-title').textContent = message;
        document.getElementById('progress-detail').textContent = `${percent}% dokončeno`;
        document.getElementById('progress-bar').style.width = `${percent}%`;
    }

    function showError(message) {
        // Add error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-error mb-4 fade-in';
        errorDiv.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <span>${message}</span>
        `;
        document.querySelector('main').insertBefore(errorDiv, document.querySelector('main').firstChild);
        
        setTimeout(() => errorDiv.remove(), 5000);
    }

    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
});

    // Dark mode toggle
    function initDarkMode() {
        const theme = localStorage.getItem('theme') || 'light';
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.setAttribute('data-theme', 'light');
        }
    }
    
    function toggleDarkMode() {
        const isDark = document.documentElement.classList.contains('dark');
        if (isDark) {
            document.documentElement.classList.remove('dark');
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.classList.add('dark');
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initDarkMode();
        // Initialize upload functionality here
    });
</script>
</body>
</html>
"""

# Templates are now complete HTML documents

# Routes
@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template_string(MAIN_TEMPLATE, session=session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in WHITELIST_USERS and WHITELIST_USERS[username]['password'] == password:
            session['username'] = username
            session['user_name'] = WHITELIST_USERS[username]['name']
            log_user_action(username, 'login', 'Successful login')
            logger.info(f"User {username} logged in successfully")
            return redirect(url_for('home'))
        else:
            flash('Neplatné přihlašovací údaje')
            log_user_action(username or 'unknown', 'login_failed', 'Invalid credentials')
            
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    if 'username' in session:
        log_user_action(session['username'], 'logout', 'User logged out')
        logger.info(f"User {session['username']} logged out")
        session.clear()
    return redirect(url_for('login'))

@app.route('/health')
def health_check():
    """Health check endpoint for deployment platforms"""
    return jsonify({
        'status': 'healthy',
        'service': 'ergonomic-analysis',
        'timestamp': datetime.now().isoformat(),
        'active_jobs': len(active_jobs)
    }), 200

@app.route('/upload/cleanup/<job_id>', methods=['DELETE'])
def cleanup_upload(job_id):
    """Clean up failed or cancelled upload"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    
    try:
        # Remove uploaded file if exists
        if job.get('filepath') and os.path.exists(job['filepath']):
            os.remove(job['filepath'])
            logger.info(f"Cleaned up upload file: {job['filepath']}")
        
        # Remove job from active jobs
        del active_jobs[job_id]
        
        log_user_action(session['username'], 'upload_cleanup', f'Cleaned up job: {job_id}')
        
        return jsonify({'status': 'cleaned_up'})
        
    except Exception as e:
        logger.error(f"Cleanup error for job {job_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/logs')
def admin_logs():
    """Admin endpoint to view user activity logs"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        user_actions_path = os.path.join(LOG_FOLDER, 'user_actions.txt')
        logs_content = []
        
        if os.path.exists(user_actions_path):
            with open(user_actions_path, 'r', encoding='utf-8') as f:
                logs_content = f.readlines()
        
        # Return last 100 entries, newest first
        logs_content = logs_content[-100:][::-1]
        
        html = """
        <html>
        <head><title>User Activity Logs</title>
        <style>
        body { font-family: monospace; background: #f5f5f5; padding: 20px; }
        .log-entry { background: white; padding: 8px; margin: 2px 0; border-left: 4px solid #007acc; }
        .header { background: #333; color: white; padding: 10px; margin-bottom: 20px; }
        .login { color: green; font-weight: bold; }
        .logout { color: orange; }
        .upload { color: blue; }
        .download { color: purple; }
        .error { color: red; }
        </style>
        </head>
        <body>
        <div class="header">
        <h2>🔍 User Activity Logs</h2>
        <p>Last 100 entries (newest first) | <a href="/" style="color: white;">← Back to App</a></p>
        </div>
        """
        
        for line in logs_content:
            line_clean = line.strip()
            css_class = ""
            if "login" in line_clean.lower():
                css_class = "login"
            elif "logout" in line_clean.lower():
                css_class = "logout"  
            elif "upload" in line_clean.lower():
                css_class = "upload"
            elif "download" in line_clean.lower():
                css_class = "download"
            elif "failed" in line_clean.lower():
                css_class = "error"
                
            html += f'<div class="log-entry {css_class}">{line_clean}</div>'
        
        html += "</body></html>"
        return html
        
    except Exception as e:
        return f"Error reading logs: {str(e)}"

@app.route('/upload/init', methods=['POST'])
def init_upload():
    """Initialize chunked upload"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    filename = data.get('filename')
    filesize = data.get('filesize')
    chunk_size = data.get('chunk_size', 1024 * 1024)  # Default 1MB chunks
    
    if not filename or not filesize:
        return jsonify({'error': 'Missing filename or filesize'}), 400
        
    # Validate file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Unsupported file format: {file_ext}'}), 400
    
    # Generate job ID and setup upload session
    job_id = str(uuid.uuid4())
    upload_filename = f"{job_id}_{filename}"
    upload_filepath = os.path.join(app.config['UPLOAD_FOLDER'], upload_filename)
    
    total_chunks = (filesize + chunk_size - 1) // chunk_size
    
    # Store upload session info
    active_jobs[job_id] = {
        'filename': upload_filename,
        'filepath': upload_filepath,
        'original_name': filename,
        'filesize': filesize,
        'chunk_size': chunk_size,
        'total_chunks': total_chunks,
        'uploaded_chunks': set(),
        'status': 'uploading',
        'upload_progress': 0,
        'user': session['username'],
        'created_at': datetime.now()
    }
    
    # Create empty file
    with open(upload_filepath, 'wb') as f:
        f.seek(filesize - 1)
        f.write(b'\0')
    
    log_user_action(session['username'], 'upload_init', f'Started upload: {filename} ({filesize} bytes, {total_chunks} chunks)')
    logger.info(f"Upload initialized: {filename} ({filesize} bytes) by {session['username']}")
    
    return jsonify({
        'job_id': job_id,
        'chunk_size': chunk_size,
        'total_chunks': total_chunks
    })

@app.route('/upload/chunk/<job_id>/<int:chunk_index>', methods=['POST'])
def upload_chunk(job_id, chunk_index):
    """Handle individual chunk upload"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if job_id not in active_jobs:
        return jsonify({'error': 'Upload session not found'}), 404
    
    job = active_jobs[job_id]
    
    if job['status'] != 'uploading':
        return jsonify({'error': 'Upload session not active'}), 400
    
    if chunk_index >= job['total_chunks'] or chunk_index < 0:
        return jsonify({'error': 'Invalid chunk index'}), 400
    
    # Check if chunk already uploaded (for resumability)
    if chunk_index in job['uploaded_chunks']:
        return jsonify({'status': 'already_uploaded', 'progress': len(job['uploaded_chunks']) / job['total_chunks'] * 100})
    
    try:
        # Get chunk data
        chunk_data = request.get_data()
        if not chunk_data:
            return jsonify({'error': 'No chunk data received'}), 400
        
        # Write chunk to file
        with open(job['filepath'], 'r+b') as f:
            f.seek(chunk_index * job['chunk_size'])
            f.write(chunk_data)
        
        # Update progress
        job['uploaded_chunks'].add(chunk_index)
        progress = len(job['uploaded_chunks']) / job['total_chunks'] * 100
        job['upload_progress'] = progress
        
        # Check if upload is complete
        if len(job['uploaded_chunks']) == job['total_chunks']:
            job['status'] = 'uploaded'
            log_user_action(session['username'], 'file_upload', f'Uploaded file: {job["original_name"]}')
            logger.info(f"Upload completed: {job['filename']} by {session['username']}")
        
        return jsonify({
            'status': 'success',
            'progress': progress,
            'uploaded_chunks': len(job['uploaded_chunks']),
            'total_chunks': job['total_chunks'],
            'upload_complete': job['status'] == 'uploaded'
        })
        
    except Exception as e:
        logger.error(f"Chunk upload error (job: {job_id}, chunk: {chunk_index}): {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload/status/<job_id>', methods=['GET'])
def upload_status(job_id):
    """Get upload progress status"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    
    return jsonify({
        'status': job['status'],
        'progress': job.get('upload_progress', 0),
        'uploaded_chunks': len(job.get('uploaded_chunks', set())),
        'total_chunks': job.get('total_chunks', 0),
        'filename': job.get('original_name', ''),
        'message': job.get('message', '')
    })

# Keep old upload endpoint for backward compatibility (deprecated)
@app.route('/upload', methods=['POST'])
def upload_file_legacy():
    """Legacy upload endpoint - deprecated, use chunked upload instead"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    job_id = request.form.get('job_id')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Unsupported file format: {file_ext}'}), 400
    
    try:
        # Create unique filename
        filename = f"{job_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file with streaming to handle large files
        CHUNK_SIZE = 16 * 1024  # 16KB chunks
        with open(filepath, 'wb') as f:
            while True:
                chunk = file.stream.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
        
        # Store job info
        active_jobs[job_id] = {
            'filename': filename,
            'filepath': filepath,
            'original_name': file.filename,
            'status': 'uploaded',
            'user': session['username']
        }
        
        log_user_action(session['username'], 'file_upload', f'Uploaded file: {file.filename}')
        logger.info(f"File uploaded: {filename} by {session['username']}")
        
        return jsonify({'job_id': job_id, 'status': 'uploaded'})
        
    except Exception as e:
        error_msg = f"Upload error for {file.filename}: {str(e)}"
        logger.error(error_msg)
        log_user_action(session['username'], 'file_upload_failed', error_msg)
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def start_processing():
    """Start video processing"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    job_id = request.json.get('job_id')
    
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
        
    # Start background processing
    active_jobs[job_id]['status'] = 'processing'
    thread = Thread(target=process_video_async, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'processing'})

def process_video_async(job_id):
    """Asynchronní zpracování videa"""
    try:
        job = active_jobs[job_id]
        input_path = job['filepath']
        original_name = job['original_name']
        
        # Generate output paths
        base_name = Path(original_name).stem
        output_video = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{base_name}_analyzed.mp4")
        output_csv = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{base_name}_analyzed.csv")  # FIX: Match main.py CSV output
        output_excel = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{base_name}_report.xlsx")
        
        job['progress'] = 20
        job['message'] = 'Spouští se ergonomická analýza...'
        
        # Use current python (should be conda python if app runs in conda environment)
        cmd1_str = f'"{sys.executable}" main.py "{input_path}" "{output_video}" --model-complexity 2 --csv-export --no-progress'
        
        # Set environment variables to handle encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result1 = subprocess.run(cmd1_str, capture_output=True, text=True, shell=True, cwd=os.getcwd(), env=env, encoding='utf-8', errors='ignore')
        
        if result1.returncode != 0:
            error_msg = f"Video processing failed. Return code: {result1.returncode}\nSTDERR: {result1.stderr}\nSTDOUT: {result1.stdout}\nCommand: {cmd1_str}"
            raise Exception(error_msg)
            
        job['progress'] = 60
        job['message'] = 'Analýza dokončena, vytvářím report...'
        
        # Get FPS from video file for accurate time calculations
        import cv2
        video_fps = 25.0  # Default fallback
        try:
            cap = cv2.VideoCapture(input_path)
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            if video_fps <= 0:
                video_fps = 25.0  # Fallback to default
            logger.info(f"Detected video FPS: {video_fps}")
        except Exception as fps_error:
            logger.warning(f"Could not detect video FPS: {fps_error}, using default 25.0")
        
        # Run analyze_ergonomics.py for Excel report with correct FPS
        cmd2_str = f'"{sys.executable}" analyze_ergonomics.py "{output_csv}" "{output_excel}" --fps {video_fps}'
        result2 = subprocess.run(cmd2_str, capture_output=True, text=True, shell=True, cwd=os.getcwd(), env=env, encoding='utf-8', errors='ignore')
        
        if result2.returncode != 0:
            error_msg = f"Excel generation failed. Return code: {result2.returncode}\nSTDERR: {result2.stderr}\nSTDOUT: {result2.stdout}\nCommand: {cmd2_str}"
            raise Exception(error_msg)
            
        job['progress'] = 100
        job['message'] = 'Analýza dokončena úspěšně!'
        job['status'] = 'completed'
        job['output_video'] = output_video
        job['output_excel'] = output_excel
        
        log_user_action(job['user'], 'processing_completed', f'Processed: {original_name}')
        logger.info(f"Processing completed for job {job_id}")
        logger.info(f"Job {job_id} files: video={job['output_video']}, excel={job['output_excel']}")
        
    except Exception as e:
        job['status'] = 'error'
        job['message'] = f'Chyba při zpracování: {str(e)}'
        logger.error(f"Processing error for job {job_id}: {str(e)}")

@app.route('/progress/<job_id>')
def get_progress(job_id):
    """SSE endpoint for progress updates"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    def generate():
        if job_id not in active_jobs:
            logger.error(f"SSE: Job {job_id} not found in active_jobs")
            yield f"data: {json.dumps({'status': 'error', 'message': 'Job not found'})}\n\n"
            return
            
        job = active_jobs[job_id]
        logger.info(f"SSE: Starting monitoring for job {job_id}, initial status: {job['status']}")
        last_progress = -1
        iterations = 0
        
        while iterations < 120:  # Max 2 minutes
            current_progress = job.get('progress', 0)
            current_status = job.get('status', 'unknown')
            current_message = job.get('message', 'Processing...')
            
            logger.debug(f"SSE: Job {job_id} iteration {iterations}, status: {current_status}, progress: {current_progress}")
            
            # Always send updates when progress changes or status changes
            if current_progress != last_progress or current_status in ['completed', 'error']:
                data = {
                    'status': current_status,
                    'progress': current_progress,
                    'message': current_message
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_progress = current_progress
                logger.info(f"SSE: Sent update for job {job_id}: {data}")
                
            if current_status == 'completed':
                # Send final completion message
                completion_data = {
                    'status': 'completed', 
                    'progress': 100,
                    'message': 'Analýza dokončena úspěšně!',
                    'results': {'video': job.get('output_video'), 'excel': job.get('output_excel')}
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                logger.info(f"SSE: Job {job_id} completed, sent final message: {completion_data}")
                break
            elif current_status == 'error':
                error_data = {
                    'status': 'error',
                    'message': job.get('message', 'Unknown error')
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                logger.error(f"SSE: Job {job_id} failed: {error_data}")
                break
                
            time.sleep(1)
            iterations += 1
        
        if iterations >= 120:
            logger.warning(f"SSE: Job {job_id} monitoring timed out after 2 minutes")
            yield f"data: {json.dumps({'status': 'timeout', 'message': 'Monitoring timed out'})}\n\n"
    
    return Response(generate(), mimetype='text/plain', headers={'Cache-Control': 'no-cache'})

@app.route('/status/<job_id>')
def get_job_status(job_id):
    """Simple polling endpoint for job status"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
        
    job = active_jobs[job_id]
    
    response_data = {
        'status': job.get('status', 'unknown'),
        'progress': job.get('progress', 0),
        'message': job.get('message', 'Processing...'),
    }
    
    if job.get('status') == 'completed':
        response_data['results'] = {
            'video': job.get('output_video'),
            'excel': job.get('output_excel')
        }
    
    logger.debug(f"Status poll for job {job_id}: {response_data}")
    return jsonify(response_data)

@app.route('/download/<job_id>/<file_type>')
def download_result(job_id, file_type):
    """Download processed files"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
        
    job = active_jobs[job_id]
    
    if job['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
        
    try:
        if file_type == 'video':
            filepath = job['output_video']
            filename = f"{Path(job['original_name']).stem}_analyzed.mp4"
        elif file_type == 'excel':
            filepath = job['output_excel']
            filename = f"{Path(job['original_name']).stem}_report.xlsx"
        else:
            return jsonify({'error': 'Invalid file type'}), 400
            
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
            
        log_user_action(session['username'], 'file_download', f'Downloaded: {filename}')
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large (max 5GB)'}), 413

@app.errorhandler(404)
def not_found(error):
    if 'username' not in session:
        return redirect(url_for('login'))
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Ergonomic Analysis Web Application")
    logger.info(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    logger.info(f"Output folder: {os.path.abspath(OUTPUT_FOLDER)}")
    logger.info(f"Log folder: {os.path.abspath(LOG_FOLDER)}")
    
    # Create test files if they don't exist
    if not os.path.exists('test.mp4') and os.path.exists('testw.mp4'):
        shutil.copy('testw.mp4', 'test.mp4')
        logger.info("Created test.mp4 symlink for testing")
    
    print("\n" + "="*60)
    print("ERGONOMIC ANALYSIS WEB APPLICATION")
    print("="*60)
    print(f"Server running at: http://localhost:5000")
    print(f"Demo accounts:")
    print(f"   - admin/admin123 (Administrator)")
    print(f"   - user1/user123 (Test User)")
    print(f"   - demo/demo123 (Demo User)")
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"Output folder: {os.path.abspath(OUTPUT_FOLDER)}")
    print(f"Logs folder: {os.path.abspath(LOG_FOLDER)}")
    print("="*60)
    print("Tip: Use Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)