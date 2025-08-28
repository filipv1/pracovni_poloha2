# 🎨 RENDER.COM DEPLOYMENT - KROK ZA KROKEM

## ⚠️ **DŮLEŽITÉ UPOZORNĚNÍ**
- **Render free tier má jen 512MB RAM** - nestačí pro MediaPipe video processing
- **Musíte upgrade na Starter plan ($7/měsíc)** pro 1GB RAM
- Railway je levnější alternativa ($5 credit zdarma)

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

### 3. Příprava Git repository:
```bash
# Pokud ještě nemáš Git repo
git init
git add .
git commit -m "Initial commit - ergonomic analysis app"

# Push na GitHub
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

## 🌐 **RENDER DEPLOYMENT (5 minut)**

### 4. Vytvoření Render účtu:
1. Jdi na https://render.com
2. Sign up s GitHub účtem
3. Authorize Render přístup k repositories

### 5. Vytvoření Web Service:
1. **Dashboard → "New +"** 
2. **"Web Service"**
3. **Connect repository:**
   - Select GitHub repo s vaší aplikací
   - Branch: `main`

### 6. Konfigurace služby:
```
Name: ergonomic-analysis-app
Region: Oregon (US West) - nejblíž pro EU
Branch: main
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: python web_app.py
```

### 7. Environment Variables:
```
FLASK_ENV = production  
FLASK_SECRET_KEY = your-secure-random-key-here
PYTHONUNBUFFERED = 1
PORT = 10000
```

### 8. **KRITICKÉ - Upgrade plánu:**
```
Plan: Starter ($7/month) - POVINNÉ!
```
Free tier nemá dost RAM pro MediaPipe!

## 📦 **STORAGE SETUP (2 minuty)**

### 9. Přidání Persistent Disk:
1. **Advanced → Add Disk**
2. **Disk Configuration:**
   ```
   Name: app-storage
   Mount Path: /opt/render/project/src/storage
   Size: 10GB
   ```

### 10. Deploy aplikace:
1. **"Create Web Service"**
2. Čekej na build (5-10 minut - MediaPipe je velký)
3. Sleduj logy v real-time

## 🧪 **TESTOVÁNÍ (2 minuty)**

### 11. Test deployment:
```bash
# Render ti dá URL typu: https://ergonomic-analysis-app.onrender.com
python deploy-test.py https://your-app.onrender.com

# Pokud test projde ✅, aplikace je hotová!
```

### 12. Manuální test v browseru:
1. Otevři https://your-app.onrender.com
2. Přihlas se (admin/admin123)  
3. Zkus nahrát test video
4. Ověř že se spustí zpracování

## 🔧 **TROUBLESHOOTING**

### Časté problémy a řešení:

**Build fails - Memory error:**
```
❌ Problem: Free tier - nedostatek RAM
✅ Řešení: Upgrade na Starter plan ($7/měsíc)
```

**Build timeout:**
```
❌ Problem: MediaPipe instalace trvá moc dlouho
✅ Řešení: 
- Build Command: pip install --no-cache-dir -r requirements.txt
- Nebo použij Railway (rychlejší buildy)
```

**Storage issues:**
```
❌ Problem: Soubory se neukládají
✅ Řešení: Ověř Mount Path v disk settings:
/opt/render/project/src/storage
```

**App crashes při video processing:**
```
❌ Problem: Nedostatek RAM během zpracování
✅ Řešení: Upgrade na Professional plan ($25/měsíc) pro 4GB RAM
```

**Python version issues:**
```
❌ Problem: Používá Python 3.12 místo 3.9
✅ Řešení: Ověř že máš runtime.txt s: python-3.9.18
```

## ⚙️ **POKROČILÁ NASTAVENÍ**

### 13. Custom doména (volitelné):
1. **Settings → Custom Domains**
2. Přidat CNAME record u DNS providera

### 14. Auto-deploy z Git:
- Render automaticky re-deployuje při git push
- Můžeš vypnout v Settings → Auto-Deploy

### 15. Health checks:
```
Health Check Path: /health
```

## 💰 **PRICING RENDER**

**Free tier:**
- ❌ 512MB RAM - nestačí pro MediaPipe  
- ❌ Aplikace spí po 15min neaktivity
- ❌ Omezený build time

**Starter ($7/měsíc):**
- ✅ 1GB RAM - minimum pro MediaPipe
- ✅ No sleep
- ✅ SSL certificates  
- ✅ Custom domains

**Professional ($25/měsíc):**
- ✅ 4GB RAM - pro větší videa
- ✅ Faster builds
- ✅ Priority support

## 🔄 **ALTERNATIVY POKUD RENDER NEFUNGUJE**

**Railway (doporučeno):**
```bash
npm install -g @railway/cli
railway login
railway up
```

**DigitalOcean App Platform:**
- $5/měsíc místo $7
- Lepší RAM allocation

## 🎉 **HOTOVO!**

Po dokončení máš:
✅ Aplikaci na https://your-app.onrender.com
✅ Persistent storage  
✅ Automatic HTTPS
✅ GitHub auto-deploy
✅ Monitoring dashboard

**Celkový čas: ~15 minut**
**Cena: $7/měsíc (Starter plan)**

## 💡 **PRO TIP**
Pokud chceš ušetřit, zkus nejdřív Railway ($5 credit zdarma) - má rychlejší buildy a lepší free tier!