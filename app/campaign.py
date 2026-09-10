"""Campagne de vérification VIES.

Reprise après interruption et TTL de fraîcheur reposent sur la même requête :
on ne sélectionne que les numéros structurellement valides, pas doublons, et
jamais vérifiés dans la fenêtre de fraîcheur. Un numéro déjà traité (ou traité
avant l'interruption) sort naturellement du prochain lot — pas besoin d'un
fichier de checkpoint séparé. Chaque vérification est committée dès qu'elle
est faite : une interruption ne perd que l'appel en cours, jamais ceux d'avant.

Les doublons ne sont jamais envoyés à VIES directement : ils héritent du
verdict de la ligne conservée (cf. app/report.py) — encore un appel évité par
ligne en double.
"""

import logging
import time

from psycopg.types.json import Json

from app.config import VIES_DELAY_BETWEEN_CALLS_SECONDS, VIES_VERDICT_TTL_DAYS
from app.vies_client import ViesClient

logger = logging.getLogger(__name__)

_SELECT_BATCH_SQL = """
SELECT vn.id, vn.pays_declare, vn.numero_normalise
FROM vat_numbers vn
WHERE vn.verdict_structurel = 'valide'
  AND NOT vn.is_duplicate
  AND NOT EXISTS (
      SELECT 1 FROM vies_verifications vv
      WHERE vv.vat_number_id = vn.id
        AND vv.checked_at > now() - make_interval(days => %(ttl_days)s)
  )
ORDER BY vn.id
LIMIT %(sample_size)s;
"""

_INSERT_VERIFICATION_SQL = """
INSERT INTO vies_verifications (
    vat_number_id, pays_interroge, numero_interroge, verdict, detail,
    reponse_brute, latency_ms
) VALUES (
    %(vat_number_id)s, %(pays_interroge)s, %(numero_interroge)s, %(verdict)s,
    %(detail)s, %(reponse_brute)s, %(latency_ms)s
);
"""


def _selectionner_lot(conn, sample_size: int, ttl_days: int) -> list[tuple[int, str, str]]:
    with conn.cursor() as cur:
        cur.execute(_SELECT_BATCH_SQL, {"ttl_days": ttl_days, "sample_size": sample_size})
        return cur.fetchall()


def run_campaign(
    conn,
    sample_size: int,
    ttl_days: int = VIES_VERDICT_TTL_DAYS,
    delay_seconds: float = VIES_DELAY_BETWEEN_CALLS_SECONDS,
) -> dict:
    lot = _selectionner_lot(conn, sample_size, ttl_days)
    logger.info("lot selectionne : %d numeros a verifier (ttl=%dj)", len(lot), ttl_days)

    compteurs = {"valide": 0, "invalide": 0, "indetermine": 0}
    traites = 0

    try:
        with ViesClient() as client:
            for i, (vat_number_id, pays, numero) in enumerate(lot):
                resultat = client.verifier(pays, numero)
                compteurs[resultat["verdict"]] += 1

                reponse = resultat["reponse_brute"]
                with conn.cursor() as cur:
                    cur.execute(
                        _INSERT_VERIFICATION_SQL,
                        {
                            "vat_number_id": vat_number_id,
                            "pays_interroge": pays,
                            "numero_interroge": numero,
                            "verdict": resultat["verdict"],
                            "detail": resultat["detail"],
                            "reponse_brute": Json(reponse) if reponse is not None else None,
                            "latency_ms": resultat["latency_ms"],
                        },
                    )
                conn.commit()
                traites += 1

                logger.info(
                    "[%d/%d] %s %s -> %s (%s, %dms)",
                    i + 1, len(lot), pays, numero,
                    resultat["verdict"], resultat["detail"], resultat["latency_ms"],
                )

                if i < len(lot) - 1:
                    time.sleep(delay_seconds)
    except KeyboardInterrupt:
        logger.warning(
            "campagne interrompue : %d/%d traites et deja enregistres. "
            "Relancez la meme commande pour continuer, rien ne sera refait.",
            traites, len(lot),
        )
        raise

    logger.info("campagne terminee : %d traites, %s", traites, compteurs)
    return compteurs
