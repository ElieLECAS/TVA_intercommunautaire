"""SUBSTITUT au module de validation structurelle annoncé par le brief.

Le module n'existe pas : confirmé par le formateur (voir PLAN.md §0 et
journal-de-bord.md — vérifié au préalable sur les 4 liens publics de la
Commission européenne, aucun ne publie le détail des clés de contrôle par
pays, seulement des généralités).

CE FICHIER N'EST DONC PAS "LE MODULE FOURNI" : ce sont des algorithmes de
clé de contrôle publiquement documentés (format + modulo par pays), du même
type que ceux implémentés par des bibliothèques open-source de référence
(ex. python-stdnum, jsvat). Ils n'ont pas été vérifiés contre une source
officielle unique par pays, seulement contre la logique généralement
documentée. À mentionner explicitement en soutenance : "structurellement
valide" ici veut dire "format + clé de contrôle conformes à l'algorithme
public standard", pas "vérifié contre la spécification officielle de
l'administration fiscale de chaque État".

Limites connues, à assumer telles quelles :
- FR : la formule utilisée est la formule standard (clé = (12 + 3*SIREN) mod
  97). Un petit nombre de numéros historiques utilisent une clé non
  numérique et ne seront jamais validés par cette formule.
- NL : depuis 2020, les entrepreneurs individuels (personnes physiques) ont
  un numéro de TVA qui n'est PLUS dérivé par cette formule (changement
  réglementaire pour raisons de vie privée) : un numéro NL réel de ce type
  sera signalé à tort comme structurellement invalide par ce substitut.
"""

import re

VERDICT_VALIDE = "valide"
VERDICT_INVALIDE = "invalide"


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _valider_fr(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{11}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    cle, siren = numero[:2], numero[2:]
    attendu = (12 + 3 * (int(siren) % 97)) % 97
    if int(cle) != attendu:
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_dk(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{8}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    poids = [2, 7, 6, 5, 4, 3, 2, 1]
    total = sum(int(c) * p for c, p in zip(numero, poids))
    if total % 11 != 0:
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_be(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{10}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    base, cle = int(numero[:8]), int(numero[8:])
    attendu = 97 - (base % 97)
    if cle != attendu:
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_lu(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{8}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    base, cle = int(numero[:6]), int(numero[6:])
    if cle != base % 89:
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_se(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{12}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    if numero[10:] != "01":
        return VERDICT_INVALIDE, "suffixe_incorrect"
    if not _luhn_ok(numero[:10]):
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_pt(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{9}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    poids = [9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(c) * p for c, p in zip(numero[:8], poids))
    reste = total % 11
    attendu = 0 if reste < 2 else 11 - reste
    if attendu != int(numero[8]):
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_nl(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{9}B\d{2}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    base = numero[:9]
    poids = [9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(c) * p for c, p in zip(base[:8], poids)) - int(base[8])
    if total % 11 != 0:
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_it(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{11}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    if not _luhn_ok(numero):
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_pl(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{10}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    poids = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    total = sum(int(c) * p for c, p in zip(numero[:9], poids))
    if total % 11 != int(numero[9]):
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


def _valider_fi(numero: str) -> tuple[str, str]:
    if not re.fullmatch(r"\d{8}", numero):
        return VERDICT_INVALIDE, "format_incorrect"
    poids = [7, 9, 10, 5, 8, 4, 2]
    total = sum(int(c) * p for c, p in zip(numero[:7], poids))
    reste = total % 11
    if reste == 1:
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    attendu = 0 if reste == 0 else 11 - reste
    if attendu != int(numero[7]):
        return VERDICT_INVALIDE, "cle_de_controle_incorrecte"
    return VERDICT_VALIDE, "ok"


_VALIDATEURS = {
    "FR": _valider_fr,
    "DK": _valider_dk,
    "BE": _valider_be,
    "LU": _valider_lu,
    "SE": _valider_se,
    "PT": _valider_pt,
    "NL": _valider_nl,
    "IT": _valider_it,
    "PL": _valider_pl,
    "FI": _valider_fi,
}


def valider(pays: str, numero_normalise: str) -> tuple[str, str]:
    """Point d'entree unique. `pays` doit etre un des 10 codes couverts."""
    validateur = _VALIDATEURS.get(pays)
    if validateur is None:
        raise KeyError(f"pays non couvert par le substitut : {pays}")
    return validateur(numero_normalise)
