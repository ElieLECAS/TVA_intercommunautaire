#!/usr/bin/env python
"""Commande unique : charge le référentiel CSV dans PostgreSQL.

Usage:
    python scripts/load_referentiel.py [--csv data/numeros-tva-....csv]

Idempotent : peut être relancé sans dupliquer de lignes (upsert sur id).
"""

import argparse
import glob
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import apply_schema, get_connection  # noqa: E402
from app.loader import load_dataframe, upsert_dataframe  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("load_referentiel")


def _default_csv() -> str:
    matches = glob.glob("data/numeros-tva-*.csv")
    if not matches:
        raise FileNotFoundError("aucun fichier data/numeros-tva-*.csv trouve")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=None, help="chemin du CSV source")
    args = parser.parse_args()

    csv_path = args.csv or _default_csv()
    logger.info("schema : application de db/schema.sql")
    apply_schema()

    logger.info("chargement de %s", csv_path)
    df = load_dataframe(csv_path)
    logger.info("lignes lues : %d", len(df))

    with get_connection() as conn:
        upsert_dataframe(conn, df)

    logger.info("repartition des verdicts structurels :")
    for verdict, count in df["verdict_structurel"].value_counts().items():
        logger.info("  %-12s %d", verdict, count)

    logger.info("motifs :")
    for motif, count in df["motif_structurel"].value_counts().items():
        logger.info("  %-20s %d", motif, count)

    logger.info("doublons detectes : %d", int(df["is_duplicate"].sum()))


if __name__ == "__main__":
    main()
