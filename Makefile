# Credit Process Intelligence — commandes du projet
#
# Prérequis : uv (Python 3.12, https://docs.astral.sh/uv/), Node.js 20 ou plus et npm, git.
# `make help` liste les cibles. `make demo` suffit pour voir le rapport (Node.js seul).

UV ?= uv
PY := $(UV) run python
NPM ?= npm
SITE := site

.DEFAULT_GOAL := help
.PHONY: help demo install install-python install-site browsers data ingest pipeline docs bpmn-svg \
	notebook site preview test test-python test-site e2e lint lint-python lint-site lint-docs \
	check-links reproductibilite screenshots readme-render all clean

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-17s\033[0m %s\n", $$1, $$2}'

demo: install-site site ## Construit et sert le rapport sur http://localhost:4173/credit-process-intelligence/
	cd $(SITE) && $(NPM) run preview

install: install-python install-site browsers ## Installe toutes les dépendances (Python, site, Chromium)

install-python: ## Environnement Python 3.12 (uv)
	$(UV) sync

install-site: ## Dépendances du site (npm ci)
	cd $(SITE) && $(NPM) ci

browsers: ## Chromium pour Playwright (rendu BPMN, tests de bout en bout, captures)
	cd $(SITE) && npx playwright install chromium

data: ## Télécharge et vérifie les journaux (4TU, sinon copie publique pm4py-core)
	$(PY) -m cpi data

ingest: data ## Convertit le journal XES en table Parquet normalisée
	$(PY) -m cpi ingest

pipeline: data ## Analyse complète : exports du site, modèles BPMN et documents chiffrés
	$(PY) -m cpi pipeline --reingest

docs: ## Régénère les modèles BPMN et les documents chiffrés depuis les exports
	$(PY) -m cpi bpmn
	$(PY) -m cpi docs

bpmn-svg: ## Rend les modèles BPMN en SVG (bpmn-js dans un navigateur sans interface)
	cd $(SITE) && node scripts/export-bpmn-svg.mjs

notebook: ## Exécute le carnet d'analyse et enregistre ses sorties
	$(UV) run jupyter nbconvert --to notebook --execute --inplace \
		--ExecutePreprocessor.timeout=900 --ExecutePreprocessor.record_timing=False notebooks/analyse-processus-credit.ipynb

site: ## Construit le rapport interactif statique (site/dist)
	cd $(SITE) && $(NPM) run build

preview: ## Sert le rapport déjà construit (bloquant : Ctrl+C pour arrêter)
	cd $(SITE) && $(NPM) run preview

test: test-python test-site ## Tests unitaires Python et site

test-python: ## Tests Python (pytest)
	$(UV) run pytest

test-site: ## Tests du site (vitest), dont la concordance avec le calcul Python
	cd $(SITE) && $(NPM) test

e2e: site ## Test de bout en bout du rapport (Playwright, Chromium)
	cd $(SITE) && npx playwright test

lint: lint-python lint-site lint-docs ## Lint, formatage, typage, typographie et liens

lint-python: ## ruff et mypy
	$(UV) run ruff check src tests scripts
	$(UV) run ruff format --check src tests scripts
	$(UV) run mypy src

lint-site: ## eslint, TypeScript et typographie française de l'interface
	cd $(SITE) && $(NPM) run lint && $(NPM) run typecheck && node scripts/typo-fr.mjs --check

lint-docs: check-links ## Typographie française du README et des documents
	$(PY) -m cpi typo --check

check-links: ## Vérifie les liens relatifs du README et des documents
	$(PY) scripts/check_links.py

reproductibilite: pipeline ## Relance le pipeline et vérifie que les fichiers suivis sont inchangés
	git diff --stat --exit-code -- site/public/data site/public/bpmn docs ':!docs/img'

screenshots: site ## Captures du rapport dans docs/img (Playwright, après les animations)
	cd $(SITE) && node scripts/screenshots.mjs

readme-render: ## Rend le README façon GitHub et en fait une capture (site/test-results/readme)
	cd $(SITE) && node scripts/render-readme.mjs

all: install pipeline notebook bpmn-svg site lint test e2e screenshots ## Régénère et vérifie tout

clean: ## Supprime les fichiers générés non versionnés
	rm -rf $(SITE)/dist $(SITE)/test-results $(SITE)/playwright-report data/interim data/models
