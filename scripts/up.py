#!/usr/bin/env python
"""Lance toute la pile depuis zero : Postgres (Docker) + schema + chargement.

Seule commande necessaire apres un clone (uv installe les dependances
Python automatiquement avant d'executer ce script) :

    uv run scripts/up.py

Pour la suite (campagne VIES, rapport, API), voir le README.
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _attendre_postgres(tentatives: int = 20, delai: float = 1.5) -> None:
    import psycopg

    from app.config import DATABASE_URL

    for i in range(tentatives):
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=3):
                print("Postgres pret.")
                return
        except psycopg.OperationalError:
            print(f"en attente de Postgres... ({i + 1}/{tentatives})")
            time.sleep(delai)
    raise RuntimeError(
        "Postgres ne repond pas apres l'attente prevue - verifiez `docker compose logs postgres`."
    )


def main() -> None:
    print("== 1/3 : demarrage de Postgres (docker compose up -d) ==")
    subprocess.run(["docker", "compose", "up", "-d"], check=True)

    print("== 2/3 : attente de la disponibilite de Postgres ==")
    _attendre_postgres()

    print("== 3/3 : schema + chargement du referentiel ==")
    subprocess.run([sys.executable, "scripts/load_referentiel.py"], check=True)

    print(
        "\nPile prete. Suite :\n"
        "  uv run scripts/run_vies_campaign.py --sample 200\n"
        "  uv run scripts/generate_report.py\n"
        "  uv run uvicorn api.main:app --reload   (puis http://127.0.0.1:8000/docs)"
    )


if __name__ == "__main__":
    main()
