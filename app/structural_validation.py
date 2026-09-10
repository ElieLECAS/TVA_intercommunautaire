"""Intégration de la validation structurelle (10 pays).

STATUT : le module que le brief annonce comme fourni n'existe pas — confirmé
par le formateur (Guillaume Soulat), après vérification que les ressources
publiques de la Commission européenne n'en contiennent pas non plus le détail
(voir PLAN.md §0 et journal-de-bord.md). Ce n'est pas un fichier égaré : le
brief l'annonce, il n'a jamais été fourni pour cette session.

Ce fichier appelle donc `app/structural_module_substitut.py` : un module
écrit à partir d'algorithmes de clé de contrôle publiquement documentés,
explicitement nommé "substitut" et jamais présenté comme "le module fourni".

Conséquence à assumer en soutenance : "structurellement valide" veut dire ici
"conforme à l'algorithme public standard du pays", pas "vérifié contre un
module remis par le brief" — puisqu'aucun n'a existé.
"""

from app.normalize import is_blank, pays_est_couvert
from app.structural_module_substitut import valider as _valider_substitut

VERDICT_VALIDE = "valide"
VERDICT_INVALIDE = "invalide"
VERDICT_INDETERMINE = "indetermine"


def _appeler_module(pays: str, numero_normalise: str) -> tuple[str, str]:
    return _valider_substitut(pays, numero_normalise)


def valider_structurellement(pays_declare: str | None, numero_normalise: str | None) -> tuple[str, str]:
    """Renvoie (verdict, motif) pour une ligne déjà normalisée.

    Ne lève jamais d'exception : les cas qu'on ne peut pas trancher (pays hors
    liste, numéro absent) renvoient un verdict explicite plutôt qu'une erreur.
    """
    if is_blank(numero_normalise):
        return VERDICT_INVALIDE, "numero_absent"

    if not pays_est_couvert(pays_declare):
        return VERDICT_INDETERMINE, "pays_non_couvert"

    return _appeler_module(pays_declare, numero_normalise)
