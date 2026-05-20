# Lead Machine — Teknisk Dokumentation

**Projekt:** Lead Machine for NextLead  
**Plats:** `/Users/elias/lead-machine/`  
**Datum:** Maj 2026  
**Avsändare:** Elias Ivanoff, elias.ivanoff@gmail.com

---

## 1. Vad är Lead Machine?

Lead Machine är ett helautomatiskt system som varje dag:

1. Hittar svenska callcenters och säljbolag på Google Maps
2. Analyserar deras hemsidor efter problem/svagheter
3. Genererar ett personligt cold email med AI (GPT-4o-mini)
4. Skickar mailet automatiskt via Gmail SMTP

Syftet är att sälja leads från **NextLead** (nextlead.se) till säljteam och callcenters utan manuellt arbete.

---

## 2. Systemöversikt — Dagligt flöde

```
Kl 09:00 — GitHub Actions / cron startar

  STEG 1: SCRAPING
  ─────────────────────────────────────────────
  Google Places API söker på:
    "callcenter Stockholm"
    "telemarketing Stockholm"
    "contact center Stockholm"
    ... (8 kategorier)

  Hittar upp till 100 nya företag per körning.
  Sparar: namn, hemsida, telefon, adress, kategori.
  Hoppar över: e-handel, restauranger, apotek m.fl.

        ↓

  STEG 2: ANALYS
  ─────────────────────────────────────────────
  För varje nytt företag hämtas hemsidan och kontrolleras:
    • SSL (https)                • Kontaktformulär
    • Mobilanpassning            • Google Analytics
    • Meta-titel & beskrivning   • Sociala medier
    • Karta (Google Maps embed)  • Copyright-år
    • CMS (Wix, Strikingly...)   • PageSpeed (mobil + dator)

  Baserat på antal problem → rekommenderar paket:
    3+ problem  → Medium (6 500 kr)
    6+ problem  → Stor (9 500 kr)
    <3 problem  → Liten (4 500 kr)

        ↓

  STEG 3: AI-GENERERING
  ─────────────────────────────────────────────
  OpenAI GPT-4o-mini skriver ett personligt mail per företag.
  Fast struktur, max 80 ord, skrivs som Elias (inte bolag).
  Sparas i databasen med status "draft".

        ↓

  STEG 4: UTSKICK
  ─────────────────────────────────────────────
  Skickar max 10 mail/dag (ökas gradvis till 35/dag).
  10–30 min slumpmässig paus mellan varje mail.
  Skickas från: elias.ivanoff@gmail.com
```

---

## 3. Teknikstack

| Komponent | Teknologi | Beskrivning |
|---|---|---|
| Scraping | Google Places API (New) | Söker företag per kategori + stad |
| Hemsideanalys | Python + BeautifulSoup | Hämtar HTML, kollar 12 kvalitetssignaler |
| Hastighetstestning | PageSpeed Insights API | Ger poäng 0–100 för mobil och dator |
| AI-generering | OpenAI GPT-4o-mini | Skriver personliga cold emails på svenska |
| Databas | Supabase (PostgreSQL) | Lagrar leads, analyser, mail, körningar |
| Mailutskick | Gmail SMTP | Via elias.ivanoff@gmail.com + App Password |
| Automation | GitHub Actions | Kör pipeline automatiskt varje dag |
| Dashboard | Next.js (localhost:3000) | Realtidsöversikt för Elias och kollegor |

---

## 4. Mappstruktur

```
lead-machine/
├── pipeline/               ← Python-pipelinen
│   ├── main.py             ← Orkestrator, kör alla steg
│   ├── scraper.py          ← Steg 1: hittar företag på Google Maps
│   ├── analyzer.py         ← Steg 2: analyserar hemsidor
│   ├── ai_processor.py     ← Steg 3: genererar mail med OpenAI
│   ├── sender.py           ← Steg 4: skickar mail via Gmail
│   ├── config.py           ← Inställningar och miljövariabler
│   └── requirements.txt    ← Python-beroenden
├── dashboard/              ← Next.js dashboard
│   └── app/
│       ├── page.tsx        ← Översiktssida
│       └── leads/          ← Leadsida
├── supabase/
│   └── schema.sql          ← Databas-schema (kör en gång i Supabase)
├── run_pipeline.sh         ← Shell-skript för cron-körning
├── SETUP.md                ← Installationsinstruktioner
└── DOKUMENTATION.md        ← Denna fil
```

---

## 5. Databas — Tabeller

Databasen finns i Supabase (PostgreSQL). Fyra tabeller:

### Tabell: `leads`
En rad per företag hittat på Google Maps.

