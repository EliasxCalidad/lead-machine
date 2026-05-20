#!/bin/bash
# Lead Machine — daglig pipeline
# Körs av cron kl 09:00 varje dag

cd /Users/elias/lead-machine/pipeline

# Ladda miljövariabler från .env
set -a
source /Users/elias/lead-machine/.env
set +a

# Kör pipeline och logga med datum
echo "" >> pipeline.log
echo "=== CRON START $(date '+%Y-%m-%d %H:%M:%S') ===" >> pipeline.log
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 main.py >> pipeline.log 2>&1
echo "=== CRON SLUT $(date '+%Y-%m-%d %H:%M:%S') ===" >> pipeline.log
