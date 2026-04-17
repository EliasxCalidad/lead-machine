# Lead Machine — Setup-guide

## Steg 1: Skapa konton (engångsjobb)

### Supabase (databasen)
1. Gå till supabase.com → skapa gratis konto
2. Skapa nytt projekt, välj "Europe (Frankfurt)"
3. Gå till "SQL Editor" → klistra in innehållet från `supabase/schema.sql` → kör

### Google Cloud (för Maps-scraping)
1. console.cloud.google.com → skapa projekt
2. Aktivera dessa APIs:
   - Places API (New)
   - PageSpeed Insights API
3. Skapa API-nyckel under "Credentials"

### Anthropic (Claude)
1. console.anthropic.com → skapa konto
2. Skapa API-nyckel

### SendGrid (email)
1. sendgrid.com → skapa gratis konto
2. Verifiera din domän (calidad.se) — kritiskt för deliverability
3. Skapa API-nyckel med "Mail Send" behörighet
4. Sätt upp SendGrid Event Webhook för open/click tracking

---

## Steg 2: Konfigurera miljövariabler

### Pipeline (Python)
```bash
cp .env.example .env
# Fyll i alla värden i .env
```

### Dashboard (Next.js)
```bash
cd dashboard
cp .env.local.example .env.local
# Fyll i Supabase URL och anon key (finns i Supabase → Settings → API)
```

---

## Steg 3: Installera Python-beroenden

```bash
cd pipeline
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Steg 4: Testa pipeline manuellt

```bash
cd pipeline
source venv/bin/activate

# Testa att scrapa 10 leads
python main.py --scrape

# Testa att analysera dem
python main.py --analyze

# Generera mail med Claude
python main.py --generate

# KOLLA dashboard innan du skickar!
# Kör sedan:
python main.py --send
```

---

## Steg 5: Deploya dashboard på Vercel

```bash
cd dashboard
npx vercel --prod
# Följ instruktionerna, lägg till env-variabler i Vercel-dashboarden
```

---

## Steg 6: Sätt upp automatisk körning

### Railway (rekommenderat — $5/mån)
1. railway.app → nytt projekt
2. Koppla till GitHub-repot
3. Sätt working directory till `/pipeline`
4. Sätt start command: `python main.py`
5. Lägg till Cron Schedule: `0 8 * * *` (kör varje dag kl 08:00)
6. Lägg till alla .env-variabler

---

## Daglig pipeline-körning (automatisk)

```
Varje dag kl 08:00:
  1. Skrapar 100 nya företag från Google Maps
  2. Analyserar deras hemsidor (~35 st/dag)
  3. Genererar personliga mail med Claude
  4. Skickar 35 mail (1 050/månad)
```

---

## Viktigt om GDPR

- B2B cold email är tillåtet under "legitimate interest" (GDPR art. 6.1.f)
- Vi skickar KUN till företag (inte privatpersoner)
- Varje mail har avprenumerera-länk
- Lagra inte mer data än nödvändigt

---

## Felsökning

**"No places found"** → Kontrollera Google Places API-nyckel och att API:et är aktiverat

**"PageSpeed timeout"** → Normal för långsamma sidor, hanteras automatiskt

**"SendGrid 403"** → Domänen är inte verifierad ännu — gör det i SendGrid-dashboarden

**"Supabase unique violation"** → Normalt — lead finns redan i databasen
