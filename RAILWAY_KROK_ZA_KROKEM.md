# 🚂 RAILWAY DEPLOYMENT - KROK ZA KROKEM

## 📋 **PŘÍPRAVA (5 minut)**

### 1. Ověření lokálního prostředí:
```bash
# Aktivuj conda prostředí
conda activate trunk_analysis

# Ověř že aplikace funguje lokálně
python web_app.py
# Otevři http://localhost:5000 - mělo by fungovat přihlášení
```

### 2. Test závislostí:
```bash
# Spusť test závislostí
python verify-dependencies.py
# Musí projít všechny testy ✅
```

## 🌐 **RAILWAY DEPLOYMENT (2 minuty)**

### 3. Instalace Railway CLI:
```bash
# Přes npm (nejjednodušší)
npm install -g @railway/cli

# Nebo přes PowerShell (Windows)
iwr -useb https://railway.app/install.ps1 | iex
```

### 4. Login do Railway:
```bash
railway login
# Otevře se browser → přihlas se GitHub účtem
# Po přihlášení se vrať do konzole
```

### 5. Inicializace a deploy:
```bash
# V adresáři s aplikací (C:\Users\vaclavik\testw2\pracovni_poloha2)
railway init

# Deploy aplikace
railway up
# Railway automaticky:
# - detekuje Python projekt
# - přečte runtime.txt (Python 3.9.18)  
# - nainstaluje requirements.txt
# - spustí python web_app.py
```

### 6. Sledování deployment:
```bash
# Sleduj logy během buildu
railway logs --follow

# Po dokončení buildu uvidíš URL typu:
# https://your-app.railway.app
```

## 📦 **STORAGE SETUP (1 minuta)**

### 7. Přidání persistent storage:
```bash
# Vytvoř volume pro uploads/outputs
railway volume create --name app-storage --size 10GB --mount-path /app/data

# Restart služby aby se volume připojil
railway redeploy
```

## 🧪 **TESTOVÁNÍ (1 minuta)**

### 8. Test deployment:
```bash
# Test základní funkčnosti
python deploy-test.py https://your-app.railway.app

# Pokud test projde ✅, aplikace je hotová!
```

### 9. Manuální test v browseru:
1. Otevři https://your-app.railway.app
2. Přihlas se (admin/admin123)
3. Zkus nahrát test video
4. Ověř že se spustí zpracování

## ⚙️ **POKROČILÁ NASTAVENÍ (volitelné)**

### 10. Environment variables (pokud potřeba):
```bash
# Přes CLI
railway vars set FLASK_SECRET_KEY="your-secure-key"

# Nebo přes web dashboard
# https://railway.app/dashboard → projekt → Variables
```

### 11. Custom doména (volitelné):
```bash
# Přes dashboard: Settings → Domains → Custom Domain
```

## 🔧 **TROUBLESHOOTING**

### Časté problémy a řešení:

**Build fails - MediaPipe error:**
```bash
# Ověř runtime.txt obsahuje: python-3.9.18
cat runtime.txt

# Re-deploy
railway up --detach
```

**Out of memory during processing:**
```bash
# Upgrade na Railway Pro plan ($5/měsíc)
# Dashboard → Settings → Plan
```

**Storage issues:**
```bash
# Ověř volume mount
railway volumes

# Re-mount volume
railway volume detach app-storage
railway volume attach app-storage --mount-path /app/data
```

**App not responding:**
```bash
# Check logy
railway logs

# Restart
railway redeploy
```

## 📊 **MONITORING**

### 12. Sledování aplikace:
```bash
# Real-time logs
railway logs --follow

# Metrics v dashboard
# https://railway.app/dashboard → projekt → Metrics
```

## 💰 **CENA**

**Free tier:** $5 credit měsíčně
- ~100 hodin běhu zdarma
- Postačí pro testování a low-traffic

**Pro upgrade:** $20/měsíc
- Unlimited usage  
- Více RAM/CPU
- Priority support

## 🎉 **HOTOVO!**

Po dokončení těchto kroků máš:
✅ Fungující aplikaci na https://your-app.railway.app
✅ Persistent storage pro uploaded soubory
✅ Automatické HTTPS
✅ Monitoring a logy
✅ GitHub integration pro future updates

**Celkový čas: ~10 minut** ⏱️