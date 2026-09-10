"""Client VIES.

Règle centrale (vue en direct le J1, cf. journal-de-bord.md) : `userError`
est un code de statut, pas seulement un champ d'erreur. Il vaut "VALID"
quand la vérification a réellement abouti — dans ce cas seulement, `isValid`
donne le vrai verdict.

Deuxième règle, découverte en testant 3 numéros à la main le J2 (cf.
journal-de-bord.md) : tous les codes non-"VALID" ne se valent pas.
- `INVALID` revient en <500ms (souvent <50ms), y compris sur un numéro dont
  seul le chiffre de tête était faux (testé et confirmé). Ça ressemble à un
  contrôle de format fait par VIES lui-même, avant tout aller-retour vers
  l'État membre : traité ici comme un vrai 'invalide', symétrique de notre
  propre validation structurelle.
- Un numéro bien formé (checksum correct) sur ce même contrôle bascule sur
  `MS_MAX_CONCURRENT_REQ`/`MS_UNAVAILABLE` — confirmé en direct avec un
  numéro BE construit exprès pour passer ce premier filtre. Ces codes-là
  restent 'indetermine' : ils parlent de la disponibilité de l'État membre,
  pas du numéro.
"""

import logging
import time

import httpx

from app.config import VIES_BASE_URL, VIES_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

VERDICT_VALIDE = "valide"
VERDICT_INVALIDE = "invalide"
VERDICT_INDETERMINE = "indetermine"

_STATUTS_SUCCES = {"VALID", ""}
_STATUTS_REJET_FORMAT = {"INVALID"}


class ViesClient:
    def __init__(self, base_url: str = VIES_BASE_URL, timeout: float = VIES_TIMEOUT_SECONDS):
        self._client = httpx.Client(timeout=timeout)
        self._base_url = base_url

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ViesClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def verifier(self, pays: str, numero: str) -> dict:
        """Interroge VIES. Ne leve jamais d'exception métier : renvoie toujours
        un dict {verdict, detail, reponse_brute, latency_ms}, y compris en cas
        de panne réseau ou de timeout.
        """
        url = f"{self._base_url}/ms/{pays}/vat/{numero}"
        start = time.perf_counter()

        try:
            resp = self._client.get(url)
        except httpx.HTTPError as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning("appel VIES en echec (%s %s) : %r", pays, numero, exc)
            return {
                "verdict": VERDICT_INDETERMINE,
                "detail": f"erreur_reseau:{exc.__class__.__name__}",
                "reponse_brute": None,
                "latency_ms": latency_ms,
            }

        latency_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code != 200:
            return {
                "verdict": VERDICT_INDETERMINE,
                "detail": f"http_{resp.status_code}",
                "reponse_brute": {"status_code": resp.status_code, "text": resp.text[:2000]},
                "latency_ms": latency_ms,
            }

        try:
            data = resp.json()
        except ValueError:
            return {
                "verdict": VERDICT_INDETERMINE,
                "detail": "reponse_non_json",
                "reponse_brute": {"text": resp.text[:2000]},
                "latency_ms": latency_ms,
            }

        user_error = data.get("userError", "")
        if user_error in _STATUTS_REJET_FORMAT:
            return {
                "verdict": VERDICT_INVALIDE,
                "detail": user_error,
                "reponse_brute": data,
                "latency_ms": latency_ms,
            }
        if user_error not in _STATUTS_SUCCES:
            return {
                "verdict": VERDICT_INDETERMINE,
                "detail": user_error,
                "reponse_brute": data,
                "latency_ms": latency_ms,
            }

        verdict = VERDICT_VALIDE if data.get("isValid") else VERDICT_INVALIDE
        return {
            "verdict": verdict,
            "detail": "ok",
            "reponse_brute": data,
            "latency_ms": latency_ms,
        }
