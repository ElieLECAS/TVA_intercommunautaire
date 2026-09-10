# Journal de bord

## 2026-09-10 — J1

- **Blocage** : le module de validation structurelle annoncé par le brief n'est pas dans les ressources fournies (seuls csv/xlsx/docker-compose y figurent). **Décision** : ne pas le réécrire soi-même (ça viderait l'exercice de son sens) ; créer un point d'intégration explicite (`app/structural_validation.py`) qui renvoie `indetermine` / `module_non_branche` pour tout pays couvert tant que le vrai module n'est pas branché — jamais un faux `invalide` ou `valide`. Le module reste à récupérer sur la plateforme du brief.
- **Exploration réelle** (`exploration/explore_referentiel.py`) sur les 10 000 lignes :
  - 15 codes `pays_declare` distincts, alors que le module n'en couvre que 10 (`FR, DK, BE, LU, SE, PT, NL, IT, PL, FI`). Les 5 autres (`ZZ` 115, `QQ` 109, `GB` 104, `UK` 104, `XX` 87 — 519 lignes, 5,2 %) ne sont structurellement évaluables par aucune règle connue.
  - 114 valeurs vides sous deux formes distinctes : chaîne vide (59) et `"-"` (55).
  - 13,4 % des lignes (1335) portent un caractère non alphanumérique dans `numero_tva` (espaces, points, tirets).
  - 651 lignes partagent (raison_sociale, numero_tva brut) avec au moins une autre ligne — à comparer au chiffre obtenu après normalisation (438, cf. plus bas) : deux définitions du doublon donnent deux chiffres différents, exactement ce que le brief demande de justifier.
- **Blocage** : `docker compose up` a échoué au premier essai — port 5432 déjà occupé par un autre conteneur local (`bouquineo-db`, sans rapport avec ce projet). **Résolution** : `POSTGRES_PORT=5433` dans `.env`, pas touché à l'autre conteneur.
- **Décision d'outillage** : gestion Python basculée sur `uv` (pyproject.toml + uv.lock) plutôt que venv+pip, à la demande explicite du besoin de reproductibilité stricte (`uv sync` réinstalle exactement les mêmes versions).
- **Pipeline de chargement** (`scripts/load_referentiel.py`) exécuté avec succès : 10 000 lignes, 438 doublons détectés (définition : même (pays_declare, numero_normalisé), on garde la ligne la plus récente par date_saisie). Rejoué une seconde fois : toujours 10 000 lignes en base, aucun doublon créé — idempotence vérifiée.
- **Mesure VIES** (`scripts/measure_vies_latency.py`) sur le numéro d'exemple FR du brief (27552032534) : **7 appels sur 7**, espacés de 0 à 8 secondes, renvoient tous HTTP 200 avec `isValid: false` ET `userError: "MS_MAX_CONCURRENT_REQ"`. Latence brute du round-trip HTTP : ~40-150 ms hors premier appel « à froid ».
  - **Constat central** : `isValid: false` ne veut ici pas dire « numéro invalide » — VIES nous dit qu'il n'a pas pu trancher (état membre saturé). Un client naïf qui ne lirait que `isValid` aurait classé ce numéro comme invalide à tort.
  - **Décision** : le client VIES (J2) devra toujours vérifier `userError` en premier ; tout `userError` non vide → verdict `indetermine`, quel que soit `isValid`. Ne jamais se fier à `isValid` seul.
  - **Point de vigilance pour la suite** : cette erreur est apparue de façon constante y compris après 8 s d'attente, ce qui suggère soit une vraie saturation du backend FR côté Commission, soit un effet de l'egress réseau partagé de cet environnement sandboxé (plusieurs sessions pourraient sortir par la même IP). À revérifier depuis un environnement normal avant de conclure définitivement sur la fréquence réelle de cet état.
