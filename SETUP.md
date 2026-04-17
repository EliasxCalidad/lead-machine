# Lead Machine — Dokumentation

Automatisk cold email-pipeline för Calidad. Hittar svenska tjänsteföretag på Google Maps,
analyserar deras hemsidor, genererar personliga mail med AI och skickar dem automatiskt.

---

## Hur det fungerar

```
Varje dag (automatiskt via GitHub Actions):

07:00  Scraping     → Hittar ~100 nya företag på Google Maps (Stockholm)
       Analys       → Kollar varje hemsida på ~35 företag
       Generering   → Skriver personliga mail med OpenAI

09:00  Skickar 3 mail (10–30 min mellanrum)
12:00  Skickar 3 mail (10–30 min mellanrum)
15:00  Skickar 4 mail (10–30 min mellanrum)

Totalt: ~10 mail/dag → ~300 mail/månad
```

---

## Vad analyseras på varje hemsida

- Webbläsaren varnar att sidan "inte är säker" (saknar SSL)
- Hemsidan ser trasig ut på mobilen
- Det finns inget sätt att kontakta er via hemsidan
- Hemsidan syns knappt i Google (saknar titel/beskrivning)
- Ingen koll på besökare (saknar Google Analytics)
- Inte kopplad till sociala medier
- Ingen karta — kunder vet inte var ni finns
- Hemsidan ser gammal och inte uppdaterad ut
- Byggd på gratisverktyg (Wix, Strikingly etc.)
- Laddar långsamt på mobil/dator

---

## Teknikstack

| Del | Teknologi |
|-----|-----------|
| Scraping | Google Places API (New) |
| Hemsideanalys | Python + BeautifulSoup |
| AI-generering | OpenAI GPT-4o-mini |
| Databas | Supabase (PostgreSQL) |
| Mailutskick | Gmail SMTP (elias.ivanoff@gmail.com) |
| Automation | GitHub Actions |
| Dashboard | Next.js (lokalt på localhost:3000) |

---

## Mailgräns och spam-skydd

- Max 10 mail/dag (ökas till 20 vecka 2, 35 vecka 3+)
- 10–30 minuters slumpmässig paus mellan varje mail
- Mail skickas i 3 omgångar under dagen (ser mänskligt ut)
- Ingen SendGrid ännu — byt när calidad.se-domänen är klar

---

## API-nycklar (sparade som GitHub Secrets)

| Nyckel | Används till |
|--------|-------------|
| GOOGLE_PLACES_API_KEY | Hitta företag på Google Maps |
| PAGESPEED_API_KEY | Mäta laddningstid på hemsidor |
| OPENAI_API_KEY | Generera mail med GPT-4o-mini |
| SUPABASE_URL | Databaskoppling |
| SUPABASE_SERVICE_KEY | Skriv/läs till databasen |
| SMTP_USER | elias.ivanoff@gmail.com |
| SMTP_PASSWORD | Gmail App Password |

---

## Köra manuellt

```bash
cd pipeline

# Hela pipelinen
python main.py

# Enskilda steg
python main.py --scrape     # Hitta företag
python main.py --analyze    # Analysera hemsidor
python main.py --generate   # Generera mail
python main.py --send       # Skicka mail
```

---

## Dashboard (realtidsöversikt)

```bash
cd dashboard
npm run dev
# Öppna http://localhost:3000
# Lösenord: calidad2024
```

---

## Nästa steg

1. **Höj dagsgränsen** — från 10 till 20 mail/dag efter en vecka
2. **Byt till SendGrid** — när calidad.se-domänen är konfigurerad hos one.com
   (se dokumentation i minnet — domänverifiering krävs)
3. **Deploya dashboard på Vercel** — så kollegor kan se statistik utan att starta lokalt

---

## Felsökning

**Google Places 403** → Gå till console.cloud.google.com → API-nyckel → Application restrictions → sätt till "None"

**Gmail blockerar utskick** → App Password kan ha gått ut — skapa ett nytt på myaccount.google.com → Säkerhet → Applösenord

**Supabase "unique violation"** → Normalt — företaget finns redan i databasen

**GitHub Actions kör inte** → Gå till github.com/EliasxCalidad/lead-machine → Actions → aktivera workflows
