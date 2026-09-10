"""API REST de validation de TVA intracommunautaire.

Le contrat de réponse est le vrai sujet (cf. brief) : chaque verdict expose
son origine (structurel / frais VIES / connu en cache / cache périmé /
aucune donnée) et sa fraîcheur — jamais un simple valide/invalide nu.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.config import VIES_VERDICT_TTL_DAYS  # noqa: E402
from app.db import get_connection  # noqa: E402
from app.verification_service import verifier_pour_facturation  # noqa: E402

app = FastAPI(
    title="Validation TVA intracommunautaire",
    description=(
        "Verifie un numero de TVA avant emission d'une facture hors taxe. "
        "Chaque reponse porte le verdict, son origine et sa fraicheur."
    ),
    version="0.1.0",
)


class VerificationResponse(BaseModel):
    pays: str
    numero: str
    verdict: str
    origine: str
    detail: str | None = None
    date_verification: datetime | None = None
    age_jours: float | None = None


@app.get("/verification/{pays}/{numero}", response_model=VerificationResponse)
def verifier(pays: str, numero: str, ttl_jours: int = VIES_VERDICT_TTL_DAYS) -> VerificationResponse:
    """Verifie un numero de TVA. `ttl_jours` permet de forcer une fraicheur
    differente du defaut (utile pour demontrer le mecanisme en soutenance)."""
    with get_connection() as conn:
        resultat = verifier_pour_facturation(conn, pays, numero, ttl_days=ttl_jours)
    return VerificationResponse(
        pays=resultat.pays,
        numero=resultat.numero,
        verdict=resultat.verdict,
        origine=resultat.origine,
        detail=resultat.detail,
        date_verification=resultat.date_verification,
        age_jours=resultat.age_jours,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
