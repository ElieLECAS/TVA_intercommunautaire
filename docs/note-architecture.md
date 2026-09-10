# Note d'architecture

## Réduction du nombre d'appels VIES

Sur les 10 000 lignes du référentiel, seules **6 161 (61,6 %)** sont des candidates réelles à un appel VIES — soit **3 839 appels évités (38,4 %)**, avant toute vérification en ligne :

| Motif d'exclusion avant VIES | Lignes |
|---|---|
| Structurellement invalide (format ou clé de contrôle) | 3 015 |
| Pays hors des 10 couverts (indéterminé d'emblée) | 519 |
| Doublon d'une ligne déjà candidate (même pays + numéro normalisé) | 305 |
| **Total évité** | **3 839** |

La mesure de latence VIES (`scripts/measure_vies_latency.py`) donne un aller-retour de l'ordre de 40 à 150 ms hors premier appel à froid — sur 10 000 appels naïfs, l'ordre de grandeur se compte en dizaines de minutes rien qu'en latence réseau, sans compter la temporisation nécessaire pour ne pas se faire rate-limiter (observé en direct : `MS_MAX_CONCURRENT_REQ`). Réduire le volume de 38 % avant d'y toucher n'est donc pas cosmétique.

## Durée de validité d'un verdict (TTL)

**90 jours par défaut** (`VIES_VERDICT_TTL_DAYS`, `.env`). Au-delà, un verdict "connu" n'est plus servi tel quel : l'API retente VIES avant de répondre (`app/verification_service.py`). 90 jours est un choix par défaut aligné sur un rythme de facturation trimestriel — à ajuster selon le rythme réel de Meridian ; c'est un paramètre de configuration, pas une constante codée en dur.

Exception volontaire : un verdict **indéterminé** n'est **jamais** servi depuis le cache, quel que soit son âge. Ce n'est pas un fait établi sur le numéro, juste une tentative qui n'a rien donné (VIES indisponible, service saturé) — le laisser bloquer 90 jours de retries serait revivre l'erreur du contrôle fiscal de mars sous une autre forme. Chaque appel à l'API sur un numéro resté indéterminé retente VIES.

## Traitement des indéterminés

Un numéro est indéterminé dans deux cas distincts, jamais confondus avec "invalide" :
1. **En amont de VIES** : le pays déclaré n'est pas un des 10 couverts par la validation structurelle (`GB`, `UK`, `ZZ`, `QQ`, `XX` dans ce jeu — 519 lignes, 5,2 %). On ne sait pas juger le format, donc on ne juge pas.
2. **Au niveau de VIES** : le service ne répond pas ou ne peut pas trancher (`userError` différent de `VALID`, hors code `INVALID` qui lui signale un rejet de format déterministe — cf. journal-de-bord.md). Confirmé en conditions réelles avec `MS_MAX_CONCURRENT_REQ`.

Dans les deux cas, le verdict stocké est `indetermine`, jamais un `invalide` par défaut. L'API expose toujours l'origine de sa réponse (`structurel`, `frais_vies`, `connu_en_cache`, `connu_en_cache_perime`, `aucune_donnee`) : un appelant sait donc systématiquement s'il tient un fait établi ou une absence de réponse, et depuis quand.

## Le module de validation structurelle

Le module annoncé par le brief n'existe pas (confirmé par le formateur). `app/structural_module_substitut.py` le remplace par des algorithmes de clé de contrôle publiquement documentés — vérifié contre une donnée réelle uniquement pour la France (numéro d'exemple du brief, confirmé par VIES comme celui de SA DANONE). Deux bugs de format (BE, PT) ont été trouvés et corrigés en confrontant le substitut à de vraies réponses VIES ; les 7 autres pays restent des formules standard non re-vérifiées individuellement — limite assumée, et surveillable : un code `INVALID` de VIES sur une ligne que le substitut juge valide est le signal qu'un cas nous échappe encore.
