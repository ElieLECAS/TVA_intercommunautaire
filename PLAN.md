# Plan de projet — Validation du référentiel de TVA intracommunautaire

> Document de travail, pas un livrable noté. Sert de feuille de route sur les 2 jours et de brouillon pour la note d'architecture / le journal de bord finaux.

## 0. État des lieux : ce qu'on a, ce qu'il manque

**Présent dans `data/`** :
- `numeros-tva-*.csv` et `.xlsx` — mêmes données, 10 000 lignes + en-tête.
- Colonnes : `id, raison_sociale, pays_declare, numero_tva, date_saisie, source_saisie`.

**Absent du dossier projet, à récupérer avant de coder pour de vrai** :
- ~~`docker-compose.yml`~~ — fait : `docker-compose.yml` à la racine, Postgres seul (image `postgres:16`), port hôte 5433 (5432 était déjà pris par un autre conteneur local, `bouquineo-db` — non touché).
- **Le module de validation structurelle** — toujours absent. Le brief dit explicitement qu'il est fourni, mais il n'apparaît pas dans la liste de ressources donnée (seuls csv/xlsx/docker-compose y figurent). Point d'intégration prêt dans [app/structural_validation.py](app/structural_validation.py) : tant qu'il n'est pas branché, toute ligne d'un pays couvert reçoit `indetermine`/`module_non_branche` plutôt qu'un faux verdict. **Toujours à récupérer sur la page Simplonline du brief.**

**Outillage** : gestion Python migrée sur `uv` (`pyproject.toml` + `uv.lock`, commande `uv sync` / `uv run ...`) plutôt que venv+pip.

## 1. Ce que le brief demande vraiment

- La question centrale a **trois** réponses, pas deux : valide / invalide / **indéterminé**. Le troisième terme est le sujet, pas un cas résiduel qu'on écarte.
- Le module fourni ne garantit qu'une **validité structurelle** (format + clé de contrôle). Ça ne dit rien sur : l'immatriculation réelle du numéro, son caractère actif à la date de facturation, ni la correspondance avec la raison sociale. Un numéro peut être structurellement parfait et ne correspondre à personne — seul VIES peut trancher ça, et VIES lui-même ne tranche pas toujours (États membres indisponibles, champs absents selon le pays).
- **Ordre imposé, et noté en tant que tel** : normaliser → dédupliquer → filtrer sur la structure → interroger VIES. Chaque étape doit réduire ce que la suivante traite, et la réduction doit être chiffrée — c'est un livrable explicite, pas un détail d'implémentation.
- Une indisponibilité VIES **ne doit jamais** devenir un "invalide" en base. C'est littéralement l'erreur qui a coûté cher au contrôle fiscal de mars (des numéros non tranchés traités comme s'ils étaient acquis dans un sens ou l'autre).
- Un verdict a une durée de vie : il faut décider et justifier un TTL, pas juste horodater.
- Tout doit être rejouable : chargement idempotent (aucun doublon au rechargement), rapport reproductible par une commande, stack lancée par une commande, README suivi à la lettre depuis un clone vierge.

## 2. Premier coup d'œil sur les données — confirmé par `exploration/explore_referentiel.py`

- **10 000 lignes**, 15 codes `pays_declare` distincts. 10 couverts par le module (`FR, DK, BE, LU, SE, PT, NL, IT, PL, FI`, ~900-975 occurrences chacun) + **5 hors liste** : `ZZ` (115), `QQ` (109), `GB` (104), `UK` (104), `XX` (87) — **519 lignes (5,2 %)** qu'aucune règle du module ne couvre. Traitées comme `indetermine`/`pays_non_couvert`, jamais comme un verdict du module.
- **114 valeurs vides sous 2 formes distinctes** : chaîne vide (59), `"-"` (55).
- **13,4 % des lignes (1335)** portent un caractère non alphanumérique dans `numero_tva` (espaces, points, tirets — ex. `SE.751298146001`, `PL 7963 612947`).
- **Doublons** : 651 lignes partagent (raison_sociale, numero_tva brut) à l'identique ; après normalisation complète (même pays + numéro nettoyé), le chiffre retombe à **438** — les deux définitions ne donnent pas le même nombre, exactement le genre d'écart que le brief demande de justifier (cf. journal-de-bord.md).

Le pipeline (`scripts/load_referentiel.py`) tourne : 10 000 lignes chargées, idempotence vérifiée (rechargement = toujours 10 000 lignes, 438 doublons, aucune duplication). Le verdict structurel reste `indetermine` partout tant que le vrai module n'est pas branché — c'est attendu, pas un bug.

