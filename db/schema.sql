-- Schéma du référentiel de TVA intracommunautaire.
-- Idempotent : peut être rejoué sans erreur sur une base déjà initialisée.

CREATE TABLE IF NOT EXISTS vat_numbers (
    id                  INTEGER PRIMARY KEY,        -- id du fichier source : clé stable, garantit qu'un rechargement upserte au lieu de dupliquer
    raison_sociale      TEXT NOT NULL,               -- brut
    pays_declare        TEXT NOT NULL,               -- brut
    numero_brut         TEXT NOT NULL,               -- brut, tel que saisi
    numero_normalise    TEXT,                        -- déduit (app/normalize.py)
    source_saisie       TEXT,                        -- brut
    date_saisie         DATE,                        -- brut
    verdict_structurel  TEXT,                        -- déduit : 'valide' | 'invalide' | 'indetermine'
    motif_structurel    TEXT,                        -- déduit : motif renvoyé par le module fourni (ou notre propre motif si le module ne couvre pas le cas)
    is_duplicate        BOOLEAN NOT NULL DEFAULT FALSE,   -- déduit
    duplicate_of_id     INTEGER REFERENCES vat_numbers(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vat_numbers_pays_numero_normalise ON vat_numbers (pays_declare, numero_normalise);
CREATE INDEX IF NOT EXISTS idx_vat_numbers_verdict_structurel ON vat_numbers (verdict_structurel);

-- Historique des vérifications VIES : une ligne par appel, jamais écrasée.
-- Permet de répondre à "depuis quand ce verdict tient" (fraîcheur) et de servir
-- de mécanisme de reprise (cf. requête de sélection du prochain lot dans PLAN.md §3).
CREATE TABLE IF NOT EXISTS vies_verifications (
    id                  SERIAL PRIMARY KEY,
    vat_number_id       INTEGER NOT NULL REFERENCES vat_numbers(id),
    pays_interroge      TEXT NOT NULL,
    numero_interroge    TEXT NOT NULL,
    verdict             TEXT NOT NULL,               -- 'valide' | 'invalide' | 'indetermine'
    detail               TEXT,
    reponse_brute        JSONB,                       -- réponse VIES complète, pour ne rien perdre de ce qu'elle renvoie
    checked_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    latency_ms           INTEGER
);

CREATE INDEX IF NOT EXISTS idx_vies_verifications_vat_number_id ON vies_verifications (vat_number_id);
CREATE INDEX IF NOT EXISTS idx_vies_verifications_checked_at ON vies_verifications (checked_at);