| Kolumn | Typ | Beskrivning |
|---|---|---|
| id | UUID | Unikt ID |
| company_name | TEXT | Företagets namn |
| website_url | TEXT | Hemsideadress |
| email | TEXT | Hittad e-post (från hemsidan) |
| phone | TEXT | Telefonnummer |
| address | TEXT | Gatuadress |
| city | TEXT | Stad (default: Stockholm) |
| category | TEXT | Google-kategori |
| google_place_id | TEXT | Unikt Google-ID (förhindrar dubbletter) |
| status | TEXT | Se statusflöde nedan |
| created_at | TIMESTAMPTZ | När leadet lades till |

**Statusflöde leads:**
```
pending → analyzing → analyzed → generating → email_ready → sent → opened → replied
                                                         ↘ email_ready_no_address
               ↘ no_website / bokadirekt_only / fetch_error / skipped_ecommerce
```

---

### Tabell: `analyses`
En rad per analyserad hemsida (kopplad till lead).

| Kolumn | Typ | Beskrivning |
|---|---|---|
| lead_id | UUID | Koppling till leads-tabellen |
| pagespeed_mobile | INTEGER | PageSpeed-poäng mobil (0–100) |
| pagespeed_desktop | INTEGER | PageSpeed-poäng dator (0–100) |
| has_ssl | BOOLEAN | Har HTTPS? |
| has_contact_form | BOOLEAN | Har kontaktformulär? |
| has_google_analytics | BOOLEAN | Har Google Analytics? |
| has_social_links | BOOLEAN | Länk till sociala medier? |
| has_blog | BOOLEAN | Har blogg/nyheter? |
| has_google_maps_embed | BOOLEAN | Har karta? |
| meta_title | TEXT | Sidans titel i Google |
| meta_description | TEXT | Sidans beskrivning i Google |
| copyright_year | INTEGER | Senast uppdaterad (copyright-år) |
| cms_detected | TEXT | Wix / Strikingly / WordPress etc. |
| issues | JSONB | Lista med identifierade problem |
| recommended_package | TEXT | Liten / Medium / Stor |

---

### Tabell: `emails`
Genererade och skickade mail.

| Kolumn | Typ | Beskrivning |
|---|---|---|
| lead_id | UUID | Koppling till leads-tabellen |
| subject | TEXT | Ämnesrad |
| body_text | TEXT | Plaintext-version |
| body_html | TEXT | HTML-version med footer |
| to_email | TEXT | Mottagarens e-post |
| status | TEXT | draft → sent → bounced → opened → replied |
| sent_at | TIMESTAMPTZ | Tidpunkt för utskick |

---

### Tabell: `pipeline_runs`
Logg för varje automatisk körning.

| Kolumn | Typ | Beskrivning |
|---|---|---|
| started_at | TIMESTAMPTZ | Starttid |
| finished_at | TIMESTAMPTZ | Sluttid |
| scraped_count | INTEGER | Antal nya leads |
| analyzed_count | INTEGER | Antal analyserade hemsidor |
| emails_sent_count | INTEGER | Antal mail skickade |
| errors_count | INTEGER | Antal fel |
| status | TEXT | running / completed / failed |
| log | TEXT | Sammanfattning |

---

## 6. API-nycklar

Alla nycklar sparas som **GitHub Secrets** för automatisk körning, och i en lokal `.env`-fil för manuell körning.

| Nyckel | Tjänst | Används till |
|---|---|---|
| GOOGLE_PLACES_API_KEY | Google Cloud | Söka företag + PageSpeed |
| PAGESPEED_API_KEY | Google Cloud | Mäta laddningstider (kan vara samma nyckel) |
| OPENAI_API_KEY | OpenAI | Generera mail med GPT-4o-mini |
| SUPABASE_URL | Supabase | Databaskoppling |
| SUPABASE_SERVICE_KEY | Supabase | Skriv- och läsbehörighet |
| SMTP_USER | Gmail | elias.ivanoff@gmail.com |
| SMTP_PASSWORD | Gmail | App Password (16 tecken) |

### Skapa/hitta nycklarna:

**Google Cloud:**  
console.cloud.google.com → APIs → Credentials  
Aktivera: Places API (New), PageSpeed Insights API

**OpenAI:**  
platform.openai.com → API Keys

**Supabase:**  
app.supabase.com → Projekt → Settings → API

**Gmail App Password:**  
myaccount.google.com → Säkerhet → 2-stegsverifiering → Applösenord  
Välj: "E-post" + "Mac" → Generera

---

## 7. Lokal `.env`-fil

Skapa filen `/Users/elias/lead-machine/.env`:

```
GOOGLE_PLACES_API_KEY=din_nyckel_här
PAGESPEED_API_KEY=din_nyckel_här
OPENAI_API_KEY=din_nyckel_här
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SMTP_USER=elias.ivanoff@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## 8. Köra manuellt

```bash
# Gå till pipeline-mappen
cd /Users/elias/lead-machine/pipeline

