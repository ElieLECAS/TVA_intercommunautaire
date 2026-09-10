"""Intégration du module de validation structurelle fourni (10 pays).

STATUT ACTUEL : le fichier du module fourni par le brief n'est pas encore
présent dans ce dépôt (voir PLAN.md §0 — à récupérer sur la page Simplonline
du brief, il n'était pas dans les liens de ressources collés dans la
conversation). Tant qu'il n'est pas branché ici, toute ligne appartenant à un
pays couvert reçoit un verdict 'indetermine' / motif 'module_non_branche' —
volontairement, pour ne jamais faire passer une absence d'outillage pour une
invalidité (même principe que pour une indisponibilité VIES).

Une fois le fichier récupéré :
1. Le déposer dans ce dossier (ex. `app/structural_module_fourni.py`).
2. Remplacer le corps de `_appeler_module_fourni` ci-dessous par l'appel réel
   (adapter la signature à celle du module : il faudra lire son code pour
   savoir s'il attend le numéro avec ou sans préfixe pays, etc. — cf. brief :
   "Lisez-le : vous devrez expliquer en soutenance ce que 'structurellement
   valide' recouvre").
3. Cataloguer ici, en commentaire, chaque (verdict, motif) que le module peut
   renvoyer et la décision prise pour chacun (PLAN.md §1 et §6).
"""

from app.normalize import pays_est_couvert

VERDICT_VALIDE = "valide"
VERDICT_INVALIDE = "invalide"
VERDICT_INDETERMINE = "indetermine"


def _appeler_module_fourni(pays: str, numero_normalise: str) -> tuple[str, str]:
    # TODO : brancher le vrai module ici une fois récupéré. Voir docstring du fichier.
    raise NotImplementedError("module de validation structurelle non branché")


def valider_structurellement(pays_declare: str | None, numero_normalise: str | None) -> tuple[str, str]:
    """Renvoie (verdict, motif) pour une ligne déjà normalisée.

    Ne lève jamais d'exception : les cas qu'on ne peut pas trancher (pays hors
    liste, numéro absent, module indisponible) renvoient un verdict explicite
    plutôt qu'une erreur.
    """
    if numero_normalise is None:
        return VERDICT_INVALIDE, "numero_absent"

    if not pays_est_couvert(pays_declare):
        return VERDICT_INDETERMINE, "pays_non_couvert"

    try:
        return _appeler_module_fourni(pays_declare, numero_normalise)
    except NotImplementedError:
        return VERDICT_INDETERMINE, "module_non_branche"
