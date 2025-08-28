# 🚀 DEPLOYMENT GUIDE - OPRAVENÉ ŘEŠENÍ

## ❌ CO BYLO ŠPATNĚ S RENDER.COM

Původní `render.yaml` měl tyto problémy:
1. **Špatný mount path** - `/opt/render/project/src/data` místo správných `uploads/`, `outputs/`, `logs/`
2. **Nedostatečná RAM** - 512MB na free tier není dost pro MediaPipe
3. **Build timeouts** - MediaPipe instalace trvá moc dlouho
4. **Python version issues** - občas ignoruje `runtime.txt`

## ✅ DOPORUČENÉ ŘEŠENÍ: RAILWAY

### Proč Railway:
- 💰 **$5 free credit** měsíčně (= cca 100 hodin běhu zdarma)
- 🚀 **Rychlejší buildy** pro ML dependencies
- 🐍 **Stabilní Python 3.9** support
- 📦 **Lepší volume handling**
- 💾 **Persistent storage** bez problémů

### Railway Deployment (KROK ZA KROKEM):

#### 1. Příprava (hotovo):
```bash
# Soubory jsou již vytvořené:
# ✅ railway.toml - konfigurace
# ✅ runtime.txt - Python 3.9.18  
# ✅ requirements.txt - všechny dependencies
# ✅ deployment_fix.py - storage path handling
```

#### 2. Instalace Railway CLI:
```bash
# Jednoduše přes npm
npm install -g @railway/cli

# Nebo přes curl
curl -fsSL https://railway.app/install.sh | sh
```

#### 3. Deployment:
```bash
# Login do Railway
railway login

# Create project 
railway init

# Deploy
railway up

# Přidat persistent storage
railway volume create --name storage --size 10GB --mount-path /app/data
```

#### 4. Environment Variables (automaticky nastavené):
- `FLASK_ENV=production`
- `FLASK_SECRET_KEY` (auto-generated)
- `PORT` (auto-assigned)
- `PYTHONUNBUFFERED=1`

### Alternativní Deployment postup (GitHub):
1. Push kód na GitHub
2. Jdi na [railway.app](https://railway.app)
3. "Deploy from GitHub repo"
4. Vyber projekt → automaticky detects Python + requirements.txt
5. Add persistent volume v Settings

## 🔧 OPRAVA RENDER.COM (pokud chcete zůstat)

### 1. Použij opravený render-fixed.yaml:
```bash
# Přejmenuj render.yaml na render-backup.yaml
mv render.yaml render-backup.yaml

# Použij opravenou verzi
mv render-fixed.yaml render.yaml
```

### 2. Upgrade na Starter plan ($7/měsíc):
- Free tier nemá dostatek RAM pro MediaPipe
- Starter plan má 1GB RAM - minimum pro video processing

### 3. Aplikuj storage fix:
Zkopíruj kód z `deployment_fix.py` do začátku `web_app.py`

## 🛠️ ALTERNATIVNÍ PLATFORMY

### DigitalOcean App Platform ($5/měsíc):
```yaml
# .do/app.yaml
name: ergonomic-analysis
services:
- name: web
  source_dir: /
  github:
    repo: your-username/your-repo
    branch: main
  run_command: python web_app.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 5000
  routes:
  - path: /
  envs:
  - key: FLASK_ENV
    value: production
```

### Heroku (ne moc doporučeno):
- Ephemeral filesystem - ztratíte uploaded soubory
- Slug size limity problematické pro MediaPipe

### VPS Solution ($5/měsíc DigitalOcean):
```bash
# Setup na Ubuntu VPS
sudo apt update
sudo apt install python3.9 python3-pip nginx
pip3 install -r requirements.txt
# + setup systemd service + nginx reverse proxy
```

## 🧪 TESTOVÁNÍ DEPLOYMENT

Použij `deploy-test.py` pro ověření:
```bash
# Po deploymenu otestuj
python deploy-test.py https://your-app.railway.app
```

## 💡 PRO TIPS

### Storage optimalizace:
```python
# Přidat do web_app.py cleanup staré soubory
import schedule
def cleanup_old_files():
    # Smaž soubory starší než 24 hodin
    pass
```

### Memory optimalizace:
```python  
# Pro Railway add memory monitoring
import psutil
if psutil.virtual_memory().available < 500_000_000:  # 500MB
    # Cleanup nebo restart
    pass
```

### Scaling:
- Railway: Auto-scaling based on CPU/RAM
- DigitalOcean: Manual scaling přes dashboard  
- Render: Auto-scaling na Professional+

## 🎯 RYCHLÁ AKCE

**Pro nejrychlejší deployment:**
1. `npm install -g @railway/cli`
2. `railway login`  
3. `railway init` v project directory
4. `railway up`
5. Add volume: `railway volume create --name storage --size 10GB --mount-path /app/data`

**Hotovo za 5 minut!** ✨