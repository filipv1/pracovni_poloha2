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
from flask_mail import Mail, Message
import hashlib
import hmac
import base64
import requests

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Přidání src do Python path pro import modulů
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Emergency fix for high memory usage on Railway
try:
    import emergency_fix
    print("Emergency memory fix activated")
except ImportError:
    pass  # Emergency fix not available, continue normally

# Import optimizations if available
try:
    from railway_optimizations import optimize_app, OptimizedEmailWorker, CleanupManager, ResourceMonitor
    OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    OPTIMIZATIONS_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'ergonomic-analysis-2025-ultra-secure-key-change-in-production')

# Session configuration for long uploads
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # 2 hour session timeout
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Konfigurace
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs' 
LOG_FOLDER = 'logs'
JOBS_FOLDER = 'jobs'
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.m4v', '.wmv', '.flv', '.webm'}

# Vytvoření potřebných složek
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, LOG_FOLDER, JOBS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Flask konfigurace pro velké soubory
max_size = int(os.environ.get('MAX_UPLOAD_SIZE', 5 * 1024 * 1024 * 1024))  # Default 5GB
app.config['MAX_CONTENT_LENGTH'] = max_size
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Email konfigurace
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
# SMTP timeout configuration (30 seconds)
app.config['MAIL_TIMEOUT'] = int(os.environ.get('MAIL_TIMEOUT', 30))
app.config['MAIL_CONNECTION_TIMEOUT'] = int(os.environ.get('MAIL_CONNECTION_TIMEOUT', 30))

# Initialize Flask-Mail
mail = Mail(app)

# Production settings
if os.environ.get('FLASK_ENV') == 'production':
    # Optimalizace pro cloud deployment
    import gc
    gc.set_threshold(500, 5, 5)  # More aggressive garbage collection
    
    # Apply Railway optimizations if available
    if OPTIMIZATIONS_AVAILABLE:
        resource_monitor, cleanup_manager = optimize_app(app)
        logger.info("Railway optimizations applied")

