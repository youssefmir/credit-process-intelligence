# Credit Process Intelligence — commandes du projet
# Prérequis : Python 3.12+ via uv (https://docs.astral.sh/uv/), Node.js 20+ et npm.
# `make help` liste les cibles.

UV ?= uv
PY := $(UV) run python

.DEFAULT_GOAL := help
.PHONY: help install install-python data ingest pipeline docs

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: install-python ## Installe toutes les dépendances

install-python: ## Installe l'environnement Python (uv, Python 3.12)
	$(UV) sync

data: ## Télécharge et vérifie le journal BPIC 2012 (4TU, sinon repli pm4py-core)
	$(PY) -m cpi data

ingest: data ## Convertit le journal XES en table Parquet normalisée
	$(PY) -m cpi ingest

pipeline: data ## Analyse complète : qualité, process mining, KPI, modèle, business case, exports
	$(PY) -m cpi pipeline --reingest

docs: ## Régénère les documents chiffrés et les modèles BPMN depuis les exports
	$(PY) -m cpi bpmn
	$(PY) -m cpi docs
