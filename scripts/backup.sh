#!/bin/sh
# Kasdien vykdomas atsarginių kopijų skriptas.
# Sukuria .sql.gz dump'ą su data-laiko žyma ir ištrina senesnius nei 30 dienų.

set -e

TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/backups"
BACKUP_FILE="$BACKUP_DIR/mokykla_db_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$TIMESTAMP] Pradedama atsarginė kopija..."

pg_dump -h db -U mokykla -d mokykla_db --clean --if-exists | gzip > "$BACKUP_FILE"

if [ -s "$BACKUP_FILE" ]; then
    DYDIS=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$TIMESTAMP] [OK] Sukurta: $BACKUP_FILE ($DYDIS)"
else
    echo "[$TIMESTAMP] [KLAIDA] Tuščias failas - trinamas"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Ištrinti kopijas senesnes nei 30 dienų
DEL=$(find "$BACKUP_DIR" -name "mokykla_db_*.sql.gz" -mtime +30 -type f | wc -l)
if [ "$DEL" -gt 0 ]; then
    find "$BACKUP_DIR" -name "mokykla_db_*.sql.gz" -mtime +30 -type f -delete
    echo "[$TIMESTAMP] Pašalinta $DEL senesnės nei 30 d. kopijos"
fi

echo "[$TIMESTAMP] Baigta."