# Aktivera Python-miljö (om installerad)
# source .venv/bin/activate

# Hela pipelinen (alla 4 steg)
python main.py

# Enskilda steg
python main.py --scrape      # Steg 1: Hitta företag
python main.py --analyze     # Steg 2: Analysera hemsidor
python main.py --generate    # Steg 3: Generera mail
python main.py --send        # Steg 4: Skicka mail
python main.py --send-one    # Skicka exakt ett mail (test)
```

**Loggar** sparas i: `pipeline/pipeline.log` och `pipeline/send.log`

---

## 9. Automatisering

### Alternativ A: GitHub Actions (rekommenderat)

Pipelinen körs automatiskt via GitHub Actions på repot:  
`github.com/EliasxCalidad/lead-machine`

Alla API-nycklar läggs in under:  
**Settings → Secrets and variables → Actions**

Kontrollera att workflows är aktiverade:  
**Actions → fliken "I understand my workflows"**

---

### Alternativ B: Lokal cron (macOS)

Skriptet `run_pipeline.sh` kan köras via cron lokalt:

```bash
# Öppna crontab
crontab -e

# Lägg till (kör kl 09:00 varje dag)
0 9 * * * /Users/elias/lead-machine/run_pipeline.sh
```

Kräver att datorn är påslagen. GitHub Actions är att föredra.

---

## 10. Dashboard

```bash
cd /Users/elias/lead-machine/dashboard
npm run dev
# Öppna: http://localhost:3000
# Lösenord: calidad2024
```

Dashboarden visar:
- Totalt antal leads
- Antal mail skickade / öppnade / besvarade
- Öppningsfrekvens och svarsfrekvens
- Lista med alla leads och deras status

---

## 11. Mailgränser och spam-skydd

| Vecka | Max mail/dag | Syfte |
|---|---|---|
| Vecka 1 | 10 | Värma upp Gmail-kontot |
| Vecka 2 | 20 | Gradvis ökning |
| Vecka 3+ | 35 | Normal volym |

Ändras i `pipeline/config.py`:
```python
EMAILS_PER_DAY = 10  # Ändra till 20 eller 35
```

**Spam-skydd inbyggt:**
- 10–30 minuters slumpmässig paus mellan varje mail
- Mail skickas i flera omgångar under dagen
- Avsändare signeras som "Elias | NextLead" (personligt, inte bolagsnamn)
- HTML-mail har avregistreringslänk (nextlead.se/avregistrera)

---

## 12. Målgrupp och erbjudande

**Målgrupp:** Svenska callcenters och säljbolag (Stockholm, expandera sedan)

**Erbjudande i mailutskick:**
> 50 gratis provleads — B2B eller B2C — helt utan krav eller bindning.  
> Leverans inom 24h. Varje lead: namn, e-post, telefon, stad, bransch.

**Syfte med gratiserbjudandet:** Låt kunden testa kvaliteten. Konverterar de → betalande kund.

**Kontakt i mail:**  
Elias Ivanoff, 072 007 33 48, elias.ivanoff@gmail.com

---

## 13. Felsökning

### Google Places returnerar 403
Gå till console.cloud.google.com → Credentials → Klicka på API-nyckeln  
→ Application restrictions → Sätt till **"None"** → Spara

### Gmail blockerar utskick / SMTP-fel
App Password kan ha gått ut eller återkallats.  
Skapa ett nytt: myaccount.google.com → Säkerhet → Applösenord  
Uppdatera `.env` och GitHub Secrets.

### Supabase "unique violation"-fel
Normalt — företaget finns redan i databasen. Pipelinen hoppar automatiskt över det.

### GitHub Actions kör inte
1. Gå till github.com/EliasxCalidad/lead-machine
2. Klicka på **Actions**-fliken
3. Om workflows är inaktiverade — klicka på knappen för att aktivera

### Inga leads hittas / pipeline-körs men scrape=0
Kontrollera att Google Places API är aktiverat i Cloud Console och att nyckeln inte har IP-begränsningar.

### Pipeline-loggen är tom
Kontrollera att `.env`-filen finns och är korrekt ifylld, eller att GitHub Secrets är inlagda.

---

## 14. Nästa steg

1. **Öka dagsgränsen** — från 10 till 20 mail/dag efter 1 vecka, sedan 35/dag
2. **Byt till SendGrid** — när calidad.se-domänen är konfigurerad hos one.com (domänverifiering krävs för att slippa hamna i spam)
3. **Deploya dashboard på Vercel** — så kollegor kan se statistik utan att starta lokalt

---

*Dokumentation genererad 2026-05-11*
