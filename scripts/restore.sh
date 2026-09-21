#!/bin/sh
# Atkūrimo skriptas iš atsarginės kopijos.
# Naudojimas: ./scripts/restore.sh <kopija.sql.gz>
# Pvz.:      ./scripts/restore.sh duomenys/atsargines_kopijos/mokykla_db_2026-09-21_12-00-00.sql.gz

set -e

if [ -z "$1" ]; then
    echo "Naudojimas: $0 <kopija.sql.gz>"
    echo "Prieinamos kopijos:"
    ls -lh duomenys/atsargines_kopijos/*.sql.gz 2>/dev/null || echo "  (kopijų nėra)"
    exit 1
fi

KOPIJA="$1"

if [ ! -f "$KOPIJA" ]; then
    echo "[KLAIDA] Failas nerastas: $KOPIJA"
    exit 1
fi

echo "==============================================="
echo "ATSTATOMA DUOMENŲ BAZĖ"
echo "  Šaltinis: $KOPIJA"
echo "==============================================="
echo ""
echo "DĖMESIO: dabartinė DB bus perrašyta!"
printf "Ar tęsiate? (yes/no): "
read ATSAKYMAS

if [ "$ATSAKYMAS" != "yes" ]; then
    echo "Atšaukta."
    exit 0
fi

echo ""
echo "Atkuriama..."
gunzip -c "$KOPIJA" | docker exec -i mokykla_db psql -U mokykla -d mokykla_db

echo ""
echo "[OK] Duomenų bazė sėkmingai atstatyta iš: $KOPIJA"
