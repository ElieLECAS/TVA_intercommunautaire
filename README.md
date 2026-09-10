# Validation du référentiel de TVA intracommunautaire

Meridian Distribution facture hors taxe ses clients européens sous condition que leur numéro de TVA soit réellement valide. Ce projet construit le service qui tranche — parmi les 10 000 numéros du référentiel client, lesquels sont valides, lesquels ne le sont pas, et lesquels n'ont pas pu être tranchés — et l'API que la facturation appellera avant chaque émission hors taxe.

## Technologies et justification

| Techno | Rôle | Pourquoi |
|---|---|---|
| Python 3.12 + [uv](https://docs.astral.sh/uv/) | pipeline, API | `uv` gère l'environnement et les dépendances (`pyproject.toml` + `uv.lock`) de façon reproductible — pas de venv/pip à gérer à la main |
| PostgreSQL (Docker) | référentiel + historique des vérifications | imposé par le brief ; `JSONB` pour garder la réponse VIES complète sans perdre d'information |
| psycopg 3 (SQL brut, pas d'ORM) | accès base | le besoin est majoritairement des agrégations/upserts, pas un graphe d'objets — du SQL versionné (`db/schema.sql`) est plus direct qu'une couche ORM sur 2 jours |
| httpx | client VIES | timeout explicite, API simple, base saine pour la temporisation |
| pandas | pipeline de chargement (J1) | 10 000 lignes : pas un problème de perf, et ça accélère nettement normalisation/dédoublonnage |
| FastAPI + Pydantic | API REST | documentation OpenAPI générée automatiquement, validation des réponses par les modèles |

## Lancement depuis zéro

Prérequis : Docker Desktop, [uv](https://docs.astral.sh/uv/getting-started/installation/), Git.

```bash
git clone <url-du-repo>
cd TVA_intercommunautaire
cp .env.example .env
# si le port 5432 est deja pris sur votre machine, changez POSTGRES_PORT
# dans .env (et DATABASE_URL en consequence) avant l'etape suivante.

uv run scripts/up.py
```

Cette seule commande démarre Postgres (Docker), attend qu'il réponde, applique le schéma et charge les 10 000 lignes (idempotent : rejouable sans dupliquer). `uv` installe les dépendances Python automatiquement au premier appel.

Ensuite, au choix :

```bash
# Campagne de verification VIES (mode echantillon, ici 200 numeros)
uv run scripts/run_vies_campaign.py --sample 200
# Interrompre (Ctrl+C) puis relancer la meme commande : rien n'est refait.

# Rapport de reconciliation (valides / invalides / indetermines / motifs / doublons)
uv run scripts/generate_report.py

# API REST
uv run uvicorn api.main:app --reload
# -> http://127.0.0.1:8000/docs (documentation OpenAPI)
```

Tests manuels utiles pour la démonstration :

```bash
uv run scripts/measure_vies_latency.py     # temps de reponse VIES, extrapolation sur le volume
uv run scripts/test_vies_manuel.py         # 3 numeros : bon, cle fausse, invente - reponse complete
```

## Structure du repo

```
data/                       jeu de donnees fourni (csv + xlsx, 10 000 lignes)
db/schema.sql                schema versionne (brut / normalise / verdict / historique VIES)
app/
  normalize.py                normalisation (bruit de saisie, valeurs vides, codes pays)
  dedupe.py                    detection des doublons
  structural_module_substitut.py  cle de controle par pays (voir "Le module manquant" ci-dessous)
  structural_validation.py     point d'integration structurel
  loader.py                     pipeline complet : lecture -> normalisation -> dedup -> verdict -> upsert
  vies_client.py                 client VIES (3 etats, jamais d'indisponibilite lue comme invalide)
  campaign.py                     campagne : selection du lot, echantillon, reprise, TTL
  verification_service.py          logique de l'API : verdict + origine + fraicheur
  report.py                         rapport de reconciliation
  db.py, config.py                   connexion, configuration (.env)
scripts/                        commandes (up, chargement, campagne, rapport, tests manuels VIES)
api/main.py                     API FastAPI
exploration/                    scripts d'exploration jetables (phase 1, non-production)
PLAN.md                         feuille de route de travail (pas un livrable note)
journal-de-bord.md              blocages, tentatives, decisions - au fil des deux jours
docs/note-architecture.md        note d'architecture (1 page)
```

## Le module manquant

Le brief annonce un module de validation structurelle fourni pour les 10 pays du jeu. **Il n'existe pas** : confirmé directement par le formateur (Guillaume Soulat). `app/structural_module_substitut.py` le remplace, à partir d'algorithmes de clé de contrôle publiquement documentés (mod 97 pour FR/BE, mod 89 pour LU, mod 11 pondéré pour PT/NL/PL/FI/DK, Luhn pour IT/SE). Détails, tests et limites connues : voir [journal-de-bord.md](journal-de-bord.md) et [docs/note-architecture.md](docs/note-architecture.md).

## Auteur

Elie Lecas
