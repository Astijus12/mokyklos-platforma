-- Vietinės kūrimo aplinkos paruošimas (PostgreSQL 16).
--
-- Sukuria programos naudotoją (rolę) „mokykla“ ir dvi duomenų bazes:
--   mokykla_db   – kūrimui (programa ir fono procesas),
--   mokykla_test – PostgreSQL testams (pytest -m postgres).
--
-- Paleidimas iš projekto katalogo (paprašys „postgres“ slaptažodžio, nustatyto diegiant):
--   & "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -f scripts\sukurti_duomenu_baze.sql
--
-- Slaptažodis sutampa su numatytuoju DB_PASSWORD iš .env.example ir docker-compose.yml.
-- Jis skirtas tik kūrimo aplinkai – produkcijoje nustatomas kitas.
-- Scenarijų galima paleisti kelis kartus: jau esantys objektai neperkuriami.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mokykla') THEN
        CREATE ROLE mokykla LOGIN PASSWORD 'slaptas123';
    END IF;
END
$$;

-- CREATE DATABASE negalima vykdyti DO bloke, todėl komanda sudaroma užklausa
-- ir įvykdoma psql komanda \gexec tik tada, kai tokios bazės dar nėra.
SELECT 'CREATE DATABASE mokykla_db OWNER mokykla ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mokykla_db')\gexec

SELECT 'CREATE DATABASE mokykla_test OWNER mokykla ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mokykla_test')\gexec
