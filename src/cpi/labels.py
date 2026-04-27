"""Table de traduction documentée des activités du journal BPI Challenge 2012.

Le journal mêle trois sous-processus (préfixes) :

* ``A_`` : états de la **demande** (application) ;
* ``O_`` : états de l'**offre** faite au client ;
* ``W_`` : **tâches humaines** (work items), avec un cycle de vie
  SCHEDULE (planifiée) → START (démarrée) → COMPLETE (terminée).

Les libellés néerlandais des tâches W_ sont traduits en français. Les descriptions
reprennent la documentation publique du BPI Challenge 2012 et ce que montre le journal
(position de l'activité dans les parcours) ; elles sont volontairement prudentes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

CATEGORY_LABELS = {
    "A": "Demande",
    "O": "Offre",
    "W": "Tâche humaine",
}

LIFECYCLE_LABELS = {
    "SCHEDULE": "planifiée",
    "START": "démarrée",
    "COMPLETE": "terminée",
}


@dataclass(frozen=True)
class Activity:
    code: str
    label: str
    short: str
    category: str
    description: str
    #: Ordre canonique utilisé pour réordonner des jalons enregistrés au même instant.
    rank: int


ACTIVITIES: tuple[Activity, ...] = (
    Activity("A_SUBMITTED", "Demande soumise", "Soumise", "A",
             "Le client dépose sa demande de crédit (en ligne).", 0),
    Activity("A_PARTLYSUBMITTED", "Demande enregistrée", "Enregistrée", "A",
             "Enregistrement technique de la demande, quelques instants après le dépôt.", 1),
    Activity("A_PREACCEPTED", "Pré-acceptée", "Pré-acceptée", "A",
             "La demande passe le pré-contrôle automatique ; des compléments sont nécessaires.", 2),
    Activity("A_ACCEPTED", "Demande complétée", "Complétée", "A",
             "Demande complétée et jugée recevable : une offre peut être préparée.", 3),
    Activity("O_CANCELLED", "Offre annulée", "Offre annulée", "O",
             "Offre annulée : remplacée par une nouvelle offre ou dossier clos.", 4),
    Activity("O_SELECTED", "Offre sélectionnée", "Offre sélectionnée", "O",
             "Choix des conditions (montant, durée) de l'offre proposée.", 5),
    Activity("A_FINALIZED", "Demande finalisée", "Finalisée", "A",
             "Demande finalisée pour l'envoi d'une offre.", 6),
    Activity("O_CREATED", "Offre créée", "Offre créée", "O",
             "Création du document d'offre.", 7),
    Activity("O_SENT", "Offre envoyée", "Offre envoyée", "O",
             "Envoi de l'offre au client, qui doit la retourner signée.", 8),
    Activity("O_SENT_BACK", "Offre retournée signée", "Offre retournée", "O",
             "Le client renvoie l'offre signée, avec ses justificatifs.", 9),
    Activity("O_ACCEPTED", "Offre acceptée", "Offre acceptée", "O",
             "L'offre signée est acceptée par l'institution.", 10),
    Activity("A_APPROVED", "Approuvée", "Approuvée", "A",
             "Décision favorable sur la demande.", 11),
    Activity("A_REGISTERED", "Enregistrée au contrat", "Contrat enregistré", "A",
             "Enregistrement du contrat de prêt.", 12),
    Activity("A_ACTIVATED", "Prêt activé", "Prêt activé", "A",
             "Mise à disposition du prêt : issue positive du dossier.", 13),
    Activity("O_DECLINED", "Offre refusée", "Offre refusée", "O",
             "L'offre est refusée par l'institution après examen.", 14),
    Activity("A_DECLINED", "Refusée", "Refusée", "A",
             "Refus de la demande (automatique au pré-contrôle ou après examen).", 15),
    Activity("A_CANCELLED", "Annulée", "Annulée", "A",
             "Dossier annulé : abandon du client ou clôture faute de retour.", 16),
    Activity("W_Afhandelen leads", "Traitement des leads", "Leads", "W",
             "Appel de qualification d'une demande (lead) avant ou après le pré-contrôle.", 20),
    Activity("W_Completeren aanvraag", "Complétion de la demande", "Complétion", "W",
             "Appels au client pour compléter la demande avant l'offre.", 21),
    Activity("W_Nabellen offertes", "Relance des offres", "Relance offre", "W",
             "Appels de relance tant que l'offre envoyée n'est pas retournée signée.", 22),
    Activity("W_Valideren aanvraag", "Validation de la demande", "Validation", "W",
             "Contrôle du dossier retourné (pièces, cohérence) avant décision.", 23),
    Activity("W_Nabellen incomplete dossiers", "Relance des dossiers incomplets",
             "Relance pièces", "W",
             "Appels pour obtenir les pièces manquantes détectées à la validation.", 24),
    Activity("W_Beoordelen fraude", "Évaluation fraude", "Fraude", "W",
             "Examen d'une suspicion de fraude.", 25),
    Activity("W_Wijzigen contractgegevens", "Modification du contrat", "Modif. contrat", "W",
             "Modification des données du contrat (planifiée 12 fois, jamais exécutée).", 26),
)

BY_CODE: dict[str, Activity] = {a.code: a for a in ACTIVITIES}

#: Issues finales d'un dossier.
OUTCOME_LABELS = {
    "approved": "Approuvée",
    "declined": "Refusée",
    "cancelled": "Annulée",
    "open": "En cours",
}

#: Ordre d'affichage des issues.
OUTCOME_ORDER = ("approved", "declined", "cancelled", "open")


def label(code: str) -> str:
    """Libellé français d'une activité (le code brut si inconnu)."""
    act = BY_CODE.get(code)
    return act.label if act else code


def short_label(code: str) -> str:
    act = BY_CODE.get(code)
    return act.short if act else code


def rank(code: str) -> int:
    act = BY_CODE.get(code)
    return act.rank if act else 99


def category(code: str) -> str:
    return code.split("_", 1)[0] if "_" in code else "?"


def as_records() -> list[dict[str, object]]:
    """Table de traduction exportable (site, documentation)."""
    return [
        {**asdict(a), "category_label": CATEGORY_LABELS[a.category]} for a in ACTIVITIES
    ]
