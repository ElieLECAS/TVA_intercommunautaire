"""Logique de vérification à la demande (utilisée par l'API).

Un appelant doit toujours savoir 3 choses : le verdict, son origine (une
réponse fraîche de VIES ou une valeur déjà connue), et sa fraîcheur. cf.
brief : "Une API qui renvoie 'valide' sans dire que l'information a huit
mois expose son appelant au même redressement qu'avant."

Ordre de préférence pour répondre :
1. structurellement invalide -> invalide, immédiat, pas besoin de VIES.
2. une vérification VIES déjà en base et encore fraîche (< TTL) -> connue.
3. sinon, on tente un appel VIES en direct :
   - ça répond -> frais.
   - ça ne répond pas (indisponible) mais il existe une vérification
     ancienne -> on la renvoie quand même, en le disant clairement (périmée).
   - ça ne répond pas et il n'y a rien en mémoire -> indéterminé, aucune donnée.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from psycopg.types.json import Json

from app.config import VIES_VERDICT_TTL_DAYS
from app.normalize import normalize_numero, normalize_pays, pays_est_couvert
from app.structural_validation import VERDICT_INVALIDE, valider_structurellement
from app.vies_client import VERDICT_INDETERMINE, ViesClient

ORIGINE_STRUCTUREL = "structurel"
ORIGINE_FRAIS = "frais_vies"
ORIGINE_CACHE = "connu_en_cache"
ORIGINE_CACHE_PERIME = "connu_en_cache_perime"
ORIGINE_AUCUNE = "aucune_donnee"


@dataclass
class ResultatVerification:
    pays: str
    numero: str
    verdict: str
    origine: str
    detail: str | None
    date_verification: datetime | None
    age_jours: float | None


_DERNIERE_VERIF_SQL = """
SELECT verdict, detail, checked_at
FROM vies_verifications
WHERE pays_interroge = %(pays)s AND numero_interroge = %(numero)s
ORDER BY checked_at DESC
LIMIT 1;
"""

_INSERT_VERIFICATION_SQL = """
INSERT INTO vies_verifications (
    vat_number_id, pays_interroge, numero_interroge, verdict, detail, reponse_brute, latency_ms
) VALUES (
    (SELECT id FROM vat_numbers WHERE pays_declare = %(pays)s AND numero_normalise = %(numero)s LIMIT 1),
    %(pays)s, %(numero)s, %(verdict)s, %(detail)s, %(reponse_brute)s, %(latency_ms)s
);
"""


def _age_jours(checked_at: datetime) -> float:
    ref = checked_at if checked_at.tzinfo else checked_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ref).total_seconds() / 86400


def _lire_derniere_verification(conn, pays: str, numero: str):
    with conn.cursor() as cur:
        cur.execute(_DERNIERE_VERIF_SQL, {"pays": pays, "numero": numero})
        return cur.fetchone()


def _enregistrer_verification(conn, pays: str, numero: str, resultat: dict) -> None:
    reponse = resultat["reponse_brute"]
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_VERIFICATION_SQL,
            {
                "pays": pays,
                "numero": numero,
                "verdict": resultat["verdict"],
                "detail": resultat["detail"],
                "reponse_brute": Json(reponse) if reponse is not None else None,
                "latency_ms": resultat["latency_ms"],
            },
        )
    conn.commit()


def verifier_pour_facturation(
    conn, pays_brut: str, numero_brut: str, ttl_days: int = VIES_VERDICT_TTL_DAYS
) -> ResultatVerification:
    pays = normalize_pays(pays_brut)
    numero = normalize_numero(pays, numero_brut)

    if numero is None:
        return ResultatVerification(pays or "", numero_brut, VERDICT_INVALIDE, ORIGINE_STRUCTUREL, "numero_absent", None, None)

    if pays_est_couvert(pays):
        verdict_struct, motif_struct = valider_structurellement(pays, numero)
        if verdict_struct == VERDICT_INVALIDE:
            return ResultatVerification(pays, numero, VERDICT_INVALIDE, ORIGINE_STRUCTUREL, motif_struct, None, None)

    derniere = _lire_derniere_verification(conn, pays, numero)
    if derniere is not None:
        verdict, detail, checked_at = derniere
        # Un 'indetermine' en cache ne vaut jamais reutilisation : ce n'est
        # pas un fait etabli, juste une tentative ratee - on retente plutot
        # que de le servir tel quel pendant tout le TTL.
        if verdict != VERDICT_INDETERMINE:
            age = _age_jours(checked_at)
            if age <= ttl_days:
                return ResultatVerification(pays, numero, verdict, ORIGINE_CACHE, detail, checked_at, age)

    with ViesClient() as client:
        resultat = client.verifier(pays, numero)

    # Chaque tentative reelle est journalisee, meme si elle n'aboutit pas.
    _enregistrer_verification(conn, pays, numero, resultat)

    if resultat["verdict"] != VERDICT_INDETERMINE:
        return ResultatVerification(
            pays, numero, resultat["verdict"], ORIGINE_FRAIS, resultat["detail"],
            datetime.now(timezone.utc), 0.0,
        )

    if derniere is not None and derniere[0] != VERDICT_INDETERMINE:
        # VIES indisponible maintenant, mais un vrai verdict perime existe :
        # on le renvoie quand meme, fraicheur annoncee clairement - mieux
        # qu'un refus sec pour la facturation.
        verdict, detail, checked_at = derniere
        return ResultatVerification(pays, numero, verdict, ORIGINE_CACHE_PERIME, detail, checked_at, _age_jours(checked_at))

    return ResultatVerification(pays, numero, VERDICT_INDETERMINE, ORIGINE_AUCUNE, resultat["detail"], None, None)
