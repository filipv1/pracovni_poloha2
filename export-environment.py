#!/usr/bin/env python3
"""
Export conda environment pro deployment
Vytvoří přesný snapshot trunk_analysis prostředí
"""

import subprocess
import sys
import os
import json

def run_conda_command(cmd):
    """Spustí conda command a vrátí output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"❌ Error running: {cmd}")
            print(f"   {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def export_conda_environment():
    """Export conda environment info"""
    print("🔍 Analyzing conda environment: trunk_analysis")
    
    # Check if we're in the right environment
    current_env = os.environ.get('CONDA_DEFAULT_ENV', 'base')
    if current_env != 'trunk_analysis':
        print(f"⚠️  Current environment: {current_env}")
        print("   Please run: conda activate trunk_analysis")
        print("   Then run this script again")
        return False
    
    # Get conda info
    conda_info = run_conda_command("conda info --json")
    if conda_info:
        info = json.loads(conda_info)
        print(f"✅ Conda version: {info.get('conda_version')}")
        print(f"✅ Python version: {info.get('python_version')}")
    
    # Export environment to YAML
    print("\n📝 Exporting environment.yml...")
    env_export = run_conda_command("conda env export -n trunk_analysis")
    if env_export:
        with open('environment.yml', 'w') as f:
            f.write(env_export)
        print("   ✅ Created environment.yml")
    
    # Export exact pip freeze
    print("\n📝 Exporting exact pip requirements...")
    pip_freeze = run_conda_command("pip freeze")
    if pip_freeze:
        with open('requirements-exact.txt', 'w') as f:
            f.write(pip_freeze)
        print("   ✅ Created requirements-exact.txt")
    
    # Get Python version
    python_version = run_conda_command("python --version")
    if python_version:
        version = python_version.replace('Python ', '').strip()
        with open('runtime-exact.txt', 'w') as f:
            f.write(f"python-{version}\n")
        print(f"   ✅ Created runtime-exact.txt ({version})")
    
    # Generate conda dockerfile
    print("\n🐳 Generating Conda Dockerfile...")
    dockerfile_content = f'''# Exact replica of trunk_analysis environment
FROM continuumio/miniconda3:latest

WORKDIR /app

# Copy environment file  
COPY environment.yml ./

# Create identical environment
RUN conda env create -f environment.yml && \\
    conda clean -afy

# Activate environment
ENV PATH /opt/conda/envs/trunk_analysis/bin:$PATH
ENV CONDA_DEFAULT_ENV trunk_analysis

# Copy application
COPY . .

# Setup storage
RUN mkdir -p /app/data/uploads /app/data/outputs /app/data/logs && \\
    chmod -R 755 /app/data

# Environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD conda run -n trunk_analysis python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Start with conda environment
CMD ["conda", "run", "-n", "trunk_analysis", "python", "web_app.py"]
'''
    
    with open('Dockerfile.exact', 'w') as f:
        f.write(dockerfile_content)
    print("   ✅ Created Dockerfile.exact")
    
    # Generate deployment instructions
    deployment_instructions = f'''# DEPLOYMENT S CONDA ENVIRONMENT

## Vytvořené soubory:
- `environment.yml` - Kompletní conda environment
- `requirements-exact.txt` - Exact pip dependencies  
- `runtime-exact.txt` - Přesná Python verze
- `Dockerfile.exact` - Docker s replikovaným conda env

## Docker deployment (DOPORUČENO):
```bash
# Build s exact environment
docker build -f Dockerfile.exact -t ergonomic-analysis .

# Run locally
docker run -d -p 8080:8080 -v $(pwd)/data:/app/data ergonomic-analysis

# Deploy na cloud (Railway/Render/DigitalOcean):
# Použij Dockerfile.exact jako Dockerfile
```

## Cloud deployment s Docker:

### Railway:
```bash
railway login
railway init
railway up
# Přidat persistent volume
railway volume create --name storage --size 10GB --mount-path /app/data
```

### Google Cloud Run:
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/ergonomic-analysis
gcloud run deploy --image gcr.io/PROJECT-ID/ergonomic-analysis --platform managed
```

### DigitalOcean App Platform:
- Upload Dockerfile.exact jako Dockerfile
- Set container port: 8080
- Add managed database pro persistent storage

## ⚠️  Bez Docker alternativy:

### Option 1: Export conda packages
```bash
conda list --explicit > spec-file.txt
# Use spec-file.txt na target serveru
conda create --name trunk_analysis --file spec-file.txt
```

### Option 2: Replicate manually
```bash
# Na target serveru:
conda create -n trunk_analysis python={python_version.replace('Python ', '').strip()}
conda activate trunk_analysis  
pip install -r requirements-exact.txt
```

Conda environment: {current_env}
Python version: {python_version}
Export date: $(date)
'''
    
    with open('CONDA_DEPLOYMENT.md', 'w') as f:
        f.write(deployment_instructions)
    print("   ✅ Created CONDA_DEPLOYMENT.md")
    
    print(f"\n🎉 Environment export complete!")
    print(f"📁 Created files:")
    files = ['environment.yml', 'requirements-exact.txt', 'runtime-exact.txt', 
             'Dockerfile.exact', 'CONDA_DEPLOYMENT.md']
    for file in files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
    
    print(f"\n🚀 Next steps:")
    print(f"   1. Use Dockerfile.exact for Docker deployment")
    print(f"   2. Or use environment.yml to recreate conda env on target server")
    print(f"   3. Follow CONDA_DEPLOYMENT.md instructions")
    
    return True

if __name__ == "__main__":
    print("🔧 CONDA ENVIRONMENT EXPORT TOOL")
    print("=" * 40)
    
    success = export_conda_environment()
    if not success:
        sys.exit(1)
    
    print(f"\n✨ Ready for deployment with exact conda environment!")