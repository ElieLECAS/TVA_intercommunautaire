#!/usr/bin/env python
"""Lance une campagne de verification VIES.

Usage:
    python scripts/run_vies_campaign.py [--sample 200] [--ttl-days 90]

Interrompre (Ctrl+C) puis relancer la meme commande ne refait pas les
appels deja enregistres (cf. app/campaign.py).
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.campaign import run_campaign  # noqa: E402
from app.config import SAMPLE_SIZE_DEFAULT, VIES_VERDICT_TTL_DAYS  # noqa: E402
from app.db import get_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=SAMPLE_SIZE_DEFAULT, help="taille de l'echantillon")
    parser.add_argument("--ttl-days", type=int, default=VIES_VERDICT_TTL_DAYS, help="duree de validite d'un verdict")
    args = parser.parse_args()

    with get_connection() as conn:
        run_campaign(conn, sample_size=args.sample, ttl_days=args.ttl_days)


if __name__ == "__main__":
    main()
