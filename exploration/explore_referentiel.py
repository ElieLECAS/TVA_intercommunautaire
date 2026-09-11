#!/usr/bin/env python
"""Exploration manuelle du référentiel brut (Phase 1 du brief).

Jetable — répond aux questions posées explicitement par le brief avant
d'écrire du code de production : combien de pays distincts, combien de
formats différents par pays, quelle proportion de bruit, combien de formes
de "vide".
"""

import glob
import re

import pandas as pd

CSV_PATH = glob.glob("data/numeros-tva-*.csv")[0]


def main() -> None:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"Lignes : {len(df)}")

    print("\n--- pays_declare (brut) ---")
    counts = df["pays_declare"].value_counts(dropna=False)
    print(counts.to_string())
    print(f"Nombre de codes pays distincts : {counts.shape[0]}")

    print("\n--- Formes de 'vide' pour numero_tva (enumeration precise, pas un seuil de longueur) ---")
    nb_nan = df["numero_tva"].isna().sum()
    trimmed = df["numero_tva"].astype(str).str.strip()
    nb_espaces_seuls = ((~df["numero_tva"].isna()) & (trimmed == "")).sum()
    nb_tiret = ((~df["numero_tva"].isna()) & (trimmed == "-")).sum()
    print(f"Cellule vraiment vide (NaN, rien saisi)     : {nb_nan}")
    print(f"Espaces/blancs seulement (quelque chose saisi) : {nb_espaces_seuls}")
    print(f"Placeholder '-'                                : {nb_tiret}")
    print(f"Total formes de vide identifiees               : {nb_nan + nb_espaces_seuls + nb_tiret}")
    print("-> 3 formes distinctes de 'vide', pas une seule : a traiter comme un motif commun (numero_absent)")
    print("   mais bon a savoir que ce ne sont pas 3 bugs de saisie identiques.")

    print("\n--- Formats distincts par pays (signature : chiffre->9, lettre->A, separateurs gardes) ---")
    def forme(v):
        if pd.isna(v):
            return "<VIDE>"
        s = str(v).strip()
        if s in ("", "-"):
            return "<VIDE>"
        return "".join("9" if c.isdigit() else "A" if c.isalpha() else c for c in s)

    df["_forme"] = df["numero_tva"].apply(forme)
    formats_par_pays = df.groupby("pays_declare")["_forme"].nunique().sort_values(ascending=False)
    print(formats_par_pays.to_string())
    print(
        "-> chaque pays couvert a entre 17 et 23 formes brutes distinctes : prefixe pays "
        "present ou non, separateur absent/point/tiret/espace group, longueur qui varie "
        "de +-1 chiffre, et occasionnellement une lettre parasite en position inattendue."
    )

    print("\n--- Caracteres hors alphanumerique dans numero_tva ---")
    def has_noise(v) -> bool:
        if pd.isna(v):
            return False
        return bool(re.search(r"[^A-Za-z0-9]", str(v).strip()))

    noise_mask = df["numero_tva"].map(has_noise)
    print(f"{noise_mask.sum()} / {len(df)} lignes ({noise_mask.mean():.1%}) portent un caractere non alphanumerique")

    noise_examples = df.loc[noise_mask, "numero_tva"].head(10).tolist()
    print("Exemples :", noise_examples)

    print("\n--- Longueur du numero_tva brut (trim), par pays_declare ---")
    lengths = df["numero_tva"].apply(lambda v: len(str(v).strip()) if pd.notna(v) else 0)
    df["_longueur_brute"] = lengths
    print(df.groupby("pays_declare")["_longueur_brute"].agg(["min", "max", "nunique"]).to_string())

    print("\n--- Doublons potentiels (meme raison_sociale + meme numero_tva brut trimme/upper) ---")
    key = (
        df["raison_sociale"].astype(str).str.strip().str.upper()
        + "|"
        + df["numero_tva"].astype(str).str.strip().str.upper()
    )
    dup_count = key.duplicated(keep=False).sum()
    print(f"{dup_count} lignes partagent (raison_sociale, numero_tva brut) avec au moins une autre ligne")


if __name__ == "__main__":
    main()