# Whitelist uživatelů s email podporou
WHITELIST_USERS = {
    'korc': {
        'password': 'K7mN9xP2Qw', 
        'name': 'Korc',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'koska': {
        'password': 'R8vB3yT6Lm', 
        'name': 'Koška',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'licha': {
        'password': 'F5jH8wE9Xn', 
        'name': 'Licha',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'koutenska': {
        'password': 'M2nV7kR4Zs', 
        'name': 'Koutenská',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'kusinova': {
        'password': 'D9xC6tY3Bp', 
        'name': 'Kušinová',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'vagnerova': {
        'password': 'L4gW8fQ5Hm', 
        'name': 'Vágnerová',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'badrova': {
        'password': 'T7kN2vS9Rx', 
        'name': 'Badrová',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'henkova': {
        'password': 'P3mJ6wA8Qz', 
        'name': 'Henková',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    },
    'vaclavik': {
        'password': 'A9xL4pK7Fn', 
        'name': 'Václavík',
        'email': 'vaclavik.renturi@gmail.com',
        'email_notifications': True
    }
}

# Queue pro zpracování videí a emailů
processing_queue = Queue()
email_queue = Queue()
active_jobs = {}  # Zachováme pro kompatibilitu, ale budeme používat filesystem

# Email service a token systém
class EmailService:
    """Služba pro zasílání emailů s notifikacemi o dokončení analýzy"""
    
    def __init__(self, app, mail):
        self.app = app
        self.mail = mail
        self.secret_key = app.secret_key.encode()
    
    def generate_download_token(self, job_id, filename, expiry_hours=168):  # 7 days
        """Vygeneruje signed token pro secure download"""
        expiry_time = int(time.time()) + (expiry_hours * 3600)
        payload = f"{job_id}:{filename}:{expiry_time}"
        signature = hmac.new(self.secret_key, payload.encode(), hashlib.sha256).hexdigest()
        token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()
        return token
    
    def verify_download_token(self, token):
        """Ověří download token a vrátí (job_id, filename) nebo None"""
        try:
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            parts = decoded.split(':')
            if len(parts) != 4:
                return None
            
            job_id, filename, expiry_time, signature = parts
            
            # Verify signature
            payload = f"{job_id}:{filename}:{expiry_time}"
            expected_sig = hmac.new(self.secret_key, payload.encode(), hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(signature, expected_sig):
                return None
            
            # Check expiry
            if int(time.time()) > int(expiry_time):
                return None
            
            return job_id, filename
            
        except Exception:
            return None
    
    def create_completion_email(self, job_data):
        """Vytvoří email o dokončení analýzy"""
        username = job_data.get('username', 'Uživatel')
        user_info = WHITELIST_USERS.get(username, {})
        user_name = user_info.get('name', username)
        user_email = user_info.get('email')
        
        if not user_email:
            return None
        
        job_id = job_data.get('id')
        files = job_data.get('files', [])
        file_count = len(files)
        
        # Generate download links with proper server config
        download_links = []
        
        # Ensure SERVER_NAME is set for URL generation
        if not self.app.config.get('SERVER_NAME'):
            # Railway provides RAILWAY_STATIC_URL or we can construct from service name
            railway_url = os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('RAILWAY_PUBLIC_DOMAIN')
            if railway_url:
                self.app.config['SERVER_NAME'] = railway_url.replace('https://', '').replace('http://', '')
                self.app.config['PREFERRED_URL_SCHEME'] = 'https'
            else:
                # Fallback for Railway - construct domain
                self.app.config['SERVER_NAME'] = 'pracpol2-production.up.railway.app'
                self.app.config['PREFERRED_URL_SCHEME'] = 'https'
        
        for file_info in files:
            for output_type in ['video', 'report']:
                if output_type in file_info and file_info[output_type]:
                    filename = os.path.basename(file_info[output_type])
                    token = self.generate_download_token(job_id, filename)
                    try:
                        download_url = url_for('download_with_token', token=token, _external=True)
                    except:
                        # Fallback URL construction
                        base_url = f"https://{self.app.config.get('SERVER_NAME', 'localhost:5000')}"
                        download_url = f"{base_url}/download/token/{token}"
                    
                    download_links.append({
                        'filename': filename,
                        'type': 'Video s analýzou' if output_type == 'video' else 'Excel report',
                        'url': download_url
                    })
        
        # HTML email template
        html_body = self.get_email_template(user_name, file_count, download_links)
        
        # Text fallback
        text_body = self.get_text_email_template(user_name, file_count, download_links)
        
        # Add user identifier for Gmail filtering (same as Resend)
        user_tag = username.upper()
        
        msg = Message(
            subject=f"✅ [{user_tag}] Analýza dokončena - {file_count} souborů",
            recipients=[user_email],
            html=html_body,
            body=text_body
        )
        
        return msg
    
    def get_email_template(self, user_name, file_count, download_links):
        """HTML email template"""
        links_html = ""
        for link in download_links:
            links_html += f'''
            <tr>
                <td style="padding: 10px; background: #f8f9fa; border-radius: 8px; margin-bottom: 5px;">
                    <div style="font-weight: 600; color: #2d3748;">{link['filename']}</div>
                    <div style="color: #718096; font-size: 14px;">{link['type']}</div>
                    <a href="{link['url']}" style="display: inline-block; margin-top: 8px; padding: 8px 16px; background: #4299e1; color: white; text-decoration: none; border-radius: 6px; font-size: 14px;">Stáhnout</a>
                </td>
            </tr>
            '''
        
        return f'''
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #2d3748; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px; text-align: center; color: white; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 700;">Analýza dokončena!</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">Vaše soubory jsou připraveny ke stažení</p>
            </div>
            
            <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <p style="font-size: 18px; margin: 0 0 20px 0;">Ahoj {user_name}!</p>
                
                <p style="margin: 0 0 25px 0; color: #4a5568;">
                    Vaše analýza pracovní polohy byla úspěšně dokončena. 
                    Zpracovali jsme <strong>{file_count} souborů</strong> a výsledky jsou připraveny ke stažení.
                </p>
                
                <div style="margin: 25px 0;">
                    <h3 style="color: #2d3748; margin: 0 0 15px 0;">Soubory ke stažení:</h3>
                    <table style="width: 100%; border-collapse: separate; border-spacing: 0 8px;">
                        {links_html}
                    </table>
                </div>
                
                <div style="background: #e6fffa; padding: 15px; border-radius: 8px; border-left: 4px solid #38b2ac; margin: 25px 0;">
                    <p style="margin: 0; color: #285e61;">
                        <strong>Poznámka:</strong> Odkazy jsou platné po dobu 7 dní. 
                        Doporučujeme si soubory stáhnout co nejdříve.
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                    <p style="margin: 0; color: #718096; font-size: 14px;">
                        Děkujeme za použití naší aplikace pro analýzu pracovní polohy.
                    </p>
                </div>
            </div>
        </body>
        </html>
        '''
    
    def get_text_email_template(self, user_name, file_count, download_links):
        """Text email template jako fallback"""
        links_text = "\n".join([
            f"- {link['filename']} ({link['type']}): {link['url']}"
            for link in download_links
        ])
        
        return f'''
Ahoj {user_name}!

Vaše analýza pracovní polohy byla úspěšně dokončena.
Zpracovali jsme {file_count} souborů a výsledky jsou připraveny ke stažení.

Soubory ke stažení:
{links_text}

Poznámka: Odkazy jsou platné po dobu 7 dní. Doporučujeme si soubory stáhnout co nejdříve.

Děkujeme za použití naší aplikace pro analýzu pracovní polohy.
        '''
    
    def send_completion_email(self, job_data):
        """Pošle email o dokončení analýzy"""
        job_id = job_data.get('id')
        username = job_data.get('username')
        
        try:
            logger.info(f"Creating email message for job {job_id}, user {username}")
            msg = self.create_completion_email(job_data)
            
            if not msg:
                logger.warning(f"No email configured for user {username}")
                return False
            
            # Log SMTP connection attempt
            smtp_server = self.app.config.get('MAIL_SERVER')
            smtp_port = self.app.config.get('MAIL_PORT')
            logger.info(f"Attempting SMTP connection to {smtp_server}:{smtp_port} for job {job_id}")
            
            # Send email with timeout handling
            import socket
            original_timeout = socket.getdefaulttimeout()
            try:
                # Set socket timeout for SMTP operations
                socket.setdefaulttimeout(30)  # 30 second timeout
                
                logger.info(f"Sending email via Flask-Mail for job {job_id}")
                start_time = time.time()
                self.mail.send(msg)
                end_time = time.time()
                
                logger.info(f"Email sent successfully for job {job_id} in {end_time - start_time:.2f}s")
                return True
                
            finally:
                # Restore original timeout
                socket.setdefaulttimeout(original_timeout)
                
        except socket.timeout as e:
            logger.error(f"SMTP timeout for job {job_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email for job {job_id}: {type(e).__name__}: {e}")
            return False

class ResendEmailService:
    """HTTP API based email service using Resend.com"""
    
    def __init__(self, app):
        self.app = app
        self.secret_key = app.secret_key.encode()
        self.api_key = os.environ.get('RESEND_API_KEY')
        self.api_url = "https://api.resend.com/emails"
        self.enabled = bool(self.api_key)
        
    def generate_download_token(self, job_id, filename, expiry_hours=168):
        """Generate secure download token (same as EmailService)"""
        expiry_time = int(time.time()) + (expiry_hours * 3600)
        payload = f"{job_id}:{filename}:{expiry_time}"
        signature = hmac.new(self.secret_key, payload.encode(), hashlib.sha256).hexdigest()
        token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()
        return token
        
    def verify_download_token(self, token):
        """Verify download token (same as EmailService)"""
        try:
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            parts = decoded.split(':')
            if len(parts) != 4:
                return None
                
            job_id, filename, expiry_str, signature = parts
            
            # Verify signature
            expected_payload = f"{job_id}:{filename}:{expiry_str}"
            expected_signature = hmac.new(self.secret_key, expected_payload.encode(), hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
                
            # Check expiry
            expiry_time = int(expiry_str)
            if time.time() > expiry_time:
                return None
                
            return {'job_id': job_id, 'filename': filename}
        except Exception:
            return None
            
    def send_completion_email(self, job_data):
        """Send completion email via Resend HTTP API"""
        if not self.enabled:
            logger.error("Resend API key not configured")
            return False
            
        job_id = job_data.get('id')
        username = job_data.get('username')
        
        try:
            # Get user info
            user_info = WHITELIST_USERS.get(username, {})
            user_email = user_info.get('email')
            user_name = user_info.get('name', username)
            
            if not user_email:
                logger.warning(f"No email configured for user {username}")
                return False
                
            # Create download links
            files = job_data.get('files', [])
            download_links = []
            
            # Handle both list and dictionary formats for backward compatibility
            if isinstance(files, list):
                # New format: list of file objects
                for file_obj in files:
                    for file_type, filepath in file_obj.items():
                        if file_type != 'original_name' and filepath and os.path.exists(filepath):
                            filename = os.path.basename(filepath)
                            token = self.generate_download_token(job_id, filename)
                            # Get correct domain for Railway
                            server_name = self.app.config.get('SERVER_NAME') or os.environ.get('RAILWAY_STATIC_URL') or 'pracpol2-production.up.railway.app'
                            if server_name.startswith('http'):
                                download_url = f"{server_name}/download/token/{token}"
                            else:
                                download_url = f"https://{server_name}/download/token/{token}"
                            
                            download_links.append({
                                'filename': filename,
                                'type': file_type,
                                'url': download_url
                            })
            else:
                # Legacy format: dictionary
                for file_type, filepath in files.items():
                    if filepath and os.path.exists(filepath):
                        filename = os.path.basename(filepath)
                        token = self.generate_download_token(job_id, filename)
                        # Get correct domain for Railway
                        server_name = self.app.config.get('SERVER_NAME') or os.environ.get('RAILWAY_STATIC_URL') or 'pracpol2-production.up.railway.app'
                        if server_name.startswith('http'):
                            download_url = f"{server_name}/download/token/{token}"
                        else:
                            download_url = f"https://{server_name}/download/token/{token}"
                        
                        download_links.append({
                            'filename': filename,
                            'type': file_type,
                            'url': download_url
                        })
            
            if not download_links:
                logger.warning(f"No files to send for job {job_id}")
                return False
                
            # Prepare email data for Resend API
            file_count = len(download_links)
            html_body = self.get_email_template(user_name, file_count, download_links)
            
            # For Resend free plan, we can only send to the registered email
            # In production, you would verify a domain to send to any email
            registered_email = "vaclavik.renturi@gmail.com"  # Resend registered email
            
            # Add user identifier for Gmail filtering
            user_tag = username.upper()  # Convert to uppercase for visibility
            
            email_data = {
                "from": "Ergonomic Analysis <onboarding@resend.dev>",  # Resend sandbox domain
                "to": [registered_email],  # Use registered email for free plan
                "subject": f"✅ [{user_tag}] Analýza dokončena - {file_count} souborů",
                "html": html_body
            }
            
            # Send via Resend HTTP API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Sending email via Resend API for job {job_id} to {user_email}")
            start_time = time.time()
            
            response = requests.post(
                self.api_url, 
                json=email_data, 
                headers=headers,
                timeout=30
            )
            
            end_time = time.time()
            
            if response.status_code == 200:
                logger.info(f"Resend API: Email sent successfully for job {job_id} in {end_time - start_time:.2f}s")
                return True
            else:
                logger.error(f"Resend API error for job {job_id}: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"Resend API timeout for job {job_id}")
            return False
        except Exception as e:
            logger.error(f"Resend API error for job {job_id}: {type(e).__name__}: {e}")
            return False
            
    def get_email_template(self, user_name, file_count, download_links):
        """HTML email template (same as EmailService)"""
        links_html = ""
        for link in download_links:
            file_type_display = {
                'video': 'Analyzované video',
                'excel': 'Excel report',
                'csv': 'CSV data'
            }.get(link['type'], link['type'])
            
            links_html += f'''
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    <strong>{file_type_display}:</strong> {link['filename']}<br>
                    <a href="{link['url']}" style="color: #007bff; text-decoration: none;">📥 Stáhnout soubor</a>
                </td>
            </tr>
            '''
        
        return f'''
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px;">✅ Analýza dokončena!</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Vaše soubory jsou připravené ke stažení</p>
                </div>
                
                <div style="padding: 30px;">
                    <p style="font-size: 18px; color: #333; margin-bottom: 20px;">Dobrý den {user_name},</p>
                    
                    <p style="color: #666; line-height: 1.6; margin-bottom: 25px;">
                        vaše analýza pracovní polohy byla úspěšně dokončena. Připravili jsme pro vás <strong>{file_count} souborů</strong> ke stažení.
                    </p>
                    
                    <div style="background-color: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                        <h3 style="color: #333; margin: 0 0 15px 0;">📁 Vaše soubory:</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            {links_html}
                        </table>
                    </div>
                    
                    <div style="background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin-bottom: 20px;">
                        <p style="margin: 0; color: #1976d2; font-size: 14px;">
                            <strong>ℹ️ Důležité informace:</strong><br>
                            • Odkazy jsou platné 7 dní<br>
                            • Soubory jsou zabezpečené pomocí tokenů<br>
                            • Pro stažení klikněte na odkaz výše
                        </p>
                    </div>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #eee;">
                    <p style="margin: 0; color: #666; font-size: 14px;">
                        Děkujeme za použití naší aplikace pro analýzu pracovní polohy.
                    </p>
                </div>
            </div>
        </body>
        </html>
        '''


class HybridEmailService:
    """Hybrid email service that tries HTTP API first, then falls back to SMTP"""
    
    def __init__(self, app, mail):
        self.smtp_service = EmailService(app, mail)
        self.resend_service = ResendEmailService(app)
        self.app = app
        
    def generate_download_token(self, job_id, filename, expiry_hours=168):
        # Use Resend service for token generation (both are identical)
        return self.resend_service.generate_download_token(job_id, filename, expiry_hours)
        
    def verify_download_token(self, token):
        # Use Resend service for token verification (both are identical)
        return self.resend_service.verify_download_token(token)
        
    def send_completion_email(self, job_data):
        """Try Resend API first, fallback to SMTP if it fails"""
        job_id = job_data.get('id')
        
        # Try Resend HTTP API first (preferred on Railway)
        if self.resend_service.enabled:
            logger.info(f"Attempting Resend HTTP API for job {job_id}")
            if self.resend_service.send_completion_email(job_data):
                logger.info(f"Email sent via Resend HTTP API for job {job_id}")
                return True
            else:
                logger.warning(f"Resend HTTP API failed for job {job_id}, trying SMTP fallback")
        
        # Fallback to SMTP (will work on Railway Pro plan or other platforms)
        logger.info(f"Attempting SMTP fallback for job {job_id}")
        if self.smtp_service.send_completion_email(job_data):
            logger.info(f"Email sent via SMTP fallback for job {job_id}")
            return True
        else:
            logger.error(f"Both Resend API and SMTP failed for job {job_id}")
            return False


# Initialize hybrid email service (HTTP API + SMTP fallback)
email_service = HybridEmailService(app, mail)

# Job persistence functions
def save_job(job_id, job_data):
    """Save job data to JSON file"""
    job_file = os.path.join(JOBS_FOLDER, f"{job_id}.json")
    temp_file = f"{job_file}.tmp"
    
    try:
        # Add timestamp if not present
        if 'updated_at' not in job_data:
            job_data['updated_at'] = time.time()
        
        # Atomic write using temp file
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)
        
        # Atomic rename
        os.replace(temp_file, job_file)
        
        # Also update in-memory cache
        active_jobs[job_id] = job_data
        
    except Exception as e:
        logger.error(f"Failed to save job {job_id}: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

def load_job(job_id):
    """Load job data from JSON file"""
    # First check memory cache
    if job_id in active_jobs:
        return active_jobs[job_id]
    
    job_file = os.path.join(JOBS_FOLDER, f"{job_id}.json")
    
    try:
        if os.path.exists(job_file):
            with open(job_file, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Update memory cache
            active_jobs[job_id] = job_data
            return job_data
    except Exception as e:
        logger.error(f"Failed to load job {job_id}: {e}")
    
    return None

def delete_job(job_id):
    """Delete job data and files"""
    job_file = os.path.join(JOBS_FOLDER, f"{job_id}.json")
    chunks_file = os.path.join(JOBS_FOLDER, f"{job_id}.chunks")
    
    try:
        if os.path.exists(job_file):
            os.remove(job_file)
        if os.path.exists(chunks_file):
            os.remove(chunks_file)
        
        # Remove from memory
        if job_id in active_jobs:
            del active_jobs[job_id]
            
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")

def save_uploaded_chunk(job_id, chunk_index):
    """Track uploaded chunks for resume capability"""
    chunks_file = os.path.join(JOBS_FOLDER, f"{job_id}.chunks")
    
    try:
        # Load existing chunks
        chunks = set()
        if os.path.exists(chunks_file):
            with open(chunks_file, 'r') as f:
                chunks = set(json.load(f))
        
        # Add new chunk
        chunks.add(chunk_index)
        
        # Save back
        with open(chunks_file, 'w') as f:
            json.dump(list(chunks), f)
            
        return True
    except Exception as e:
        logger.error(f"Failed to save chunk {chunk_index} for job {job_id}: {e}")
        return False

def get_uploaded_chunks(job_id):
    """Get list of uploaded chunks"""
    chunks_file = os.path.join(JOBS_FOLDER, f"{job_id}.chunks")
    
    try:
        if os.path.exists(chunks_file):
            with open(chunks_file, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        logger.error(f"Failed to load chunks for job {job_id}: {e}")
    
    return set()

# Cleanup old upload sessions on startup
def cleanup_old_sessions():
    """Clean up old upload sessions and incomplete files"""
    try:
        # More aggressive cleanup in production
        if os.environ.get('FLASK_ENV') == 'production':
            cutoff_time = datetime.now() - timedelta(hours=12)  # 12 hours in production
        else:
            cutoff_time = datetime.now() - timedelta(hours=24)  # 24 hours in dev
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

# Email worker thread - Use optimized version if available
if OPTIMIZATIONS_AVAILABLE and os.environ.get('FLASK_ENV') == 'production':
    # Use optimized email worker for production
    optimized_worker = OptimizedEmailWorker(email_queue, email_service, app)
    optimized_worker.start()
    logger.info("Using optimized email worker")
else:
    # Original email worker
    def email_worker():
        """Background worker pro zasílání emailů"""
        logger.info("Email worker started - ready to process emails")
        
        while True:
            try:
                # Čeká na email úlohu v queue (timeout 30s)
                email_task = email_queue.get(timeout=30)
                
                if email_task is None:  # Shutdown signal
                    logger.info("Email worker received shutdown signal")
                    break
                    
                job_data = email_task.get('job_data')
                retry_count = email_task.get('retry_count', 0)
                job_id = job_data.get('id')
                
                logger.info(f"Email worker: Processing job {job_id}, attempt {retry_count + 1}")
                
                # Pokus o odeslání emailu s aplikačním kontextem a timeoutem
                try:
                    worker_start_time = time.time()
                    with app.app_context():
                        success = email_service.send_completion_email(job_data)
                    worker_end_time = time.time()
                
                    logger.info(f"Email worker: Email processing completed for job {job_id} in {worker_end_time - worker_start_time:.2f}s, success: {success}")
                    
                    if success:
                        # Email odeslán úspěšně
                        job_data['email_sent'] = True
                        job_data['email_sent_at'] = time.time()
                        save_job(job_id, job_data)
                        logger.info(f"Email worker: Successfully processed and saved job {job_id}")
                    else:
                        # Email se nepodařilo odeslat
                        if retry_count < 2:  # Maximálně 3 pokusy (0, 1, 2)
                            # Exponential backoff: 30s, 60s, 120s (shorter for faster debugging)
                            retry_delay = 30 * (2 ** retry_count)
                            logger.warning(f"Email worker: Job {job_id} failed, scheduling retry {retry_count + 2}/3 in {retry_delay}s")
                            
                            # Zaplanuj retry
                            def retry_email():
                                time.sleep(retry_delay)
                                logger.info(f"Email worker: Retrying job {job_id} after {retry_delay}s delay")
                                email_queue.put({
                                    'job_data': job_data,
                                    'retry_count': retry_count + 1
                                })
                            
                            Thread(target=retry_email, daemon=True).start()
                        else:
                            logger.error(f"Email worker: Job {job_id} permanently failed after 3 attempts")
                            job_data['email_failed'] = True
                            job_data['email_failed_at'] = time.time()
                            save_job(job_id, job_data)
                            
                except Exception as email_error:
                    logger.error(f"Email worker: Error processing job {job_id}: {type(email_error).__name__}: {email_error}")
                    # This counts as a failure, will be retried if retries remain
                    if retry_count < 2:
                        retry_delay = 30 * (2 ** retry_count)
                        logger.warning(f"Email worker: Exception for job {job_id}, scheduling retry in {retry_delay}s")
                        
                        def retry_email():
                            time.sleep(retry_delay)
                            email_queue.put({
                                'job_data': job_data,
                                'retry_count': retry_count + 1
                            })
                        
                        Thread(target=retry_email, daemon=True).start()
                    else:
                        logger.error(f"Email worker: Job {job_id} permanently failed due to exception after 3 attempts")
                        job_data['email_failed'] = True
                        job_data['email_failed_at'] = time.time()
                        job_data['email_error'] = str(email_error)
                        save_job(job_id, job_data)
                
                email_queue.task_done()
                
            except Exception as worker_error:
                # Ignoruj normální queue timeout chyby (Queue.Empty exception)
                if "empty" not in str(worker_error).lower() and "timeout" not in str(worker_error).lower():
                    logger.error(f"Email worker: Unexpected error in main loop: {type(worker_error).__name__}: {worker_error}")
                continue

    # Spuštění email worker threadu (only for non-optimized version)
    if not (OPTIMIZATIONS_AVAILABLE and os.environ.get('FLASK_ENV') == 'production'):
        email_worker_thread = Thread(target=email_worker, daemon=True)
        email_worker_thread.start()

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
        
        /* Individual Progress Toast styles */
        .progress-toast {
            animation: slideInRight 0.3s ease-out;
            max-height: 200px;
            overflow: hidden;
        }
        
        .progress-toast:hover {
            transform: translateX(-5px);
            transition: transform 0.2s ease;
        }
        
        @keyframes slideInRight {
            from { 
                opacity: 0; 
                transform: translateX(100px); 
            } 
            to { 
                opacity: 1; 
                transform: translateX(0); 
            }
        }
        
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
        // Generate secure download link using token system (same as emails)
        async function generateDownloadLink(jobId, fileType) {
            try {
                console.log(`Generating download link for job ${jobId}, type ${fileType}`);
                const response = await fetch(`/api/generate-download-token/${jobId}/${fileType}`);
                const data = await response.json();
                
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                
                console.log('Download URL generated:', data.download_url);
                // Open download link in new tab
                window.open(data.download_url, '_blank');
            } catch (error) {
                console.error('Download error:', error);
                alert('Chyba při generování download linku');
            }
        }
        
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
    
    <!-- Individual Progress Toasts Container -->
    <div id="progress-toasts-container" class="fixed bottom-20 right-4 space-y-3 pointer-events-none z-50">
        <!-- Individual progress windows for each file will be dynamically created here -->
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
    const progressToastsContainer = document.getElementById('progress-toasts-container');
    
    // Heartbeat to keep session alive during long uploads
    let heartbeatInterval = null;
    
    function startHeartbeat() {
        if (heartbeatInterval) return;
        
        heartbeatInterval = setInterval(async () => {
            try {
                await fetch('/keep-alive');
            } catch (e) {
                console.log('Heartbeat failed:', e);
            }
        }, 30000); // Every 30 seconds
    }
    
    function stopHeartbeat() {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    }
    
    let selectedFiles = [];
    let activeJobs = {};

    // Create individual progress window for each file
    function createProgressToast(jobId, filename) {
        const toast = document.createElement('div');
        toast.id = `progress-toast-${jobId}`;
        toast.className = 'progress-toast pointer-events-auto fade-in';
        
        toast.innerHTML = `
            <div class="alert alert-info relative min-w-[400px] max-w-[500px]">
                <button onclick="removeProgressToast('${jobId}')" class="absolute top-2 right-2 btn btn-ghost btn-xs">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
                <div class="pr-6">
                    <div class="flex items-center mb-2">
                        <div class="spin-animation w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-3"></div>
                        <div class="flex-1">
                            <div class="font-semibold text-sm" id="progress-title-${jobId}">Zpracovávám...</div>
                            <div class="text-xs text-gray-600 truncate" title="${filename}">${filename}</div>
                            <div class="text-sm" id="progress-detail-${jobId}">Prosím počkejte</div>
                        </div>
                    </div>
                    
                    <!-- Frame counter section -->
                    <div id="frame-counter-${jobId}" class="hidden text-sm space-y-1 mb-2">
                        <div class="flex justify-between">
                            <span>Snímky:</span>
                            <span id="frame-progress-${jobId}">0 / 0</span>
                        </div>
                        <div class="flex justify-between text-opacity-75">
                            <span>Detekováno:</span>
                            <span id="detected-frames-${jobId}">0</span>
                        </div>
                    </div>
                    
                    <div class="w-full bg-base-300 rounded-full h-2 mt-2">
                        <div id="progress-bar-${jobId}" class="bg-primary h-2 rounded-full progress-bar transition-all duration-500" style="width: 0%"></div>
                    </div>
                </div>
            </div>
        `;
        
        progressToastsContainer.appendChild(toast);
        return toast;
    }

    // Remove individual progress toast
    function removeProgressToast(jobId) {
        const toast = document.getElementById(`progress-toast-${jobId}`);
        if (toast) {
            toast.remove();
        }
    }

    // Update individual progress toast
    function updateIndividualProgress(jobId, message, percent, data = null) {
        const titleEl = document.getElementById(`progress-title-${jobId}`);
        const detailEl = document.getElementById(`progress-detail-${jobId}`);
        const barEl = document.getElementById(`progress-bar-${jobId}`);
        
        if (titleEl) titleEl.textContent = message;
        if (detailEl) detailEl.textContent = `${Math.round(percent)}% dokončeno`;
        if (barEl) barEl.style.width = `${percent}%`;
        
        // Update frame counters if data provided
        if (data && data.current_frame && data.total_frames) {
            const frameCounterEl = document.getElementById(`frame-counter-${jobId}`);
            const frameProgressEl = document.getElementById(`frame-progress-${jobId}`);
            const detectedFramesEl = document.getElementById(`detected-frames-${jobId}`);
            
            if (frameCounterEl) frameCounterEl.classList.remove('hidden');
            if (frameProgressEl) frameProgressEl.textContent = `${data.current_frame} / ${data.total_frames}`;
            if (detectedFramesEl) detectedFramesEl.textContent = data.detected_frames || 0;
        }
    }

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

        // Add jobId to each file
        const filesWithJobId = validFiles.map(file => ({
            file: file,
            jobId: generateUUID()
        }));

        selectedFiles = [...selectedFiles, ...filesWithJobId];
        updateFileList();
        fileList.classList.remove('hidden');
        startProcessing.disabled = false;
    }

    function updateFileList() {
        filesContainer.innerHTML = '';
        selectedFiles.forEach((fileObj, index) => {
            const file = fileObj.file; // Extract the File object
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
        resultsSection.classList.remove('hidden');
        
        // Create individual progress toasts for each file
        selectedFiles.forEach(file => {
            const jobId = file.jobId;
            createProgressToast(jobId, file.file.name);
            uploadAndProcess(file);
        });
    });

    async function uploadAndProcess(fileObj) {
        // Start heartbeat for long uploads
        startHeartbeat();
        
        const file = fileObj.file;
        const jobId = fileObj.jobId;
        
        // Update progress toast for this specific file
        updateIndividualProgress(jobId, 'Nahrávám soubor...', 0);
        
        const uploadJobId = await chunkedUpload(file, jobId);
        if (!uploadJobId) {
            stopHeartbeat();
            updateIndividualProgress(jobId, 'Chyba při nahrávání!', 0);
            return; // Upload failed
        }
        
        try {
            // Use the server job ID for all further operations
            const serverJobId = uploadJobId;
            updateIndividualProgress(serverJobId, `Zpracovávám ${file.name}`, 30);
            
            // Start processing
            const processResponse = await fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id: serverJobId })
            });
            
            if (!processResponse.ok) throw new Error('Processing failed');
            
            // Monitor progress
            monitorJob(serverJobId);
            
        } catch (error) {
            console.error('Error:', error);
            showError(`Chyba při zpracování ${file.name}: ${error.message}`);
        }
    }

    async function chunkedUpload(file, jobId) {
        const CHUNK_SIZE = 1024 * 1024; // 1MB chunks
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
        const startTime = Date.now();
        let uploadedBytes = 0;
        
        // Format file size
        function formatBytes(bytes) {
            if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
            return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        }
        
        // Format time
        function formatTime(seconds) {
            if (seconds < 60) return `${Math.round(seconds)}s`;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.round(seconds % 60);
            return `${minutes}m ${remainingSeconds}s`;
        }
        
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
            const serverJobId = job_id;
            activeJobs[serverJobId] = { file: file.name, status: 'uploading', originalFile: file };
            
            // Update the progress toast to use the correct server job_id
            removeProgressToast(jobId);
            createProgressToast(serverJobId, file.name);
            
            // Check for existing upload to resume
            let uploadedChunks = new Set();
            try {
                const resumeResponse = await fetch(`/upload/resume/${serverJobId}`);
                if (resumeResponse.ok) {
                    const resumeData = await resumeResponse.json();
                    if (resumeData.uploaded_chunks) {
                        uploadedChunks = new Set(resumeData.uploaded_chunks);
                        console.log(`Resuming upload: ${uploadedChunks.size}/${total_chunks} chunks already uploaded`);
                    }
                }
            } catch (e) {
                console.log('No resume data available, starting fresh');
            }
            
            // Upload chunks (skip already uploaded ones)
            for (let chunkIndex = 0; chunkIndex < total_chunks; chunkIndex++) {
                // Skip if chunk already uploaded
                if (uploadedChunks.has(chunkIndex)) {
                    console.log(`Skipping already uploaded chunk ${chunkIndex}`);
                    continue;
                }
                const start = chunkIndex * chunk_size;
                const end = Math.min(start + chunk_size, file.size);
                const chunk = file.slice(start, end);
                
                // Calculate upload stats
                uploadedBytes = Math.min(end, file.size); // Use end of current chunk, not start
                const elapsedSeconds = Math.max(0.1, (Date.now() - startTime) / 1000); // Avoid division by zero
                const uploadSpeed = uploadedBytes / elapsedSeconds; // bytes per second
                const remainingBytes = file.size - uploadedBytes;
                const eta = uploadSpeed > 0 ? remainingBytes / uploadSpeed : 0;
                
                const progress = Math.round((chunkIndex / total_chunks) * 25); // Upload is 0-25% of total progress
                const uploadMessage = `Nahrávám: ${formatBytes(uploadedBytes)} / ${formatBytes(file.size)} (${formatBytes(uploadSpeed)}/s) - zbývá ${formatTime(eta)}`;
                
                updateIndividualProgress(serverJobId, uploadMessage, progress, {
                    upload_phase: true,
                    uploaded_bytes: uploadedBytes,
                    total_bytes: file.size,
                    upload_speed: uploadSpeed,
                    eta_seconds: eta
                });
                
                // Upload chunk with retry logic
                let retryCount = 0;
                const maxRetries = 3;
                
                while (retryCount < maxRetries) {
                    try {
                        const chunkResponse = await fetch(`/upload/chunk/${serverJobId}/${chunkIndex}`, {
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
            
            // Final upload stats
            const totalTime = (Date.now() - startTime) / 1000;
            const avgSpeed = file.size / totalTime;
            updateIndividualProgress(serverJobId, `Upload dokončen: ${formatBytes(file.size)} za ${formatTime(totalTime)} (průměr ${formatBytes(avgSpeed)}/s)`, 25);
            return serverJobId;
            
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
                
                // Update individual job progress
                activeJobs[jobId].progress = data.progress;
                activeJobs[jobId].message = data.message;
                activeJobs[jobId].current_frame = data.current_frame;
                activeJobs[jobId].total_frames = data.total_frames;
                
                // Update individual progress toast
                updateIndividualProgress(jobId, data.message, data.progress, {
                    current_frame: data.current_frame,
                    total_frames: data.total_frames,
                    detected_frames: data.detected_frames
                });
                
                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    activeJobs[jobId].status = 'completed';
                    activeJobs[jobId].progress = 100;
                    
                    // Show completion in individual progress toast
                    updateIndividualProgress(jobId, 'Analýza dokončena úspěšně!', 100);
                    
                    // Auto-hide completed toast after 5 seconds
                    setTimeout(() => {
                        removeProgressToast(jobId);
                    }, 5000);
                    
                    addResult(jobId, data.results);
                    checkAllJobsCompleted();
                } else if (data.status === 'error') {
                    clearInterval(pollInterval);
                    activeJobs[jobId].status = 'error';
                    
                    // Show error in individual progress toast
                    updateIndividualProgress(jobId, 'Chyba při zpracování!', 0);
                    
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
                    <button onclick="fetch('/api/generate-download-token/${jobId}/video').then(r=>r.json()).then(d=>d.error?alert('Error: '+d.error):window.open(d.download_url,'_blank')).catch(e=>alert('Chyba: '+e.message))" class="btn btn-sm btn-primary">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-4-4m4 4l4-4m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                        </svg>
                        Video
                    </button>
                    <button onclick="fetch('/api/generate-download-token/${jobId}/excel').then(r=>r.json()).then(d=>d.error?alert('Error: '+d.error):window.open(d.download_url,'_blank')).catch(e=>alert('Chyba: '+e.message))" class="btn btn-sm btn-success">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-4-4m4 4l4-4m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path>
                        </svg>
                        Excel
                    </button>
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
            // Show completion message
            const completedCount = Object.values(activeJobs).filter(job => job.status === 'completed').length;
            const totalCount = Object.keys(activeJobs).length;
            console.log(`Všechno dokončeno! (${completedCount}/${totalCount} úspěšně)`);
            
            // Stop heartbeat when all jobs complete
            stopHeartbeat();
            
            // Re-enable start processing button
            startProcessing.disabled = false;
        }
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

@app.route('/keep-alive')
def keep_alive():
    """Keep session alive during long uploads"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Refresh session
    session.permanent = True
    session.modified = True
    
    return jsonify({
        'status': 'alive',
        'timestamp': time.time(),
        'user': session['username']
    })

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

@app.route('/upload/resume/<job_id>')
def get_upload_status(job_id):
    """Get upload status for resume capability"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'Upload session not found'}), 404
    
    uploaded_chunks = get_uploaded_chunks(job_id)
    
    return jsonify({
        'job_id': job_id,
        'status': job.get('status'),
        'uploaded_chunks': list(uploaded_chunks),
        'total_chunks': job.get('total_chunks'),
        'chunk_size': job.get('chunk_size'),
        'progress': len(uploaded_chunks) / job.get('total_chunks', 1) * 100
    })

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
    job_data = {
        'job_id': job_id,
        'filename': upload_filename,
        'filepath': upload_filepath,
        'original_name': filename,
        'filesize': filesize,
        'chunk_size': chunk_size,
        'total_chunks': total_chunks,
        'status': 'uploading',
        'upload_progress': 0,
        'user': session['username'],
        'created_at': datetime.now().isoformat(),
        'updated_at': time.time()
    }
    save_job(job_id, job_data)
    
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
    
    # Load job from persistent storage
    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'Upload session not found'}), 404
    
    if job['status'] != 'uploading':
        return jsonify({'error': 'Upload session not active'}), 400
    
    if chunk_index >= job['total_chunks'] or chunk_index < 0:
        return jsonify({'error': 'Invalid chunk index'}), 400
    
    # Check if chunk already uploaded (for resumability)
    uploaded_chunks = get_uploaded_chunks(job_id)
    if chunk_index in uploaded_chunks:
        return jsonify({'status': 'already_uploaded', 'progress': len(uploaded_chunks) / job['total_chunks'] * 100})
    
    try:
        # Get chunk data
        chunk_data = request.get_data()
        if not chunk_data:
            return jsonify({'error': 'No chunk data received'}), 400
        
        # Write chunk to file
        with open(job['filepath'], 'r+b') as f:
            f.seek(chunk_index * job['chunk_size'])
            f.write(chunk_data)
        
        # Save uploaded chunk for resume capability
        save_uploaded_chunk(job_id, chunk_index)
        
        # Update progress
        uploaded_chunks = get_uploaded_chunks(job_id)
        progress = len(uploaded_chunks) / job['total_chunks'] * 100
        job['upload_progress'] = progress
        job['updated_at'] = time.time()
        
        # Check if upload is complete
        if len(uploaded_chunks) == job['total_chunks']:
            job['status'] = 'uploaded'
            log_user_action(session['username'], 'file_upload', f'Uploaded file: {job["original_name"]}')
            logger.info(f"Upload completed: {job['filename']} by {session['username']}")
        
        # Save updated job data
        save_job(job_id, job)
        
        return jsonify({
            'status': 'success',
            'progress': progress,
            'uploaded_chunks': len(uploaded_chunks),
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
    logger.info(f"Processing request received for job {job_id}")
    
    if job_id not in active_jobs:
        logger.error(f"Job {job_id} not found in active_jobs")
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    logger.info(f"Job {job_id} current status: {job.get('status')}, file: {job.get('original_name')}")
        
    # Start background processing
    active_jobs[job_id]['status'] = 'processing'
    thread = Thread(target=process_video_async, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    logger.info(f"Started processing thread for job {job_id}")
    return jsonify({'status': 'processing'})

def monitor_progress_file(job_id, progress_file, process):
    """Monitor progress file and update job status"""
    job = active_jobs[job_id]
    last_update = 0
    
    logger.info(f"Starting progress monitoring for job {job_id}, progress file: {progress_file}")
    
    try:
        while process.poll() is None:  # While process is running
            if os.path.exists(progress_file):
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                    
                    # Update job with detailed progress
                    job['progress'] = min(90, 20 + (progress_data['percent'] * 0.7))  # Scale to 20-90%
                    job['current_frame'] = progress_data.get('current_frame', 0)
                    job['total_frames'] = progress_data.get('total_frames', 0)
                    job['phase'] = progress_data.get('phase', 'processing')
                    job['message'] = progress_data.get('message', 'Zpracovávám video...')
                    job['detected_frames'] = progress_data.get('detected_frames', 0)
                    job['bend_frames'] = progress_data.get('bend_frames', 0)
                    job['failed_detections'] = progress_data.get('failed_detections', 0)
                    
                    last_update = time.time()
                except Exception as e:
                    logger.debug(f"Could not read progress file: {e}")
            
            time.sleep(0.5)  # Check every 500ms
    
    except Exception as e:
        logger.error(f"Progress monitoring error for job {job_id}: {e}")
    
    finally:
        # Clean up progress file
        if os.path.exists(progress_file):
            try:
                os.remove(progress_file)
            except:
                pass

def process_video_async(job_id):
    """Asynchronní zpracování videa"""
    try:
        logger.info(f"=== THREAD STARTED: process_video_async for job {job_id} ===")
        if job_id not in active_jobs:
            logger.error(f"CRITICAL: Job {job_id} not found in active_jobs when thread started!")
            return
        
        job = active_jobs[job_id]
        logger.info(f"Thread {job_id}: Job found, original_name: {job.get('original_name')}")
        input_path = job['filepath']
        original_name = job['original_name']
        logger.info(f"Processing {original_name}, input path: {input_path}")
        
        # Generate output paths
        base_name = Path(original_name).stem
        output_video = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{base_name}_analyzed.mp4")
        output_csv = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{base_name}_analyzed.csv")  # FIX: Match main.py CSV output
        output_excel = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_{base_name}_report.xlsx")
        
        job['progress'] = 20
        job['message'] = 'Spouští se ergonomická analýza...'
        
        # Create progress file path
        progress_file = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_progress.json")
        job['progress_file'] = progress_file
        
        # Use current python (should be conda python if app runs in conda environment)
        cmd1_str = f'"{sys.executable}" main.py "{input_path}" "{output_video}" --model-complexity 2 --csv-export --no-progress --progress-file "{progress_file}"'
        
        # Set environment variables to handle encoding
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'  # Ensure unbuffered output
        
        # Start subprocess
        process1 = subprocess.Popen(cmd1_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   shell=True, cwd=os.getcwd(), env=env, 
                                   encoding='utf-8', errors='ignore')
        
        # Start progress monitoring thread
        monitor_thread = Thread(target=monitor_progress_file, args=(job_id, progress_file, process1))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Wait for process to complete
        stdout, stderr = process1.communicate()
        
        if process1.returncode != 0:
            error_msg = f"Video processing failed. Return code: {process1.returncode}\nSTDERR: {stderr}\nSTDOUT: {stdout}\nCommand: {cmd1_str}"
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
        job['completed_at'] = time.time()
        
        # Update job data structure for email compatibility
        if 'files' not in job:
            job['files'] = []
        
        job['files'].append({
            'original_name': original_name,
            'video': output_video,
            'report': output_excel
        })
        
        # Save completed job
        save_job(job_id, job)
        
        log_user_action(job['user'], 'processing_completed', f'Processed: {original_name}')
        logger.info(f"Processing completed for job {job_id}")
        logger.info(f"Job {job_id} files: video={job['output_video']}, excel={job['output_excel']}")
        
        # Trigger email notification if user has email notifications enabled
        username = job.get('username') or job.get('user')  # Kompatibilita se starými daty
        user_info = WHITELIST_USERS.get(username, {})
        
        if user_info.get('email_notifications', False) and user_info.get('email'):
            logger.info(f"Queuing email notification for user {username}")
            email_queue.put({
                'job_data': {
                    'id': job_id,
                    'username': username,
                    'files': job['files'],
                    'status': 'completed',
                    'completed_at': job['completed_at']
                },
                'retry_count': 0
            })
        else:
            logger.info(f"Email notifications disabled or no email configured for user {username}")
        
    except Exception as e:
        logger.error(f"=== THREAD ERROR: process_video_async for job {job_id} ===")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Job data at time of error: {active_jobs.get(job_id, 'Job not found')}")
        
        if job_id in active_jobs:
            job = active_jobs[job_id]
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
                    'message': current_message,
                    'phase': job.get('phase', 'processing'),
                    'current_frame': job.get('current_frame', 0),
                    'total_frames': job.get('total_frames', 0),
                    'detected_frames': job.get('detected_frames', 0),
                    'bend_frames': job.get('bend_frames', 0),
                    'failed_detections': job.get('failed_detections', 0)
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                last_progress = current_progress
                logger.info(f"SSE: Sent update for job {job_id}: status={current_status}, progress={current_progress}, frames={data.get('current_frame')}/{data.get('total_frames')}")
                
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
        
    # Use in-memory cache first for active progress, fallback to disk
    if job_id in active_jobs:
        job = active_jobs[job_id]
    else:
        job = load_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
    
    response_data = {
        'status': job.get('status', 'unknown'),
        'progress': job.get('progress', 0),
        'message': job.get('message', 'Processing...'),
        'current_frame': job.get('current_frame', 0),
        'total_frames': job.get('total_frames', 0),
        'detected_frames': job.get('detected_frames', 0),
        'bend_frames': job.get('bend_frames', 0),
        'failed_detections': job.get('failed_detections', 0),
        'phase': job.get('phase', 'processing')
    }
    
    if job.get('status') == 'completed':
        response_data['results'] = {
            'video': job.get('output_video'),
            'excel': job.get('output_excel')
        }
    
    logger.debug(f"Status poll for job {job_id}: {response_data}")
    return jsonify(response_data)

@app.route('/api/generate-download-token/<job_id>/<file_type>')
def generate_download_token_api(job_id, file_type):
    """Generate secure download token for job files"""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Load job data
    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job['status'] != 'completed':
        return jsonify({'error': 'Processing not completed'}), 400
    
    try:
        # Find the correct filename based on file type
        filename = None
        
        if file_type == 'video':
            # Try old format first
            if 'output_video' in job:
                filename = os.path.basename(job['output_video'])
            # Fallback to new format
            elif 'files' in job and isinstance(job['files'], list):
                for file_obj in job['files']:
                    if 'video' in file_obj:
                        filename = os.path.basename(file_obj['video'])
                        break
        
        elif file_type == 'excel':
            # Try old format first
            if 'output_excel' in job:
                filename = os.path.basename(job['output_excel'])
            # Fallback to new format
            elif 'files' in job and isinstance(job['files'], list):
                for file_obj in job['files']:
                    if 'report' in file_obj:
                        filename = os.path.basename(file_obj['report'])
                        break
        
        if not filename:
            return jsonify({'error': f'{file_type.title()} file not available'}), 404
        
        # Generate secure token using email service
        token = email_service.generate_download_token(job_id, filename)
        download_url = f"https://pracpol2-production.up.railway.app/download/token/{token}"
        
        return jsonify({
            'download_url': download_url,
            'filename': filename
        })
        
    except Exception as e:
        logger.error(f"Token generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Note: Old download endpoint removed - now using secure token system

@app.route('/download/token/<token>')
def download_with_token(token):
    """Download files using secure token (for email links)"""
    try:
        # Verify token
        result = email_service.verify_download_token(token)
        if not result:
            return jsonify({'error': 'Invalid or expired download link'}), 401
        
        # Handle both tuple and dict formats
        if isinstance(result, dict):
            job_id = result['job_id']
            filename = result['filename']
        else:
            job_id, filename = result
        
        # Load job data
        job = load_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        if job['status'] != 'completed':
            return jsonify({'error': 'Processing not completed'}), 400
        
        # Find the file path
        filepath = None
        files = job.get('files', [])
        
        for file_info in files:
            if file_info.get('video') and os.path.basename(file_info['video']) == filename:
                filepath = file_info['video']
                break
            elif file_info.get('report') and os.path.basename(file_info['report']) == filename:
                filepath = file_info['report']
                break
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Log download
        username = job.get('username', 'unknown')
        log_user_action(username, 'email_download', f'Downloaded via email: {filename}')
        logger.info(f"Token download: {filename} by {username}")
        
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Token download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

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