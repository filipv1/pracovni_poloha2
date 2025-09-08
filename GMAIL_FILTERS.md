# Gmail Filtry pro Ergonomic Analysis

Všechny emaily se posílají na `vaclavik.renturi@gmail.com` s klíčovými slovy pro automatické přesměrování.

## 📋 Seznam uživatelů a jejich klíčových slov

| Uživatel | Klíčové slovo | Subject obsahuje | Email adresa |
|----------|---------------|------------------|--------------|
| admin | `[ADMIN]` | `✅ [ADMIN] Analýza dokončena - X souborů` | admin@example.com |
| user1 | `[USER1]` | `✅ [USER1] Analýza dokončena - X souborů` | user1@example.com |
| demo | `[DEMO]` | `✅ [DEMO] Analýza dokončena - X souborů` | demo@example.com |
| korc | `[KORC]` | `✅ [KORC] Analýza dokončena - X souborů` | korc@example.com |
| koska | `[KOSKA]` | `✅ [KOSKA] Analýza dokončena - X souborů` | koska@example.com |
| licha | `[LICHA]` | `✅ [LICHA] Analýza dokončena - X souborů` | licha@example.com |
| koutenska | `[KOUTENSKA]` | `✅ [KOUTENSKA] Analýza dokončena - X souborů` | koutenska@example.com |
| kusinova | `[KUSINOVA]` | `✅ [KUSINOVA] Analýza dokončena - X souborů` | kusinova@example.com |
| vagnerova | `[VAGNEROVA]` | `✅ [VAGNEROVA] Analýza dokončena - X souborů` | vagnerova@example.com |
| badrova | `[BADROVA]` | `✅ [BADROVA] Analýza dokončena - X souborů` | badrova@example.com |
| henkova | `[HENKOVA]` | `✅ [HENKOVA] Analýza dokončena - X souborů` | henkova@example.com |
| vaclavik | `[VACLAVIK]` | `✅ [VACLAVIK] Analýza dokončena - X souborů` | vaclavik@renturi.cz |

## 🔧 Jak nastavit Gmail filtry

### Krok 1: Otevři Gmail nastavení
1. Jdi na [Gmail.com](https://gmail.com)
2. Klikni na ⚙️ (Settings) → **See all settings**
3. Přejdi na záložku **"Filters and Blocked Addresses"**

### Krok 2: Vytvoř filtry pro každého uživatele

**Pro každého uživatele z tabulky výše:**

1. Klikni **"Create a new filter"**
2. **Has the words:** `[KORC]` (příklad pro uživatele KORC)
3. Klikni **"Create filter"**
4. Zaškrtni **"Forward it to"** a vyber/přidej email adresu
5. Volitelně zaškrtni:
   - **"Apply the label"** → vytvoř label "Ergonomic-KORC"
   - **"Mark as important"**
   - **"Never send to spam"**
6. Klikni **"Create filter"**

### Krok 3: Nastav email forwarding

**Před vytvořením filtrů musíš povolit forwarding:**

1. V Gmail settings jdi na **"Forwarding and POP/IMAP"**
2. Klikni **"Add a forwarding address"**
3. Přidej každou email adresu (korc@example.com, licha@example.com, atd.)
4. Potvrdí forwarding přes potvrzovací email

## 📧 Příklad filtru pro KORC

```
From: any
To: any  
Subject: any
Has the words: [KORC]
Doesn't have: any
Has attachment: any

Actions:
✅ Forward it to: korc@example.com
✅ Apply the label: Ergonomic-KORC
✅ Mark as important
✅ Never send to spam
```

## ⚡ Quick Setup Script

Pro rychlé nastavení můžeš použít Gmail Search pro testování:

```
in:inbox subject:[KORC]
in:inbox subject:[LICHA]  
in:inbox subject:[VACLAVIK]
```

## 🛠️ Testování

Po nastavení filtrů:
1. Nahraj testovací video jako různí uživatelé
2. Zkontroluj že se emaily správně přesměrovávají
3. Ověř že labels fungují správně

## 📝 Poznámky

- Všechny emaily stále dorazí do hlavní schránky `vaclavik.renturi@gmail.com`
- Filtry je automaticky přesměrují podle klíčových slov
- Můžeš přidat labels pro lepší organizaci
- Funguje s Resend HTTP API i SMTP fallback