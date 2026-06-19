# Conduite du changement

> Document généré par `make docs` : les valeurs de référence citées viennent des exports du pipeline.

## 1. Ce qui change, pour qui

| Population | Aujourd'hui (mesuré) | Demain | Impact |
|---|---|---|---|
| Clients | Pièces réclamées après la validation dans 51 % des dossiers validés ; retour médian de l'offre en 9,0 j | Manques signalés dès le dépôt | Moins d'allers-retours, délai plus court |
| Centre de contact | 3,3 sessions d'appel de complétion par dossier ; 22 976 relances d'offres en 5 mois | Appels ciblés sur les manques restants ; pilote de relance renforcée | Fort : nouvelle file, nouveaux scripts |
| Back-office validation | Attente médiane de 26 h avant traitement ; 11 407 appels pour pièces manquantes en 5 mois | Moins de re-validations | Moyen : moins de reprises, plus de dossiers complets |
| Conformité et protection des données | — | Analyse d'impact, registre des usages, supervision | Moyen : nouvelles revues périodiques |
| DSI et équipe data | — | Exploitation du contrôle de complétude, supervision des modèles | Moyen |

Capacité libérée visée par le contrôle de complétude : environ 1 698 heures par an (1,1 équivalent temps plein, scénario central). L'objectif n'est pas de supprimer des postes : la capacité est redéployée vers la relance des offres et l'accueil des clients en difficulté avec le dépôt en ligne.

## 2. Parties prenantes

| Partie prenante | Intérêt | Influence | Stratégie |
|---|---|---|---|
| Direction des opérations crédit | Élevé | Élevée | Associer : arbitrages, comité mensuel |
| Responsables centre de contact et back-office | Élevé | Élevée | Co-construire : hypothèses, scripts, cibles |
| Conseillers et analystes | Élevé | Moyenne | Impliquer : ateliers, champions, retours terrain |
| Conformité, délégué à la protection des données, risques | Moyen | Élevée | Consulter tôt : qualification, garde-fous |
| Représentants du personnel | Moyen | Moyenne | Informer : finalités, absence d'évaluation individuelle |
| Clients | Élevé | Faible | Informer : parcours de dépôt, mentions de profilage |

## 3. Plan de communication

| Moment | Message | Public | Canal |
|---|---|---|---|
| Lancement | Pourquoi : 99,6 % du délai d'un dossier approuvé est de l'attente, pas du travail | Tous | Réunion d'équipe, restitution du rapport |
| Avant le pilote | Ce que fait (et ne fait pas) la priorisation : jamais l'octroi | Centre de contact, octroi | Atelier, fiche d'une page |
| Mise en service de la complétude | Nouveau parcours de dépôt, rôle du conseiller en cas d'alerte | Clients, centre de contact | Parcours en ligne, formation |
| Chaque mois | Indicateurs d'adoption et de valeur | Comité, équipes | Tableau de bord |

## 4. Formation

| Module | Public | Durée | Contenu |
|---|---|---|---|
| Lire une alerte de complétude | Conseillers | 2 h | Types d'alertes, levée d'une alerte, cas limites |
| Relance renforcée | Conseillers du groupe test | 3 h | Script, rythme de rappel, droit d'opposition du client |
| Esprit critique face aux outils d'IA | Conseillers, analystes | 2 h | Biais d'automatisation, vérification des sources (obligation de culture de l'IA, article 4 de l'AI Act) |
| Supervision des modèles | Équipe data | 1 j | PSI, recalibrage, journalisation, procédure de suspension |

## 5. Indicateurs d'adoption et de valeur

| Indicateur | Référence mesurée | Cible | Fréquence |
|---|---|---|---|
| Dossiers validés passés par une boucle « incomplet » | 51 % | −40 % (hypothèse centrale) | Hebdomadaire |
| Sessions d'appel de complétion par dossier | 3,3 | −20 % (hypothèse centrale) | Mensuelle |
| Délai médian d'un prêt approuvé | 14,4 j | 13,7 j (rejeu) | Mensuelle |
| Offres envoyées finalement annulées | 35 % | À fixer après le pilote A/B | Mensuelle |
| Taux d'usage du parcours de dépôt guidé | — | 90 % des dépôts | Hebdomadaire |
| Alertes de complétude levées par un conseiller | — | Moins de 10 % des alertes | Hebdomadaire |
| Satisfaction des conseillers (outils) | — | Au moins 7 sur 10 | Trimestrielle |

## 6. Risques humains et parades

| Risque | Parade |
|---|---|
| Crainte d'une suppression de postes | Engagement de redéploiement, capacité visée explicitée, dialogue avec les représentants du personnel |
| Défiance envers les alertes automatiques | Levée d'alerte simple, boucle de retour visible, champions dans chaque équipe |
| Confiance excessive (biais d'automatisation) | Relecture obligatoire, échantillon de contrôle, formation |
| Report de charge vers le dépôt en ligne | Suivi des abandons au dépôt, assistance téléphonique dédiée |

## 7. Gouvernance

- **Comité de pilotage mensuel** : direction des opérations, responsables d'équipes, conformité, data.
- **Revue trimestrielle des modèles** : performance, dérive, usages, incidents.
- **Points de décision** : fin du pilote A/B (industrialiser ou non une relance renforcée), réévaluation de la pré-analyse assistée avant le 2 décembre 2027.