## 3. Architecture proposée

**Stack** (le brief impose Python/FastAPI/PostgreSQL/Docker/Git — le reste est un choix à justifier) :
- Accès DB : `psycopg` (v3) ou SQLAlchemy Core + SQL brut versionné (`db/schema.sql`, `CREATE TABLE IF NOT EXISTS`, upsert `ON CONFLICT`). Pas d'Alembic — sur 2 jours, une migration framework coûte plus qu'elle ne rapporte.
- Appels VIES : `httpx` (timeout explicite, gestion d'erreurs réseau propre).
- Exploration / normalisation : `pandas` pour aller vite en phase 1 (10 000 lignes, pas un problème de perf).
- API : FastAPI + Pydantic (modèles de réponse explicites → OpenAPI généré gratuitement).
- Logs : module `logging` standard, un logger dédié aux appels VIES (utile pour la preuve de reprise en soutenance).

**Modèle de données (esquisse conceptuelle, le DDL viendra à l'implémentation)** :

```
vat_numbers                              vies_verifications
─────────────                            ──────────────────
id                                        id
raison_sociale                           vat_number_id (FK)
pays_declare        ← brut reçu          pays_interroge, numero_interroge
numero_brut          ← brut reçu          verdict            (valide/invalide/indetermine)
numero_normalise     ← déduit             motif / detail
source_saisie, date_saisie ← brut reçu    reponse_brute (jsonb)  ← tout ce que VIES a renvoyé
verdict_structurel   ← déduit             checked_at
motif_structurel     ← déduit             latency_ms
is_duplicate, duplicate_of_id ← déduit
UNIQUE(pays_declare, numero_normalise)    → clé d'upsert, garantit qu'un rechargement ne duplique rien
```

Séparer les deux tables (plutôt qu'une seule colonne "dernier statut VIES") permet de garder l'historique complet des vérifications — nécessaire pour répondre à "depuis quand ce verdict tient" et pour que la reprise après interruption soit une simple requête, pas un mécanisme à part.

**Idée clé pour la campagne VIES** : la requête "quels numéros interroger dans ce batch" peut s'écrire comme :
```sql
SELECT ... FROM vat_numbers
WHERE verdict_structurel = 'valide'
  AND id NOT IN (
    SELECT vat_number_id FROM vies_verifications
    WHERE checked_at > NOW() - INTERVAL '<TTL>'
  )
LIMIT <taille_echantillon>
```
Cette seule requête donne en même temps : le mode échantillon (LIMIT), la reprise après interruption (les lignes déjà traitées récemment sortent naturellement du lot), et l'application du TTL de fraîcheur. Pas besoin d'un fichier de checkpoint séparé — l'état est dans la base.

## 4. Plan détaillé — Jour 1 (Cadrage, réduction, chargement)

1. **Exploration manuelle, sans code de prod** — répondre aux questions du brief : nb de pays distincts, nb de formats par pays, proportion de bruit, formes du "vide". (Notebook ou script jetable, dans un dossier genre `exploration/`, pas dans le pipeline final.)
2. **Squelette du repo** : `git init`, structure de dossiers, venv, `requirements.txt`, `docker-compose up` pour Postgres, `.env`, premier commit.
3. **Lecture du module fourni** : cataloguer chaque couple (verdict, motif) qu'il peut renvoyer. Décider, pour chaque motif, s'il doit compter comme invalide, comme "à normaliser puis retenter", ou comme indéterminé — et pourquoi.
4. **Normalisation** : trim, retrait des séparateurs parasites, casse, détection des valeurs vides/sentinelles (`"-"` etc.), et décision explicite pour les codes pays hors liste (`GB/UK/ZZ/QQ/XX` ou équivalents une fois votre propre inventaire fait).
5. **Passage du module structurel** sur les 10 000 lignes normalisées → verdict + motif par ligne.
6. **Déduplication** : définir ce qu'est un doublon (numéro normalisé identique ? même entreprise + numéro ? peu importe la source/date ?), justifier, implémenter, chiffrer combien sont retirés.
7. **Mesure VIES** : chronométrer une poignée d'appels réels, extrapoler le temps total sur le volume restant, en tirer une stratégie de réduction chiffrée (c'est un livrable : "combien d'appels évités").
8. **Schéma PostgreSQL versionné** (`db/schema.sql`) + **script de chargement idempotent** (upsert sur la clé naturelle).
9. **Requête de répartition par motif** — script ou simple fichier `.sql`.
10. Commits réguliers tout au long de la journée (pas un seul commit géant le soir).

**Checkpoint fin J1** (repris du brief, à valider avant de passer à J2) : une commande unique charge les 10 000 lignes ; la base porte le verdict structurel de chacune ; une requête donne la répartition par motif ; vous savez dire combien d'appels VIES ont été évités et comment.

## 5. Plan détaillé — Jour 2 (Vérification en ligne et API)

1. **Test manuel VIES** sur 3 numéros (un bon, un à clé fausse, un inventé) — script jetable, lire **toute** la réponse, pas juste le booléen valide/invalide.
2. **Test en volume** (quelques dizaines d'appels), log complet, confrontation systématique à ce qu'on attendait. Toute réponse surprenante (champ absent, état membre indisponible, comportement différent selon le pays) est à noter, pas à contourner.
3. **Client VIES** : timeout, temporisation entre appels, gestion explicite des 3 états — **une indisponibilité de service n'est jamais un "invalide"**.
4. **Campagne** : mode échantillon paramétrable (`--sample 200` par défaut), la requête décrite en section 3 donne la reprise gratuitement.
5. **Décision de TTL** : à trancher et justifier (ex. aligné sur un cycle de facturation) — répond à "un numéro vérifié il y a six mois doit-il être revérifié ?".
6. **API FastAPI** : le contrat de réponse est le vrai sujet — verdict + origine (appel frais / valeur connue) + fraîcheur (date du dernier contrôle), y compris le cas "VIES injoignable ET rien en mémoire".
7. **OpenAPI** accessible (`/docs`, gratuit avec FastAPI si les modèles Pydantic sont soignés).
8. **Rapport de réconciliation** reproductible par une commande : valides / invalides / indéterminés / motifs / doublons.
9. **README, note d'architecture (1 page), journal de bord** — le journal se tient au fil des deux jours, pas reconstitué le soir du J2.
10. **Épreuve finale** : dossier supprimé, dépôt recloné, README suivi à la lettre.

**Checkpoint fin J2** : campagne en mode échantillon qui tourne ; chaque ligne a un verdict justifiable ; une relance ne refait pas les appels déjà faits ; l'API renvoie verdict + origine + fraîcheur ; le rapport se régénère par une commande.

## 6. Décisions à trancher (proposition par défaut, à valider ou changer)

| Décision | Proposition par défaut |
|---|---|
| Définition d'un doublon | Même `(pays_declare, numero_normalisé)` → doublon ; on garde la ligne la plus récente par `date_saisie`, les autres sont loguées, pas supprimées silencieusement |
| Codes pays hors liste (GB/UK/ZZ/QQ/XX...) | Motif dédié type `pays_non_couvert`, classé indéterminé dès la phase structurelle — jamais invalide par défaut |
| TTL d'un verdict VIES | 90 jours (à ajuster selon le rythme de facturation réel de Meridian) |
| Taille d'échantillon par défaut | 200, comme suggéré par le brief |
| Accès DB | SQL brut versionné + upsert, pas d'ORM/migration framework |

## 7. Pièges déjà identifiés à ce stade

- Confondre "VIES indisponible" et "invalide" — c'est l'erreur qui a motivé le brief.
- Confondre "structurellement valide" et "légalement valide" — le module ne garantit que le premier.
- GB apparaît dans le fichier mais **n'est pas un des dix pays** que le module couvre — traitement à définir, indépendant du verdict du module.
- La réduction du volume d'appels VIES doit être un nombre, pas une affirmation ("on a réduit" ne suffit pas, il faut le chiffre et la méthode).
- Un rechargement de la base ne doit produire aucun doublon — ça se vérifie en rejouant le chargement deux fois.
- Répartir les commits sur les deux jours est noté explicitement — ne pas tout committer le soir du J2.

## 8. État réel du J1 (mis à jour)

Fait : scaffold repo (`uv`, docker-compose Postgres sur le port 5433), schéma versionné, normalisation, dédoublonnage, pipeline de chargement idempotent (10 000 lignes, 438 doublons, vérifié rejouable), exploration chiffrée, mesure de latence VIES (7 appels, tous `MS_MAX_CONCURRENT_REQ` — voir [journal-de-bord.md](journal-de-bord.md), décision : toujours lire `userError` avant `isValid`), 8 commits.

**Reste bloquant pour clore le J1** : récupérer le vrai module de validation structurelle et le brancher dans [app/structural_validation.py](app/structural_validation.py) — sans lui, `verdict_structurel` reste `indetermine` partout, et la répartition par motif (item 9 du plan) ne veut rien dire de définitif.

Prochaine étape : le module, puis on tranche les décisions de la section 6 pour de vrai (elles sont pour l'instant des valeurs par défaut, pas encore validées par vous), puis J2.
