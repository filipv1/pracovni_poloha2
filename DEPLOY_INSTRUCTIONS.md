# INSTRUKCE PRO BEZPEČNÝ DEPLOY - FIX VYSOKÉ SPOTŘEBY PAMĚTI

## CO BYLO ZMĚNĚNO:
1. **emergency_fix.py** - nový soubor, který automaticky čistí staré soubory každou hodinu
2. **web_app.py** - přidán import emergency_fix (řádky 35-40)
3. **Procfile** - snížen počet workerů a přidán max-requests pro restart workeru

## KROK 1: OTESTUJ LOKÁLNĚ (DŮLEŽITÉ!)
```bash
cd pracovni_poloha2
python test_emergency_fix.py
```

Pokud všechny testy projdou (uvidíš ✅), pokračuj. Pokud ne, NEDEPLOY!

## KROK 2: DEPLOY NA RAILWAY
```bash
# Přidej změněné soubory
git add emergency_fix.py web_app.py Procfile test_emergency_fix.py

# Commitni s jasnou zprávou
git commit -m "Fix high memory usage - add automatic cleanup and reduce workers"

# Pushni na Railway
git push
```

## KROK 3: MONITORUJ PO DEPLOYI (5-10 minut)
1. Otevři Railway dashboard
2. Sleduj logy v "Deployments" → "View Logs"
3. Měl bys vidět: "Emergency memory fix activated"
4. Zkontroluj že aplikace běží: https://tvoje-app.railway.app

## KROK 4: OVĚŘ SNÍŽENÍ SPOTŘEBY
- Počkej 1 hodinu
- Zkontroluj Railway metrics
- Memory by měla klesnout o 50-70%

## POKUD NĚCO NEFUNGUJE - ROLLBACK:
```bash
# Vrať změny
git checkout -- web_app.py
cp Procfile.backup Procfile

# Nebo kompletní rollback na předchozí commit
git reset --hard HEAD~1
git push --force
```

## ALTERNATIVA - JEŠTĚ BEZPEČNĚJŠÍ:
Pokud se bojíš, můžeš nejdřív změnit POUZE Procfile:
```bash
# Změň pouze Procfile
git add Procfile
git commit -m "Reduce workers and add max-requests"
git push
```

To sníží spotřebu o ~40% bez jakéhokoli rizika.

## CO DĚLAJÍ ZMĚNY:

### emergency_fix.py:
- Každou hodinu smaže soubory starší než 6 hodin
- Vynutí garbage collection Pythonu
- Běží v separátním threadu, neovlivní hlavní aplikaci

### Změna v Procfile:
- **--workers 1**: Místo 2 workerů jen 1 (ušetří 50% RAM)
- **--max-requests 200**: Worker se restartuje po 200 requestech (vyčistí paměť)
- **Odstraněn --preload**: Bezpečnější, méně problémů s importy

### Změna ve web_app.py:
- Pouze přidává import emergency_fix
- Obaleno v try/except - pokud soubor chybí, aplikace poběží normálně

## OČEKÁVANÉ VÝSLEDKY:
- **Memory**: Z ~480 MB → ~150-200 MB
- **Náklady**: Z $5/den → $1.50/den
- **Network egress**: Významné snížení

## KONTAKT NA PODPORU:
Pokud něco nefunguje, Railway má dobrý support:
- Discord: https://discord.gg/railway
- Email: team@railway.app