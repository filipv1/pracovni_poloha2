#!/usr/bin/env python3
"""
Test script for Resend HTTP API email functionality
"""

import os
import sys
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_resend_api():
    """Test Resend HTTP API directly"""
    
    print("=" * 60)
    print("RESEND HTTP API TEST")
    print("=" * 60)
    
    # Get API key from environment
    api_key = os.environ.get('RESEND_API_KEY')
    
    if not api_key:
        print("❌ RESEND_API_KEY not found in .env file")
        print("Please:")
        print("1. Go to https://resend.com")
        print("2. Sign up and get your API key")
        print("3. Add RESEND_API_KEY=your_key_here to .env file")
        return False
    
    print(f"API Key: {'*' * (len(api_key) - 8)}{api_key[-8:]}")
    print("")
    
    # Get registered email (for Resend free plan limitation)
    registered_email = "vaclavik.renturi@gmail.com"  # Must match Resend registration
    
    # Test email data
    test_email = {
        "from": "Ergonomic Analysis <onboarding@resend.dev>",  # Resend sandbox domain
        "to": [registered_email],  # Must use registered email on free plan
        "subject": "TEST: Resend HTTP API Test",
        "html": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #4CAF50;">Resend API Test uspesny!</h2>
            <p>Tento email byl odeslán pomocí <strong>Resend HTTP API</strong> místo SMTP.</p>
            
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Výhody HTTP API:</h3>
                <ul>
                    <li>✅ Funguje na Railway Hobby plánu</li>
                    <li>✅ Rychlejší než SMTP (žádné timeouts)</li>
                    <li>✅ Lepší error handling</li>
                    <li>✅ Jednodušší konfigurace</li>
                </ul>
            </div>
            
            <p><strong>Čas odeslání:</strong> {timestamp}</p>
            
            <hr style="margin: 30px 0;">
            <p style="font-size: 14px; color: #666;">
                Test email z Ergonomic Analysis aplikace<br>
                Powered by Resend.com
            </p>
        </body>
        </html>
        """.format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))
    }
    
    # API endpoint and headers
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print("Sending test email...")
    print(f"To: {test_email['to'][0]} (registered email)")
    print(f"Subject: {test_email['subject']}")
    print("Note: Free plan can only send to registered email address")
    print("")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=test_email, headers=headers, timeout=30)
        end_time = time.time()
        
        print(f"Response time: {end_time - start_time:.2f}s")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("EMAIL SENT SUCCESSFULLY!")
            print(f"Email ID: {result.get('id', 'N/A')}")
            print("")
            print("Check your email inbox at vaclavik.renturi@gmail.com")
            print("")
            print("Resend HTTP API is working correctly!")
            print("This means emails will work on Railway Hobby plan.")
            return True
        else:
            print("EMAIL SENDING FAILED")
            print(f"Error: {response.text}")
            
            # Common error messages
            if response.status_code == 401:
                print("Common issue: Invalid API key")
            elif response.status_code == 422:
                print("Common issue: Invalid email format or missing required fields")
            elif response.status_code == 429:
                print("Common issue: Rate limit exceeded")
            
            return False
            
    except requests.exceptions.Timeout:
        print("REQUEST TIMEOUT")
        print("API request took too long (>30s)")
        return False
    except requests.exceptions.ConnectionError:
        print("CONNECTION ERROR")
        print("Cannot connect to Resend API")
        return False
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        return False


def test_fallback_mechanism():
    """Test the fallback mechanism in our application"""
    print("\n" + "=" * 60)
    print("FALLBACK MECHANISM TEST")
    print("=" * 60)
    
    # Import our hybrid email service
    sys.path.append(os.path.dirname(__file__))
    
    try:
        from web_app import HybridEmailService, app, mail
        
        with app.app_context():
            hybrid_service = HybridEmailService(app, mail)
            
            # Check which services are available
            resend_enabled = hybrid_service.resend_service.enabled
            smtp_configured = bool(app.config.get('MAIL_USERNAME'))
            
            print(f"Resend API: {'Enabled' if resend_enabled else 'Disabled'}")
            print(f"SMTP: {'Configured' if smtp_configured else 'Not configured'}")
            print("")
            
            if resend_enabled:
                print("Primary method: Resend HTTP API")
                print("Fallback method: SMTP")
                print("Railway Hobby plan compatible")
            elif smtp_configured:
                print("Primary method: SMTP only")
                print("Requires Railway Pro plan")
            else:
                print("No email service configured")
                
            return resend_enabled or smtp_configured
            
    except Exception as e:
        print(f"❌ Error testing fallback mechanism: {e}")
        return False


if __name__ == "__main__":
    print("Testing Resend HTTP API email functionality...\n")
    
    # Test Resend API directly
    api_success = test_resend_api()
    
    # Test fallback mechanism
    fallback_success = test_fallback_mechanism()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if api_success:
        print("Resend HTTP API: Working")
        print("Railway Hobby plan: Compatible")
        print("No SMTP timeouts")
    else:
        print("Resend HTTP API: Failed")
        print("   Please check API key configuration")
    
    if fallback_success:
        print("Fallback mechanism: Available")
    else:
        print("Fallback mechanism: Not available")
        
    print("\nNext steps:")
    if not api_success:
        print("1. Get Resend API key from https://resend.com")
        print("2. Add RESEND_API_KEY to .env file")
        print("3. Re-run this test")
    else:
        print("1. Deploy to Railway")
        print("2. Set RESEND_API_KEY in Railway environment variables")
        print("3. Test email functionality in production")