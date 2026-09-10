#!/usr/bin/env python
"""Test manuel VIES sur 3 numeros (J2, etape 1) : un bon, un a cle fausse,
un invente. Affiche la reponse complete, pas seulement le verdict.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import VIES_DELAY_BETWEEN_CALLS_SECONDS  # noqa: E402
from app.vies_client import ViesClient  # noqa: E402

CAS = [
    ("bon (SA DANONE, confirme par VIES au J1)", "FR", "27552032534"),
    ("cle fausse (meme SIREN, cle alteree)", "FR", "28552032534"),
    ("invente (SIREN qui n'existe probablement pas)", "FR", "99123456789"),
]


def main() -> None:
    with ViesClient() as client:
        for label, pays, numero in CAS:
            print(f"\n=== {label} : {pays} {numero} ===")
            resultat = client.verifier(pays, numero)
            print(f"verdict={resultat['verdict']}  detail={resultat['detail']}  latency={resultat['latency_ms']}ms")
            print(json.dumps(resultat["reponse_brute"], indent=2, ensure_ascii=False))
            time.sleep(VIES_DELAY_BETWEEN_CALLS_SECONDS * 3)


if __name__ == "__main__":
    main()
