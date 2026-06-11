# Business case — trois opportunités IA

> Document généré par `make docs`. Les valeurs de référence sont mesurées dans le journal ; les hypothèses viennent de [`config/hypotheses.yaml`](../config/hypotheses.yaml) et sont modifiables dans le simulateur du rapport.

## Résumé

| Opportunité | Gain annuel (médiane) | VAN 3 ans P10 / P50 / P90 | P(VAN > 0) | Retour (central) | Recommandation |
|---|---|---|---|---|---|
| Contrôle automatique de complétude à la soumission | 105 k€ | −4 k€ / **48 k€** / 108 k€ | 88 % | 24 mois | Lancer |
| Priorisation des relances d'offres par score d'abandon | 48 k€ | −45 k€ / **1 k€** / 68 k€ | 51 % | 36 mois | Pilote A/B d'abord |
| Pré-analyse assistée des dossiers à valider | 53 k€ | −132 k€ / **−89 k€** / −45 k€ | 0 % | au-delà de 36 mois | Différer |

Le contrôle de complétude est la seule opportunité rentable dans la grande majorité des scénarios. La priorisation des relances dépend d'un taux de récupération inconnu : elle se teste par un pilote peu coûteux, sans score d'IA à ce stade. La pré-analyse assistée ne se justifie pas à ce volume par la seule productivité.

## Méthode

1. **Valeurs de référence mesurées** : volumes, heures et taux sont calculés sur les 13 087 demandes, puis annualisés (facteur 2,40 : 365 jours rapportés aux 152 jours de dépôts observés).
2. **Rejeu contrefactuel** : pour le contrôle de complétude, chaque boucle « dossier incomplet » réelle est évitée ou non (tirage de Bernoulli) ; on retire ses heures réelles et, pour un prêt approuvé, son délai réel. Les autres leviers sont appliqués en espérance.
3. **Monte Carlo** : 5 000 tirages ; chaque hypothèse suit une loi triangulaire (minimum, mode, maximum). Graine fixe : résultats reproductibles.
4. **Flux de trésorerie mensuels sur 36 mois** : coût de construction étalé sur la durée du projet, puis bénéfices en montée en charge linéaire sur 6 mois, coûts de fonctionnement dès la mise en service. VAN au taux d'actualisation retenu ; retour sur investissement : premier mois où le cumul redevient positif.
5. **Valorisation** : heures libérées × coût horaire complet (capacité redéployable, pas forcément une économie de trésorerie) ; prêts supplémentaires × montant moyen approuvé × marge nette actualisée.

Les formules déterministes sont reproduites à l'identique dans le simulateur du rapport ; un test croisé compare les deux implémentations sur 15 scénarios.

## Valeurs de référence mesurées

| Mesure (sur la période observée) | Valeur |
|---|---|
| Dossiers passés par une boucle « dossier incomplet » | 1 647 |
| Heures de ces boucles (appels et re-validations) | 1 536 h |
| Heures d'appels de complétion | 2 164 h |
| Heures de validation | 2 126 h |
| Écart de taux d'annulation des dossiers validés avec et sans boucle | 7,6 % |
| Taux d'approbation des offres retournées | 71,1 % |
| Montant moyen des prêts approuvés | 15 713 € |
| Annulations après l'envoi d'une offre | 1 640 |
| Dossiers ayant reçu une offre | 5 015 |
| Abandons couverts en appelant 20 % des dossiers (modèle, période de test) | 23,2 % |
| Durée médiane d'un appel de relance | 1,7 min |
| Délai médian des prêts approuvés | 14,4 j |

## Hypothèses

