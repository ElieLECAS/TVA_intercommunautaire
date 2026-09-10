"""Détection des doublons.

Définition retenue (PLAN.md §6) : deux lignes sont doublons l'une de l'autre
si elles partagent le même (pays_declare, numero_normalise) une fois normalisé
— indépendamment de la source ou de la raison sociale saisie. On garde la
ligne la plus récente (date_saisie) comme référence ; les autres sont
conservées en base (pas supprimées) mais flaggées is_duplicate=True avec un
pointeur vers la ligne conservée, pour que le rapport de réconciliation
puisse les compter et les justifier.
"""

import pandas as pd


def flag_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_duplicate"] = False
    df["duplicate_of_id"] = pd.array([pd.NA] * len(df), dtype="Int64")

    groupable = df[df["numero_normalise"].notna()]
    for (_, _), group in groupable.groupby(["pays_declare", "numero_normalise"]):
        if len(group) <= 1:
            continue
        ordered = group.sort_values("date_saisie", ascending=False)
        keeper_id = ordered.iloc[0]["id"]
        dup_ids = ordered.iloc[1:]["id"]
        df.loc[df["id"].isin(dup_ids), "is_duplicate"] = True
        df.loc[df["id"].isin(dup_ids), "duplicate_of_id"] = keeper_id

    return df
