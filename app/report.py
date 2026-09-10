"""Rapport de réconciliation.

Le verdict final d'un numéro combine deux couches :
- si le verdict structurel n'est pas 'valide', il fait foi (invalide ou
  indeterminé, avec son motif) — inutile d'aller voir VIES ;
- sinon, la dernière vérification VIES fait foi ; s'il n'y en a aucune
  encore, le numéro reste 'indetermine' / 'vies_jamais_interroge'.

Les doublons sont comptés à part : ils héritent du verdict de la ligne
conservée (pas de double-appel VIES pour une même entreprise déclarée deux
fois), donc exclus de la répartition principale pour ne pas gonfler les
chiffres, mais leur nombre est un livrable en soi.
"""

_VERDICT_FINAL_SQL = """
WITH derniere_verif AS (
    SELECT DISTINCT ON (vat_number_id)
        vat_number_id, verdict AS verdict_vies, detail AS detail_vies, checked_at
    FROM vies_verifications
    ORDER BY vat_number_id, checked_at DESC
)
SELECT
    vn.id,
    vn.is_duplicate,
    CASE
        WHEN vn.verdict_structurel <> 'valide' THEN vn.verdict_structurel
        WHEN dv.verdict_vies IS NOT NULL THEN dv.verdict_vies
        ELSE 'indetermine'
    END AS verdict_final,
    CASE
        WHEN vn.verdict_structurel <> 'valide' THEN vn.motif_structurel
        WHEN dv.verdict_vies IS NOT NULL THEN dv.detail_vies
        ELSE 'vies_jamais_interroge'
    END AS motif_final,
    dv.checked_at
FROM vat_numbers vn
LEFT JOIN derniere_verif dv ON dv.vat_number_id = vn.id
"""


def generer_rapport(conn) -> str:
    with conn.cursor() as cur:
        cur.execute(_VERDICT_FINAL_SQL)
        lignes = cur.fetchall()

    total = len(lignes)
    doublons = [l for l in lignes if l[1]]
    principales = [l for l in lignes if not l[1]]

    repartition: dict[str, int] = {}
    motifs: dict[tuple, int] = {}
    verifiees_vies = 0
    for _id, _dup, verdict, motif, checked_at in principales:
        repartition[verdict] = repartition.get(verdict, 0) + 1
        motifs[(verdict, motif)] = motifs.get((verdict, motif), 0) + 1
        if checked_at is not None:
            verifiees_vies += 1

    lignes_md = []
    lignes_md.append("# Rapport de réconciliation\n")
    lignes_md.append("Généré automatiquement — `uv run scripts/generate_report.py`\n")
    lignes_md.append(f"\nTotal référentiel : **{total}** lignes (hors doublons : {len(principales)}, doublons : {len(doublons)})\n")

    lignes_md.append("\n## Répartition finale (hors doublons)\n")
    lignes_md.append("| Verdict | Nombre | % |\n|---|---|---|\n")
    for verdict in ("valide", "invalide", "indetermine"):
        n = repartition.get(verdict, 0)
        pct = (n / len(principales) * 100) if principales else 0
        lignes_md.append(f"| {verdict} | {n} | {pct:.1f}% |\n")

    lignes_md.append(f"\nDont vérifiées au moins une fois par VIES : **{verifiees_vies}** / {len(principales)}\n")

    lignes_md.append("\n## Motifs\n")
    lignes_md.append("| Verdict | Motif | Nombre |\n|---|---|---|\n")
    for (verdict, motif), n in sorted(motifs.items(), key=lambda kv: (-kv[1])):
        lignes_md.append(f"| {verdict} | {motif} | {n} |\n")

    lignes_md.append(f"\n## Doublons\n\n**{len(doublons)}** lignes flaggées doublon "
                      f"(même (pays, numéro normalisé), la plus récente par date_saisie est conservée "
                      f"comme référence — cf. app/dedupe.py).\n")

    return "".join(lignes_md)
