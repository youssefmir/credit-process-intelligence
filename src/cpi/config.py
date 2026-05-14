"""Paramètres centraux du pipeline : chemins, graine, constantes métier.

Toutes les constantes qui influencent un chiffre publié sont regroupées ici
(ou dans ``config/hypotheses.yaml`` pour les hypothèses du business case),
afin que chaque résultat soit traçable et reproductible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


def _find_root() -> Path:
    """Racine du dépôt : variable ``CPI_ROOT`` ou premier parent contenant pyproject.toml."""
    env = os.environ.get("CPI_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


ROOT = _find_root()
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
MODELS_DIR = DATA_DIR / "models"
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs"
SITE_DATA_DIR = ROOT / "site" / "public" / "data"
SITE_BPMN_DIR = ROOT / "site" / "public" / "bpmn"
HYPOTHESES_FILE = CONFIG_DIR / "hypotheses.yaml"

RAW_LOG = RAW_DIR / "bpic2012.xes.gz"
RAW_LOG_2017 = RAW_DIR / "bpic2017-offers.xes.gz"
EVENTS_FILE = INTERIM_DIR / "events.parquet"

#: Graine unique utilisée partout (échantillonnage, modèles, Monte Carlo).
SEED = 2012

#: Fuseau horaire de l'institution (Pays-Bas) pour les analyses heure / jour.
TIMEZONE = "Europe/Amsterdam"


@dataclass(frozen=True)
class DatasetInfo:
    """Métadonnées et contrat du jeu de données BPI Challenge 2012."""

    name: str = "BPI Challenge 2012"
    author: str = "van Dongen, B. (Boudewijn)"
    year: int = 2012
    publisher: str = "4TU.ResearchData"
    doi: str = "10.4121/uuid:3926db30-f712-4394-aebc-75976070e91f"
    landing_page: str = "https://data.4tu.nl/articles/_/12689204/1"
    terms: str = "4TU General Terms of Use"
    citation: str = "van Dongen, B. (2012). BPI Challenge 2012. 4TU.ResearchData."
    expected_cases: int = 13_087
    expected_events: int = 262_200

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}"


DATASET = DatasetInfo()

# --- Règles de nettoyage des sessions de travail ---------------------------------
#: Au-delà de cette durée, une session START→COMPLETE est considérée comme restée
#: ouverte (oubli de clôture) : sa durée est remplacée par la médiane de l'activité.
SESSION_MAX_SECONDS = 2 * 3600

#: Fenêtre (secondes) en deçà de laquelle des jalons A_/O_ consécutifs d'un même
#: dossier sont considérés simultanés et réordonnés selon l'ordre canonique.
TIE_WINDOW_SECONDS = 1.0

# --- Modèle de prédiction des abandons --------------------------------------------
#: Point de décision : envoi de la première offre au client.
DECISION_ACTIVITY = "O_SENT"

# Découpage temporel strict (dates locales Europe/Amsterdam, bornes incluses à gauche).
TRAIN_START = pd.Timestamp("2011-10-01", tz=TIMEZONE)
TRAIN_END = pd.Timestamp("2011-12-01", tz=TIMEZONE)  # offres envoyées en oct.-nov. 2011
TEST_START = pd.Timestamp("2012-01-01", tz=TIMEZONE)  # déploiement simulé au 1er janvier
#: Une offre n'entre dans le test que si son issue a pu être observée :
#: au moins ``OBSERVATION_DAYS`` jours entre l'offre et la fin du journal.
OBSERVATION_DAYS = 45

#: Part (chronologique) de la fenêtre d'apprentissage réservée à la validation interne
#: (arrêt précoce et calibration).
INNER_VALIDATION_SHARE = 0.2

#: Points de lecture du gain (part des dossiers appelés en priorité).
TOP_K_SHARES = (0.1, 0.2, 0.3, 0.5)
