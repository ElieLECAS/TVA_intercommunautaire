#!/usr/bin/env python
"""Mesure le temps de reponse de VIES sur quelques appels reels (item 7, J1).

Objectif : ne pas decouvrir le cout d'un appel VIES en plein milieu de la
campagne du J2. On chronometre ici, on extrapole, et scripts/load_referentiel.py
donne deja le volume reel a interroger (colonne verdict_structurel une fois
le module branche).
"""

import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (  # noqa: E402
    VIES_BASE_URL,
    VIES_DELAY_BETWEEN_CALLS_SECONDS,
    VIES_TIMEOUT_SECONDS,
)

# Numero donne en exemple dans les ressources du brief lui-meme.
NUMEROS_TEST = [
    ("FR", "27552032534"),
    ("FR", "27552032534"),
    ("FR", "27552032534"),
]


def main() -> None:
    latences_ms = []
    with httpx.Client(timeout=VIES_TIMEOUT_SECONDS) as client:
        for pays, numero in NUMEROS_TEST:
            url = f"{VIES_BASE_URL}/ms/{pays}/vat/{numero}"
            start = time.perf_counter()
            try:
                resp = client.get(url)
                elapsed_ms = (time.perf_counter() - start) * 1000
                print(f"{url} -> {resp.status_code} en {elapsed_ms:.0f} ms")
                print(resp.text[:500])
            except httpx.HTTPError as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                print(f"{url} -> ERREUR ({exc!r}) apres {elapsed_ms:.0f} ms")
            latences_ms.append(elapsed_ms)
            print("-" * 60)
            time.sleep(VIES_DELAY_BETWEEN_CALLS_SECONDS)

    print(f"\nLatences (ms) : {[round(v) for v in latences_ms]}")
    moyenne = statistics.mean(latences_ms)
    print(f"Moyenne : {moyenne:.0f} ms")

    for volume in (10000, 9481, 200):
        total_s = (moyenne / 1000) * volume
        print(f"Extrapolation sur {volume} appels : {total_s / 60:.1f} min ({total_s / 3600:.2f} h)")


if __name__ == "__main__":
    main()
