#!/usr/bin/env python3
"""
Test script pro ověření, že emergency fix nerozhodí aplikaci
Spusť PŘED deployem na Railway!
"""

import sys
import time
import requests
import subprocess
import os
from pathlib import Path

def test_emergency_fix():
    """Test že emergency_fix.py funguje správně"""
    print("1. Test emergency_fix.py...")
    try:
        import emergency_fix
        print("   ✓ Emergency fix se načetl správně")
    except Exception as e:
        print(f"   ✗ CHYBA: {e}")
        return False
    
    # Zkontroluj že složky existují
    for folder in ['uploads', 'outputs', 'jobs', 'logs']:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"   ✓ Vytvořena složka {folder}")
    
    return True

def test_web_app_import():
    """Test že web_app.py se spustí s emergency fix"""
    print("\n2. Test web_app.py import...")
    try:
        # Zkus importovat web_app
        import web_app
        print("   ✓ web_app.py se načetl správně")
        return True
    except Exception as e:
        print(f"   ✗ CHYBA při importu web_app: {e}")
        return False

def test_local_server():
    """Test lokálního serveru"""
    print("\n3. Test lokálního serveru...")
    print("   Spouštím server na 5 sekund...")
    
    # Spusť server v pozadí
    proc = subprocess.Popen(
        [sys.executable, "web_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Počkej až server nastartuje
    time.sleep(3)
    
    try:
        # Zkus se připojit
        response = requests.get("http://localhost:5000", timeout=2)
        if response.status_code in [200, 302]:  # 302 je redirect na login
            print("   ✓ Server běží a odpovídá")
            result = True
        else:
            print(f"   ✗ Server vrátil status {response.status_code}")
            result = False
    except requests.exceptions.ConnectionError:
        print("   ✗ Nelze se připojit k serveru")
        result = False
    except Exception as e:
        print(f"   ✗ Chyba: {e}")
        result = False
    
    # Zastav server
    proc.terminate()
    time.sleep(1)
    
    return result

def check_procfile():
    """Zkontroluj Procfile"""
    print("\n4. Kontrola Procfile...")
    
    procfile_path = Path("Procfile")
    if not procfile_path.exists():
        print("   ✗ Procfile neexistuje!")
        return False
    
    content = procfile_path.read_text()
    
    # Kontroly
    checks = [
        ("--workers 1" in content, "Pouze 1 worker"),
        ("--max-requests" in content, "Max requests nastaven"),
        ("--timeout 3600" in content, "Timeout nastaven"),
        ("--preload" not in content, "Bez --preload (bezpečnější)")
    ]
    
    all_ok = True
    for check, desc in checks:
        if check:
            print(f"   ✓ {desc}")
        else:
            print(f"   ✗ {desc}")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 50)
    print("TEST EMERGENCY FIX PRO RAILWAY")
    print("=" * 50)
    
    results = []
    
    # Změň do správného adresáře
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Spusť testy
    results.append(("Emergency fix", test_emergency_fix()))
    results.append(("Web app import", test_web_app_import()))
    results.append(("Procfile", check_procfile()))
    
    # Lokální server test - volitelný
    print("\n" + "=" * 50)
    test_server = input("Chceš otestovat lokální server? (y/n): ").lower()
    if test_server == 'y':
        results.append(("Lokální server", test_local_server()))
    
    # Výsledky
    print("\n" + "=" * 50)
    print("VÝSLEDKY:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✓ OK" if passed else "✗ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("\n✅ VŠECHNY TESTY PROŠLY - můžeš deployovat!")
        print("\nPříkazy pro deploy:")
        print("  git add emergency_fix.py web_app.py Procfile")
        print('  git commit -m "Fix high memory usage on Railway"')
        print("  git push")
    else:
        print("\n❌ NĚKTERÉ TESTY SELHALY - NEOPRAVUJ!")
        print("\nPro rollback:")
        print("  git checkout -- web_app.py")
        print("  cp Procfile.backup Procfile")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())