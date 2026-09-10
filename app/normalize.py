"""Normalisation des numéros de TVA bruts.

Les constats ci-dessous viennent d'un sondage rapide du fichier (voir PLAN.md §2),
pas d'un profilage exhaustif — à confirmer/compléter lors de l'exploration réelle
(exploration/explore_referentiel.py) avant de considérer cette liste comme définitive.
"""

import re

import pandas as pd

# Les 10 pays couverts par le module de validation structurelle fourni.
# Confirmé par comptage sur pays_declare (chacun entre ~900 et ~975 occurrences).
# À ajuster si l'exploration complète en révèle d'autres.
PAYS_COUVERTS = {"FR", "DK", "BE", "LU", "SE", "PT", "NL", "IT", "PL", "FI"}

# Valeurs vues (ou attendues) comme sentinelles de "vide" plutôt que comme un vrai numéro.
_SENTINELLES_VIDES = {"", "-", "--", "N/A", "NA", "NC", "INCONNU", "?", "NONE", "NULL"}

_CARACTERES_A_RETIRER = re.compile(r"[\s.\-_/]")


def is_blank(raw) -> bool:
    if raw is None:
        return True
    if pd.isna(raw):
        return True
    cleaned = str(raw).strip().upper()
    return cleaned in _SENTINELLES_VIDES


def strip_noise(raw: str) -> str:
    """Retire espaces et séparateurs parasites (., -, _, /), met en majuscules."""
    return _CARACTERES_A_RETIRER.sub("", raw).upper()


def normalize_pays(pays_declare) -> str | None:
    if is_blank(pays_declare):
        return None
    return str(pays_declare).strip().upper()


def split_country_prefix(pays: str, cleaned_number: str) -> tuple[bool, str]:
    """Si le numéro nettoyé commence par le préfixe pays attendu, le retire.

    Retourne (prefixe_present, numero_local).
    """
    if pays and cleaned_number.startswith(pays):
        return True, cleaned_number[len(pays):]
    return False, cleaned_number


def normalize_numero(pays_declare: str | None, numero_brut: str | None) -> str | None:
    """Renvoie le numéro local normalisé (sans préfixe pays, sans bruit), ou None si vide."""
    if is_blank(numero_brut):
        return None
    pays = normalize_pays(pays_declare) or ""
    cleaned = strip_noise(numero_brut.strip())
    _, local = split_country_prefix(pays, cleaned)
    return local or None


def pays_est_couvert(pays_declare: str | None) -> bool:
    pays = normalize_pays(pays_declare)
    return pays in PAYS_COUVERTS
