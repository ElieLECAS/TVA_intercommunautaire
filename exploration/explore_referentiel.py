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

    print("\n--- Formes de 'vide' pour numero_tva (valeurs courtes/suspectes) ---")
    as_str = df["numero_tva"].apply(lambda v: "<NaN>" if pd.isna(v) else str(v).strip())
    empty_forms = as_str[as_str.str.len() <= 2].value_counts()
    print(empty_forms.to_string() if not empty_forms.empty else "(aucune trouvee sous ce seuil)")

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
