# Journal des décisions

Chaque décision structurante est consignée avec son contexte, l'option retenue, les options écartées et ses conséquences. Les numéros sont stables : une décision révisée est marquée comme remplacée, jamais effacée.

## D01 — Source des données et repli

- **Contexte** : le journal BPI Challenge 2012 est publié par 4TU.ResearchData ; le téléchargement direct peut être indisponible selon le réseau.
- **Décision** : `make data` tente d'abord l'API officielle 4TU (contrôle MD5 publié), puis se replie sur la copie publique du dépôt pm4py-core (clone superficiel et partiel, contrôle SHA-256). Dans tous les cas, les comptes (13 087 dossiers, 262 200 événements) sont vérifiés et la provenance est écrite dans `data/raw/`.
- **Écarté** : committer les données brutes (licence, poids du dépôt).
- **Conséquence** : reproductible hors du réseau de 4TU ; les données restent sous leurs conditions d'origine.

## D02 — BPI Challenge 2017 : uniquement pour étalonner une hypothèse

- **Contexte** : le journal 2012 ne contient aucune condition financière ; la valeur d'un prêt supplémentaire est pourtant nécessaire au business case.
- **Décision** : utiliser le journal des offres 2017 (même établissement) pour calculer le taux implicite, la durée et les intérêts bruts des offres retenues, et justifier ainsi l'hypothèse de marge nette. Les deux journaux ne sont jamais mélangés dans les analyses de processus.
- **Écarté** : une marge « de marché » sans ancrage dans les données.

## D03 — Ordre canonique des jalons simultanés

- **Contexte** : 4 116 dossiers ont des jalons enregistrés au même instant dans un ordre arbitraire, ce qui multipliait les variantes (576 au lieu de 86).
- **Décision** : réordonner les seuls jalons A_/O_ distants de moins d'une seconde selon l'ordre métier ; les tâches W_ gardent leur position ; toutes les durées restent calculées sur les horodatages réels.
- **Conséquence** : variantes lisibles ; règle testée sur un mini-journal synthétique.

## D04 — Sessions restées ouvertes

- **Contexte** : 477 sessions de plus de deux heures représentent plus de la moitié des heures brutes ; ce sont des sessions non clôturées, pas du travail.
- **Décision** : remplacer leur durée par la médiane de l'activité (seuil de deux heures), avec une table de sensibilité (une demi-heure à huit heures).
- **Conséquence** : estimation prudente du travail, donc des gains de productivité.

## D05 — Point de décision, étiquette et découpage temporel du modèle

- **Décision** : prédire, à l'envoi de la première offre, si le dossier finira annulé. Apprentissage sur les offres d'octobre et novembre 2011 dont l'issue était connue au 1er janvier 2012 ; décembre sert de zone tampon ; test sur janvier 2012, avec au moins 45 jours d'observation après chaque offre.
- **Écarté** : un découpage aléatoire (fuite temporelle) ; un découpage temporel sans zone tampon (conservé comme contrôle : résultat équivalent).
- **Conséquence** : l'évaluation simule un déploiement réel.

## D06 — Aucun identifiant de collaborateur parmi les variables

- **Décision** : exclure l'identifiant du conseiller des variables du modèle.
- **Raisons** : éviter une évaluation individuelle déguisée des salariés. Un test d'ablation, recalculé à chaque exécution (`model.json`, clé `resource_ablation`, repris dans la fiche modèle), montre que cette variable n'apporte aucun signal.

## D07 — Seuils d'acceptation fixés avant l'évaluation, et non-déploiement

- **Décision** : ROC-AUC ≥ 0,65, lift à 20 % ≥ 1,5, écart de calibration ≤ 0,05, PSI < 0,2. Le score obtenu (ROC-AUC 0,56) ne passe pas : il n'est pas mis en production ; le pilote de relance utilise une règle simple.
- **Raisons** : un modèle à peine meilleur que le hasard coûterait plus qu'il ne rapporte et donnerait une fausse impression de maîtrise.

## D08 — Business case : rejeu contrefactuel et Monte Carlo

