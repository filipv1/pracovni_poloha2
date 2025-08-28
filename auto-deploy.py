#!/usr/bin/env python3
"""
Automatický deployment script pro multiple platformy
Použití: python auto-deploy.py [platform]
Platformy: railway, render, docker, local
"""

import os
import sys
import subprocess
import json
import time

def run_command(cmd, description=""):
    """Spuštění shell příkazu s error handlingem"""
    print(f"🔄 {description}")
    print(f"   Command: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"   ✅ Success")
        if result.stdout.strip():
            print(f"   Output: {result.stdout.strip()}")
        return True
    else:
        print(f"   ❌ Failed")
        if result.stderr.strip():
            print(f"   Error: {result.stderr.strip()}")
        return False

def deploy_railway():
    """Deploy na Railway"""
    print("🚀 RAILWAY DEPLOYMENT")
    
    # Check railway CLI
    if not run_command("railway --version", "Checking Railway CLI"):
        print("❌ Railway CLI not installed. Install with: npm install -g @railway/cli")
        return False
    
    # Login check
    if not run_command("railway whoami", "Checking login"):
        print("🔑 Please login first: railway login")
        return False
    
    # Deploy
    steps = [
        ("railway init", "Initializing Railway project"),
        ("railway up", "Deploying application"),
    ]
    
    for cmd, desc in steps:
        if not run_command(cmd, desc):
            return False
    
    print("✅ Railway deployment complete!")
    print("📝 Don't forget to add persistent storage:")
    print("   railway volume create --name storage --size 10GB --mount-path /app/data")
    return True

def deploy_render():
    """Deploy na Render pomocí Git"""
    print("🎨 RENDER DEPLOYMENT")
    
    # Git check
    if not run_command("git status", "Checking git repository"):
        return False
    
    print("📋 Manual steps for Render.com:")
    print("1. Push to GitHub: git push origin main")
    print("2. Go to https://render.com")
    print("3. New Web Service → Connect repository")
    print("4. Use render-fixed.yaml configuration")
    print("5. Add persistent disk in Advanced settings")
    
    # Optional git push
    response = input("Push to git now? (y/n): ")
    if response.lower() == 'y':
        run_command("git add .", "Adding files")
        run_command('git commit -m "Deploy configuration"', "Committing changes")  
        run_command("git push origin main", "Pushing to remote")
    
    return True

def deploy_docker():
    """Build a spuštění Docker kontejneru"""
    print("🐳 DOCKER DEPLOYMENT")
    
    # Check Docker
    if not run_command("docker --version", "Checking Docker"):
        print("❌ Docker not installed")
        return False
    
    steps = [
        ("docker build -t ergonomic-analysis .", "Building Docker image"),
        ("docker run -d -p 8080:8080 -v $(pwd)/data:/app/data --name ergonomic-app ergonomic-analysis", 
         "Running Docker container")
    ]
    
    for cmd, desc in steps:
        if not run_command(cmd, desc):
            return False
    
    print("✅ Docker deployment complete!")
    print("🌐 Application running at: http://localhost:8080")
    return True

def deploy_local():
    """Lokální spuštění pro testing"""
    print("💻 LOCAL DEPLOYMENT")
    
    # Check Python
    if not run_command("python --version", "Checking Python"):
        return False
    
    # Check conda environment
    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env != 'trunk_analysis':
        print("⚠️  Warning: Not in 'trunk_analysis' conda environment")
        print("   Activate with: conda activate trunk_analysis")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False
    
    # Create directories
    for folder in ['uploads', 'outputs', 'logs']:
        os.makedirs(folder, exist_ok=True)
    
    print("✅ Local setup complete!")
    print("🚀 Start with: python web_app.py")
    print("🌐 Application will be at: http://localhost:5000")
    return True

def main():
    platforms = {
        'railway': deploy_railway,
        'render': deploy_render, 
        'docker': deploy_docker,
        'local': deploy_local
    }
    
    print("🚀 ERGONOMIC ANALYSIS - AUTO DEPLOYMENT")
    print("=" * 50)
    
    if len(sys.argv) != 2 or sys.argv[1] not in platforms:
        print(f"Usage: python auto-deploy.py [{' | '.join(platforms.keys())}]")
        print("\nPlatforms:")
        print("  railway - Deploy to Railway (recommended)")
        print("  render  - Setup for Render.com deployment")  
        print("  docker  - Build and run Docker container")
        print("  local   - Setup for local development")
        sys.exit(1)
    
    platform = sys.argv[1]
    deploy_func = platforms[platform]
    
    print(f"Selected platform: {platform.upper()}")
    print("-" * 30)
    
    success = deploy_func()
    
    if success:
        print(f"\n🎉 {platform.upper()} deployment successful!")
        
        # Test deployment pokud je URL dostupné
        if platform == 'local':
            test_url = "http://localhost:5000"
        elif platform == 'docker':  
            test_url = "http://localhost:8080"
        else:
            test_url = None
            
        if test_url:
            print(f"🧪 Test deployment with: python deploy-test.py {test_url}")
    else:
        print(f"\n💥 {platform.upper()} deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()