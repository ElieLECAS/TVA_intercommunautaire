"""Pipeline de chargement : lecture CSV -> normalisation -> dédoublonnage ->
validation structurelle -> upsert idempotent dans PostgreSQL.

Commande unique attendue en fin de J1 : `python scripts/load_referentiel.py`.
"""

import logging

import pandas as pd

from app.dedupe import flag_duplicates
from app.normalize import normalize_numero, normalize_pays
from app.structural_validation import valider_structurellement

logger = logging.getLogger(__name__)


def load_dataframe(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df = df.rename(columns={"numero_tva": "numero_brut"})

    df["pays_declare"] = df["pays_declare"].map(normalize_pays)
    df["numero_normalise"] = df.apply(
        lambda row: normalize_numero(row["pays_declare"], row["numero_brut"]), axis=1
    )
    df["date_saisie"] = pd.to_datetime(df["date_saisie"], errors="coerce").dt.date

    df = flag_duplicates(df)

    verdicts = df.apply(
        lambda row: valider_structurellement(row["pays_declare"], row["numero_normalise"]),
        axis=1,
        result_type="expand",
    )
    df["verdict_structurel"] = verdicts[0]
    df["motif_structurel"] = verdicts[1]

    return df


_UPSERT_SQL = """
INSERT INTO vat_numbers (
    id, raison_sociale, pays_declare, numero_brut, numero_normalise,
    source_saisie, date_saisie, verdict_structurel, motif_structurel,
    is_duplicate, updated_at
)
VALUES (
    %(id)s, %(raison_sociale)s, %(pays_declare)s, %(numero_brut)s, %(numero_normalise)s,
    %(source_saisie)s, %(date_saisie)s, %(verdict_structurel)s, %(motif_structurel)s,
    %(is_duplicate)s, now()
)
ON CONFLICT (id) DO UPDATE SET
    raison_sociale = EXCLUDED.raison_sociale,
    pays_declare = EXCLUDED.pays_declare,
    numero_brut = EXCLUDED.numero_brut,
    numero_normalise = EXCLUDED.numero_normalise,
    source_saisie = EXCLUDED.source_saisie,
    date_saisie = EXCLUDED.date_saisie,
    verdict_structurel = EXCLUDED.verdict_structurel,
    motif_structurel = EXCLUDED.motif_structurel,
    is_duplicate = EXCLUDED.is_duplicate,
    updated_at = now();
"""

# Deuxième passe séparée : duplicate_of_id référence une autre ligne de la
# même table. On la fixe une fois que toutes les lignes existent déjà, pour
# ne jamais violer la contrainte de clé étrangère selon l'ordre du batch.
_UPDATE_DUPLICATE_OF_SQL = """
UPDATE vat_numbers SET duplicate_of_id = %(duplicate_of_id)s, updated_at = now()
WHERE id = %(id)s;
"""


def upsert_dataframe(conn, df: pd.DataFrame) -> None:
    records = df.where(pd.notnull(df), None).to_dict(orient="records")

    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, records)

        dup_records = [r for r in records if r["is_duplicate"]]
        if dup_records:
            cur.executemany(_UPDATE_DUPLICATE_OF_SQL, dup_records)

    logger.info(
        "upsert termine : %d lignes, %d doublons flagges", len(records), len(dup_records)
    )