- **Décision** : rejouer les dossiers réels avec et sans chaque apport (boucles évitées tirées au sort, heures et délais réels retirés), puis faire varier les hypothèses par Monte Carlo (lois triangulaires, 5 000 tirages, graine fixe). VAN sur 36 mois avec montée en charge, retour sur investissement mensuel, sensibilité par hypothèse.
- **Écarté** : un calcul unique « hypothèse centrale » sans incertitude.
- **Conséquence** : chaque résultat se lit avec une fourchette et une probabilité d'être positif.

## D09 — Annualisation explicite

- **Décision** : facteur 365 / 152 (jours de dépôts observés), encadré par un facteur de volume de −15 % à +10 % dans le Monte Carlo.
- **Raison** : cinq mois observés, saisonnalité inconnue ; prudence à la hausse.

## D10 — BPMN généré par le code

- **Décision** : décrire les modèles AS-IS et TO-BE dans le code (couloirs, grille, règles de tracé) et générer un BPMN 2.0 standard avec diagramme ; rendu SVG par bpmn-js.
- **Écarté** : un modèle dessiné à la main (annotations chiffrées non synchronisées) ; l'export brut de l'inductive miner (identifiants aléatoires, sortie non déterministe, modèle illisible pour le métier).

## D11 — Documents chiffrés générés

- **Décision** : les documents qui citent des chiffres sont produits par des gabarits à partir des exports du pipeline (`make docs`). Les nombres suivent la typographie française et le même arrondi que le site.
- **Conséquence** : aucun chiffre saisi à la main ; un changement de données met tout à jour.

## D12 — Direction artistique : plan de réseau et modernisme néerlandais

- **Contexte** : le rapport doit avoir une identité propre, née du sujet, et éviter l'esthétique générique des interfaces produites en série (polices par défaut, dégradés, cartes arrondies).
- **Décision** : les données viennent d'une banque néerlandaise et un processus est un réseau de parcours. Le rapport emprunte au graphisme moderniste néerlandais (grille stricte, grotesque à largeurs variables, couleurs franches, angles vifs) et au langage des plans de transport : chaque parcours type est une ligne colorée et épaisse, chaque étape une station.
- **Inspirations** : le studio Total Design et Wim Crouwel (grilles et typographie), la signalétique ferroviaire néerlandaise (lisibilité, couleurs franches), le plan du métro de Londres de Harry Beck (schématisation à 45°), la narration annotée du Financial Times et de The Pudding, l'animation de flux des outils de process mining.
- **Choix concrets** : police Archivo (largeurs Expanded pour les titres et chiffres, normale pour le texte, étroite pour les tableaux) ; lignes bleu nominal, vert approuvé, rouge annulé, gris refusé, jaune boucles de reprise ; sections numérotées dont le titre énonce le constat chiffré ; contexte en gris et une seule couleur pour ce qui compte ; annotations posées sur les graphiques.
- **Mouvement** : rejeu animé du journal réel en ouverture ; graphiques qui se dessinent au défilement ; chiffres qui s'incrémentent une fois ; aucune boucle décorative ; préférence « mouvement réduit » respectée (état final affiché directement).

## D13 — Couleurs des graphiques validées

- **Décision** : les couleurs d'identité des lignes sont conservées sur le plan de réseau ; pour les marques des graphiques, la luminosité est ajustée (même teinte) pour passer les contrôles de séparation pour les daltonismes et de contraste, en clair et en sombre. Vert et rouge, proches pour un daltonisme deutéranope, sont toujours accompagnés d'un libellé direct.
- **Conséquence** : chaque graphique a une vue tableau ; aucune information portée par la couleur seule.

## D14 — Pas de sortie de modèle de langage affichée

- **Décision** : la pré-analyse est prototypée par une fiche factuelle déterministe ; la rédaction par un modèle de langage est facultative (clé fournie par l'utilisateur, API compatible OpenAI ou Mistral) et n'est jamais enregistrée ni affichée dans le rapport.
- **Raison** : honnêteté (aucun texte généré présenté comme un résultat) et frontière AI Act.

## D15 — Site statique d'une seule page

- **Décision** : Vite, React et TypeScript, une page avec ancres, chemin de base configurable (`BASE_PATH`) ; polices et bibliothèques embarquées, aucun appel à un réseau de diffusion au chargement.
- **Conséquence** : publication sur GitHub Pages sans erreur 404, fonctionnement hors ligne.