| Hypothèse | Min | Mode | Max | Justification |
|---|---|---|---|---|
| Coût horaire complet d'un conseiller back-office | 38 €/h | 45 €/h | 55 €/h | Salaire brut annuel d'environ 35 k€, charges patronales d'environ 45 % et frais de structure (encadrement, poste de travail, locaux) d'environ 30 %, rapportés à 1 607 h. Ordre de grandeur, à remplacer par le coût réel de l'établissement. |
| Taux d'actualisation annuel | 8 % | 10 % | 12 % | Taux de rentabilité exigé pour un projet de transformation dans une banque de détail (coût des fonds propres majoré d'une prime de risque projet). |
| Correction du volume annualisé | 0,85 | 1,00 | 1,10 | Le journal couvre 5 mois (octobre à février) ; la saisonnalité sur 12 mois est inconnue. On encadre le volume annualisé de −15 % à +10 % (prudence à la hausse). |
| Taux d'adoption en régime de croisière | 75 % | 90 % | 100 % | Part des dossiers éligibles réellement traités avec la nouvelle solution après la montée en charge (exceptions, refus d'usage, cas non couverts). |
| Marge nette actualisée par euro prêté | 3 % | 5 % | 8 % | Les offres retenues (attribut « Selected ») du BPI Challenge 2017 (21 768 sur 42 995, même établissement, 2016) impliquent des intérêts bruts médians d'environ 18 % du montant sur la durée du prêt (taux annuel implicite médian proche de 5 %, durée médiane de 80 mois). Après coût de refinancement, coût du risque et frais de gestion, on retient environ un quart à un tiers des intérêts bruts (calcul : make pipeline). |
| Complétude à la soumission — Coût de construction | 80 k€ | 110 k€ | 160 k€ | Lecture et classement des pièces (OCR et IA documentaire), règles de complétude, intégration au parcours de dépôt, recette ; environ 4 à 6 mois d'une équipe de 3 personnes. |
| Complétude à la soumission — Coût de fonctionnement annuel | 15 k€/an | 22 k€/an | 30 k€/an | Licences ou API de reconnaissance documentaire, hébergement, maintenance et suivi de la qualité. |
| Complétude à la soumission — Part des boucles « dossier incomplet » évitées | 25 % | 40 % | 55 % | Pièces absentes, illisibles ou périmées détectables automatiquement au dépôt ; une partie des compléments naît toutefois des questions de l'analyste à la validation et reste hors d'atteinte. |
| Complétude à la soumission — Part des appels de complétion évités | 10 % | 20 % | 30 % | Les informations manquantes signalées en ligne au moment du dépôt évitent une partie des appels de complétion (en moyenne 3,3 sessions d'appel par dossier complété). |
| Complétude à la soumission — Part de l'effort reportée en amont | 10 % | 25 % | 40 % | Traitement des alertes du contrôle, accompagnement des clients en difficulté avec le dépôt en ligne : une partie du temps économisé est réengagée en amont. |
| Complétude à la soumission — Part causale de l'écart d'annulation lié aux boucles | 25 % | 50 % | 75 % | Les dossiers passés par une boucle « incomplet » sont plus souvent annulés que les autres dossiers validés (écart mesuré) ; seule une partie de cet écart est attribuable à la boucle elle-même. |
| Relances priorisées — Coût de construction | 40 k€ | 60 k€ | 90 k€ | Industrialisation du score, file de relance triée dans l'outil des conseillers, tableau de suivi ; environ 3 mois. |
| Relances priorisées — Coût de fonctionnement annuel | 10 k€/an | 15 k€/an | 25 k€/an | Supervision du modèle (dérive, recalibrage trimestriel), maintenance. |
| Relances priorisées — Part des offres envoyées ciblées en priorité | 20 % | 20 % | 20 % | Variable de pilotage (capacité de relance renforcée disponible). |
| Relances priorisées — Part des abandons ciblés récupérés par la relance renforcée | 5 % | 10 % | 20 % | Inconnue à ce stade : c'est précisément ce qu'un pilote A/B doit mesurer. Fourchette volontairement large. |
| Relances priorisées — Appels supplémentaires par dossier ciblé | 1 | 2 | 3 | Relance renforcée (appel anticipé puis rappel avant expiration de l'offre). |
| Pré-analyse assistée — Coût de construction | 90 k€ | 130 k€ | 200 k€ | Extraction et rapprochement des pièces, fiche de synthèse, évaluation de la qualité, garde-fous et documentation de conformité ; environ 6 mois. |
| Pré-analyse assistée — Coût de fonctionnement annuel | 15 k€/an | 25 k€/an | 40 k€/an | Appels au modèle de langage (quelques centaines d'euros par an au volume observé), hébergement, supervision humaine de la qualité, maintenance. |
| Pré-analyse assistée — Réduction du temps de travail de validation | 15 % | 25 % | 40 % | Ordres de grandeur publiés sur l'IA générative en situation de travail réelle ou contrôlée : +14 % de productivité en support client (Brynjolfsson, Li et Raymond), −40 % de temps sur des tâches de rédaction professionnelle (Noy et Zhang), +25 % de vitesse sur des tâches de conseil (Dell'Acqua et al.). La validation reste une décision humaine : seule la préparation du dossier est accélérée. |

Sources des ordres de grandeur de productivité de l'IA générative : Brynjolfsson, Li et Raymond, *Generative AI at Work*, NBER Working Paper 31161 (2023), +14 % de demandes résolues par heure ; Noy et Zhang, *Science* 381 (2023), −40 % de temps sur des tâches de rédaction ; Dell'Acqua et al., *Navigating the Jagged Technological Frontier*, Harvard Business School Working Paper 24-013 (2023), tâches réalisées 25 % plus vite.

Étalonnage de la marge : sur les 21 768 offres retenues du BPI Challenge 2017 – Offer log (même établissement, 2016 ; van Dongen, 2017, 4TU.ResearchData, https://doi.org/10.4121/uuid:7e326e7e-8b93-4701-8860-71213edf0fbe), le taux annuel implicite médian est de 4,9 %, la durée médiane de 80 mois et les intérêts bruts représentent 18 % du montant (médiane). La marge nette retenue en est environ le quart.

## Résultats par opportunité

### Contrôle automatique de complétude à la soumission

| Indicateur (scénario central, régime de croisière) | Valeur |
|---|---|
| Heures libérées par an | 1 698 h (1,1 ETP) |
| Prêts supplémentaires par an | 38,5 |
| Capacité libérée valorisée | 76 k€ |
| Marge sur prêts supplémentaires | 30 k€ |
| Coût des appels supplémentaires | 0 k€ |
| Bénéfice annuel | 107 k€ |
| VAN sur 36 mois | 57 k€ |
| Retour sur investissement | 24 mois |

Monte Carlo : VAN médiane 48 k€ (P10 −4 k€, P90 108 k€), positive dans 88 % des tirages. Délai médian des prêts approuvés après rejeu : 13,7 j (contre 14,4 j).

Hypothèses les plus influentes (VAN quand l'hypothèse passe de son minimum à son maximum) :

| Hypothèse | VAN au minimum | VAN au maximum |
|---|---|---|
| Part des boucles « dossier incomplet » évitées | 1 k€ | 113 k€ |
| Coût de construction | 86 k€ | 8 k€ |
| Part des appels de complétion évités | 26 k€ | 89 k€ |
| Part de l'effort reportée en amont | 88 k€ | 27 k€ |

### Priorisation des relances d'offres par score d'abandon

| Indicateur (scénario central, régime de croisière) | Valeur |
|---|---|
| Heures libérées par an | 0 h (0,0 ETP) |
| Prêts supplémentaires par an | 58,4 |
| Capacité libérée valorisée | 0 k€ |
| Marge sur prêts supplémentaires | 46 k€ |
| Coût des appels supplémentaires | 5 k€ |
| Bénéfice annuel | 40 k€ |
| VAN sur 36 mois | −7 k€ |
| Retour sur investissement | 36 mois |

Monte Carlo : VAN médiane 1 k€ (P10 −45 k€, P90 68 k€), positive dans 51 % des tirages.

Hypothèses les plus influentes (VAN quand l'hypothèse passe de son minimum à son maximum) :

| Hypothèse | VAN au minimum | VAN au maximum |
|---|---|---|
| Part des abandons ciblés récupérés par la relance renforcée | −57 k€ | 91 k€ |
| Marge nette actualisée par euro prêté | −47 k€ | 52 k€ |
| Coût de construction | 12 k€ | −37 k€ |
| Coût de fonctionnement annuel | 4 k€ | −31 k€ |

Lecture : la VAN s'annule pour un taux de récupération de 10,7 % (hypothèse centrale 10 %) ou une couverture des abandons de 24,9 % à 20 % des dossiers appelés (mesurée : 23,2 %). Un ciblage au hasard donnerait une VAN de −21 k€ : le score n'apporte qu'une petite part du gain, qui dépend surtout de l'efficacité de la relance elle-même.

### Pré-analyse assistée des dossiers à valider

| Indicateur (scénario central, régime de croisière) | Valeur |
|---|---|
| Heures libérées par an | 1 149 h (0,7 ETP) |
| Prêts supplémentaires par an | 0,0 |
| Capacité libérée valorisée | 52 k€ |
| Marge sur prêts supplémentaires | 0 k€ |
| Coût des appels supplémentaires | 0 k€ |
| Bénéfice annuel | 52 k€ |
| VAN sur 36 mois | −80 k€ |
| Retour sur investissement | au-delà de 36 mois |

Monte Carlo : VAN médiane −89 k€ (P10 −132 k€, P90 −45 k€), positive dans 0 % des tirages.

Hypothèses les plus influentes (VAN quand l'hypothèse passe de son minimum à son maximum) :

| Hypothèse | VAN au minimum | VAN au maximum |
|---|---|---|
| Coût de construction | −41 k€ | −148 k€ |
| Réduction du temps de travail de validation | −120 k€ | −21 k€ |
| Coût de fonctionnement annuel | −59 k€ | −112 k€ |
| Coût horaire complet d'un conseiller back-office | −96 k€ | −58 k€ |

## Portefeuille et interactions

La pré-analyse s'appliquerait aux heures de validation restantes après le contrôle de complétude (les re-validations évitées ne sont pas comptées deux fois) : 1 922 h observées au lieu de 2 126 h, soit une VAN centrale de −90 k€. Lancer les trois opportunités ensemble donnerait une VAN centrale de −40 k€ : le portefeuille n'a de sens que s'il est séquencé.

## Recommandation

1. **Lancer le contrôle de complétude** (construction en 5 mois), avec un suivi hebdomadaire du taux de boucles « incomplet ».
2. **Piloter la relance renforcée** sur une règle simple (délai avant offre, montant) en A/B pendant 8 semaines, avant tout développement de score.
3. **Différer la pré-analyse assistée** : la réévaluer une fois le socle de lecture documentaire de la complétude en service (coûts mutualisés) et avant l'échéance des obligations haut risque de l'AI Act (2 décembre 2027).

## Limites

- Cinq mois observés : la saisonnalité est encadrée par un facteur de volume (−15 % à +10 %), pas mesurée.
- Les coûts de construction et de fonctionnement sont des ordres de grandeur à remplacer par des devis.
- L'effet des boucles sur les annulations est observationnel : seule une part causale (hypothèse) est retenue.
- Les heures libérées ne deviennent une économie que si la capacité est redéployée ou absorbe une croissance.
