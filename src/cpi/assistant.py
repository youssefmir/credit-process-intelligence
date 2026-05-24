"""Fiche de pré-analyse d'un dossier (prototype de l'opportunité « pré-analyse assistée »).

Deux étages, volontairement séparés :

1. **Fiche factuelle déterministe** (toujours disponible) : chronologie, volumes de reprise,
   attentes, points d'attention, calculés depuis le journal. Elle ne contient aucune
   appréciation de solvabilité et aucune recommandation de décision.
2. **Rédaction par un modèle de langage** (facultative) : reformulation de la fiche en note
   courte pour l'analyste, via une API compatible OpenAI (dont Mistral). La clé est fournie
   par l'utilisateur (variables d'environnement) ; sans clé, rien n'est appelé. Le texte
   produit est affiché comme brouillon à relire et n'est jamais enregistré dans le dépôt.

Variables : ``CPI_LLM_PROVIDER`` (``mistral`` ou ``openai-compatible``), ``CPI_LLM_API_KEY``,
``CPI_LLM_BASE_URL`` (endpoint compatible OpenAI), ``CPI_LLM_MODEL``.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from cpi import labels
from cpi.config import TIMEZONE

SYSTEM_PROMPT = (
    "Tu aides un analyste crédit à relire un dossier. Reformule les faits fournis en une note "
    "de 120 mots maximum, en français, avec : chronologie, points d'attention, pièces à "
    "vérifier. N'ajoute aucun fait. N'émets aucun avis sur la solvabilité ni sur la décision "
    "d'octroi : la décision appartient à l'analyste."
)


def _local(ts: pd.Timestamp | None) -> str | None:
    if ts is None or pd.isna(ts):
        return None
    return pd.Timestamp(ts).tz_convert(TIMEZONE).strftime("%d/%m/%Y %H:%M")


def build_brief(
    case_id: str, events: pd.DataFrame, sessions: pd.DataFrame, cases: pd.DataFrame
) -> dict[str, Any]:
    if case_id not in cases.index:
        raise KeyError(f"Dossier inconnu : {case_id}")
    row = cases.loc[case_id]
    c: dict[str, Any] = {str(k): v for k, v in row.to_dict().items()}
    ev = events[events["case_id"] == case_id].sort_values("order")
    s = sessions[sessions["case_id"] == case_id]
    closed = cases[cases["outcome"] != "open"]

    def med(col: str) -> float:
        return float(closed[col].median())

    hours_to_offer = None
    if pd.notna(c["t_first_offer"]):
        hours_to_offer = round((c["t_first_offer"] - c["start"]).total_seconds() / 3600, 1)
    alerts = []
    if c["n_offers"] >= 2:
        alerts.append(f"{int(c['n_offers'])} offres successives : vérifier la dernière version.")
    if c["has_incomplete_calls"]:
        alerts.append(
            f"Pièces manquantes déjà réclamées ({int(c['n_incomplete_calls'])} appels) : "
            "contrôler la complétude avant toute nouvelle relance."
        )
    if c["n_completion"] > 2 * max(med("n_completion"), 1):
        alerts.append("Complétion laborieuse (appels nombreux) : client difficile à joindre.")
    if hours_to_offer is not None and hours_to_offer > 3 * max(
        float(((closed["t_first_offer"] - closed["start"]).dt.total_seconds() / 3600).median()),
        1,
    ):
        alerts.append("Délai long avant la première offre.")
    timeline = [
        {"when": _local(ts), "step": labels.label(a)}
        for a, ts in zip(ev["activity"], ev["timestamp"], strict=True)
        if a.startswith(("A_", "O_"))
    ]
    return {
        "case_id": case_id,
        "amount_requested_eur": float(c["amount_req"]),
        "outcome_so_far": labels.OUTCOME_LABELS[str(c["outcome"])],
        "submitted": _local(c["start"]),
        "first_offer": _local(c["t_first_offer"]),
        "offer_returned": _local(c["t_sent_back"]),
        "hours_to_first_offer": hours_to_offer,
        "offers": int(c["n_offers"]),
        "completion_calls": int(c["n_completion"]),
        "offer_calls": int(c["n_offer_calls"]),
        "incomplete_calls": int(c["n_incomplete_calls"]),
        "work_minutes": round(float(s["dur_s"].sum()) / 60, 1),
        "alerts": alerts,
        "timeline": timeline,
        "disclaimer": (
            "Fiche factuelle issue du journal ; aucune appréciation de solvabilité, "
            "aucune recommandation de décision."
        ),
    }


def to_markdown(brief: dict[str, Any]) -> str:
    lines = [
        f"# Fiche de pré-analyse — dossier {brief['case_id']}",
        "",
        f"- Montant demandé : {brief['amount_requested_eur']:,.0f} €".replace(",", " "),
        f"- Statut : {brief['outcome_so_far']}",
        f"- Dépôt : {brief['submitted']} ; 1re offre : {brief['first_offer'] or '—'} ; "
        f"offre retournée : {brief['offer_returned'] or '—'}",
        f"- Offres : {brief['offers']} ; appels de complétion : {brief['completion_calls']} ; "
        f"relances d'offre : {brief['offer_calls']} ; relances pièces : "
        f"{brief['incomplete_calls']}",
        "",
        "## Points d'attention",
        *(f"- {a}" for a in brief["alerts"] or ["Aucun point d'attention détecté."]),
        "",
        f"_{brief['disclaimer']}_",
    ]
    return "\n".join(lines)


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass
class OpenAICompatibleClient:
    """Client minimal pour une API « chat completions » compatible OpenAI (dont Mistral)."""

    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.load(resp)
        return str(body["choices"][0]["message"]["content"]).strip()


def client_from_env(env: dict[str, str] | None = None) -> OpenAICompatibleClient | None:
    env = dict(os.environ if env is None else env)
    key = env.get("CPI_LLM_API_KEY")
    if not key:
        return None
    provider = env.get("CPI_LLM_PROVIDER", "mistral").lower()
    default_url = "https://api.mistral.ai/v1" if provider == "mistral" else ""
    base_url = env.get("CPI_LLM_BASE_URL", default_url)
    if not base_url:
        raise ValueError("CPI_LLM_BASE_URL est requis pour un endpoint compatible OpenAI.")
    model = env.get("CPI_LLM_MODEL", "mistral-small-latest" if provider == "mistral" else "")
    if not model:
        raise ValueError("CPI_LLM_MODEL est requis.")
    return OpenAICompatibleClient(base_url=base_url, api_key=key, model=model)


def draft_note(brief: dict[str, Any], client: LLMClient) -> str:
    facts = {k: v for k, v in brief.items() if k not in ("disclaimer",)}
    return client.complete(SYSTEM_PROMPT, json.dumps(facts, ensure_ascii=False))


def main(case_id: str, use_llm: bool = False) -> None:
    from cpi.cases import build_cases
    from cpi.ingest import load_events
    from cpi.sessions import build_sessions

    events = load_events()
    sessions, _ = build_sessions(events)
    cases = build_cases(events, sessions)
    brief = build_brief(case_id, events, sessions, cases)
    print(to_markdown(brief))
    if not use_llm:
        return
    client = client_from_env()
    if client is None:
        print("\nAucune clé fournie (CPI_LLM_API_KEY) : rédaction par LLM ignorée.")
        return
    print("\n--- Brouillon rédigé par un modèle de langage (à relire, non enregistré) ---\n")
    print(draft_note(brief, client))
