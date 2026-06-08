# Note de cadrage — Credit Process Intelligence

> Document généré par `make docs` à partir des exports du pipeline : les chiffres cités sont recalculés à chaque exécution.

## 1. Contexte

Une institution néerlandaise de crédit à la consommation a publié le journal d'événements de son processus de demande de prêt (BPI Challenge 2012). Chaque demande y laisse une trace datée : dépôt, pré-contrôle automatique, appels de complétion, offre, relances, validation, décision.

La mission simule une intervention de conseil : partir de ces traces réelles pour comprendre le processus tel qu'il se déroule, mesurer où se perdent le temps et la valeur, puis identifier, chiffrer et sécuriser les usages de l'IA qui en valent la peine.

Les rôles cités ci-dessous sont des rôles types : les données sont réelles et anonymisées, l'organisation interne de l'institution n'est pas connue.

## 2. Questions métier

| N° | Question | Livrable principal |
|---|---|---|
| Q1 | Quel est le parcours réel d'une demande ? | Carte des flux, variantes, conformité au chemin nominal |
| Q2 | Combien de temps, et où se perd-il ? | Délais par issue, attente contre travail, goulots |
| Q3 | Combien coûtent les allers-retours ? | Volumes, heures et délais des boucles de reprise |
| Q4 | Qui abandonne, quand, et pourquoi ? | Annulations par étape, délai et montant |
| Q5 | Peut-on prédire tôt le risque d'abandon ? | Modèle évalué hors période d'apprentissage, seuils d'acceptation |
| Q6 | Quelles opportunités IA, quel gain, quels risques ? | Business case, qualification AI Act et RGPD, feuille de route |

## 3. Périmètre

**Inclus** : le parcours d'une demande, du dépôt à l'issue (prêt activé, refus ou annulation), pour les 13 087 demandes déposées du 1er octobre 2011 au 29 février 2012.

**Exclus** :

- l'octroi lui-même et le score de solvabilité : aucune analyse ne cherche à prédire si un client doit obtenir un crédit ;
- la tarification, le recouvrement et la relation client après l'activation ;
- toute donnée personnelle autre que celles du journal public (montant demandé, horodatages, identifiants pseudonymisés).

## 4. Données

| Élément | Valeur |
|---|---|
| Source | van Dongen, B. (2012). BPI Challenge 2012. 4TU.ResearchData. |
| DOI | https://doi.org/10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f |
| Conditions d'utilisation | 4TU General Terms of Use (citation obligatoire) |
| Volumétrie | 13 087 demandes, 262 200 événements, 24 activités |
| Période | dépôts du 1er octobre 2011 au 29 février 2012, événements jusqu'au 14 mars 2012 |
| Attributs utiles | activité, cycle de vie (planifiée, démarrée, terminée), horodatage, ressource pseudonymisée, montant demandé |
| Source secondaire | BPI Challenge 2017 – Offer log, uniquement pour étalonner une hypothèse de marge |

Limites connues dès le cadrage : cinq mois d'observation (annualisation nécessaire), pas de motif d'annulation, pas de pièce justificative, pas d'attribut sociodémographique.

## 5. Démarche et livrables

| Étape | Livrable | Emplacement |
|---|---|---|
| Cadrage | Présente note | `docs/01-note-de-cadrage.md` |
| Données et qualité | Acquisition reproductible, contrôles de qualité | `src/cpi/data.py`, `src/cpi/quality.py` |
| Diagnostic | Analyse AS-IS chiffrée | `docs/02-analyse-as-is.md` |
| Modélisation | BPMN AS-IS et TO-BE | `docs/03-modelisation-bpmn.md`, `docs/bpmn/` |
| Besoins | User stories et critères d'acceptation | `docs/04-user-stories.md` |
| Valeur | Business case | `docs/05-business-case.md` |
| Conformité | Analyse AI Act et RGPD | `docs/06-conformite-ia-rgpd.md` |
| Recette | Plan de recette | `docs/07-plan-de-recette.md` |
| Adoption | Conduite du changement | `docs/08-conduite-du-changement.md` |
| Restitution | Rapport interactif | `site/` |

## 6. Parties prenantes (rôles types)

| Rôle | Attente | Implication |
|---|---|---|
| Direction des opérations crédit (commanditaire) | Délai, coût, conversion | Arbitre la feuille de route |
| Responsable du centre de contact | Charge des relances, qualité des appels | Valide les hypothèses de terrain |
| Responsable du back-office validation | File d'attente, dossiers incomplets | Co-conçoit la pré-analyse |
| Conformité et délégué à la protection des données | Qualification AI Act, RGPD, droit du crédit | Valide les garde-fous |
| Risques | Absence d'effet sur l'octroi | Revue du modèle |
| DSI et équipe data | Intégration, exploitation, supervision | Estime les coûts |

## 7. Hypothèses de travail et contraintes

- Le journal est représentatif du fonctionnement de l'institution sur la période ; la saisonnalité sur douze mois est inconnue.
- Les coûts (coût horaire, coûts de construction et de fonctionnement) ne figurent pas dans les données : ils sont posés comme hypothèses explicites, avec une fourchette, et testés en sensibilité.
- Aucun modèle ne doit toucher à la décision de crédit.
- Tout chiffre publié doit être recalculable par une commande (`make all`).

## 8. Critères de succès de la mission

- Chaque question Q1 à Q6 reçoit une réponse chiffrée, sourcée et reproductible.
- Les recommandations distinguent clairement ce qui est mesuré de ce qui est supposé.
- Chaque opportunité est qualifiée au regard de l'AI Act et du RGPD avant tout chiffrage final.
- Le commanditaire peut faire varier les hypothèses lui-même (simulateur du rapport).

## 9. Risques de la mission

| Risque | Effet | Parade |
|---|---|---|
| Qualité des données (horodatages simultanés, sessions non clôturées) | Délais et heures faussés | Contrôles de qualité, règles de nettoyage documentées et testées en sensibilité |
| Surinterprétation de corrélations | Gains surestimés | Rejeu contrefactuel prudent, part causale explicite, fourchettes |
| Fuite d'information dans le modèle | Performance illusoire | Découpage temporel strict, zone tampon, préfixes au point de décision |
| Glissement vers un usage d'octroi | Haut risque AI Act | Frontière d'usage écrite, qualification par la conformité |

## 10. Planning indicatif

| Semaine | Jalon |
|---|---|
| S1 | Cadrage validé, données acquises et contrôlées |
| S2 | Diagnostic AS-IS et carte du processus |
| S3 | Modèle prédictif et seuils d'acceptation |
| S4 | Business case, conformité, feuille de route |
| S5 | Restitution au comité de direction |
